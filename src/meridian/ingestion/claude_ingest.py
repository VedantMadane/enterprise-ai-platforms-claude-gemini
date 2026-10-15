import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple
from meridian.config import DATA_DIR
from meridian.ingestion.directory_loader import Directory
from meridian.models.unified import UnifiedUsageRecord

def ingest_claude_data(data_dir: Path, directory: Directory) -> List[UnifiedUsageRecord]:
    """
    Ingests Claude Enterprise Analytics API exports (usage and cost reports)
    into unified records.
    
    Converts cost from cents (decimal strings) to USD dollars (float).
    Aggregates tokens breakdown into input, output, and total tokens.
    Attributes to user and group via Directory.
    """
    usage_path = data_dir / "claude" / "user_usage_report.json"
    cost_path = data_dir / "claude" / "user_cost_report.json"

    with open(usage_path, "r", encoding="utf-8") as f:
        usage_data = json.load(f)["data"]

    with open(cost_path, "r", encoding="utf-8") as f:
        cost_data = json.load(f)["data"]

    # Index costs by (user_id, date, product, model) -> total cost in USD and breakdown
    cost_map: Dict[Tuple[str, str, str, str], Dict] = {}
    for entry in cost_data:
        user_id = entry["actor"]["user_id"]
        record_date = entry["starting_at"][:10]
        product = entry["product"]
        model = entry["model"]
        key = (user_id, record_date, product, model)

        amount_cents = Decimal(str(entry.get("amount", "0")))
        amount_usd = float(amount_cents / Decimal(100))
        cost_type = entry.get("cost_type", "tokens")

        if key not in cost_map:
            cost_map[key] = {
                "total_cost_usd": 0.0,
                "breakdown": {}
            }
        cost_map[key]["total_cost_usd"] += amount_usd
        cost_map[key]["breakdown"][cost_type] = cost_map[key]["breakdown"].get(cost_type, 0.0) + amount_usd

    records: List[UnifiedUsageRecord] = []
    for row in usage_data:
        actor_id = row["actor"]["user_id"]
        rec_date_str = row["starting_at"][:10]
        rec_date = date.fromisoformat(rec_date_str)
        iso_year, iso_week_num, _ = rec_date.isocalendar()
        iso_week = f"{iso_year}-W{iso_week_num:02d}"

        product = row["product"]
        model = row["model"]
        key = (actor_id, rec_date_str, product, model)

        # Attribute user
        user = directory.get_user(actor_id)
        user_name = user.name if user else row["actor"].get("name", actor_id)
        user_email = user.email if user else row["actor"].get("email", "")

        # Attribute group
        rbac_id = row.get("rbac_group_id")
        group = directory.get_group_for_claude_rbac(rbac_id) if rbac_id else None
        if not group and user and user.group_ids:
            group = directory.get_group(user.group_ids[0])
        group_id = group.group_id if group else "unknown-group"

        # Token calculation
        cache_creation = row.get("cache_creation", {})
        ephem_5m = cache_creation.get("ephemeral_5m_input_tokens", 0)
        ephem_1h = cache_creation.get("ephemeral_1h_input_tokens", 0)
        uncached_in = row.get("uncached_input_tokens", 0)
        cache_read_in = row.get("cache_read_input_tokens", 0)
        input_tokens = uncached_in + cache_read_in + ephem_5m + ephem_1h
        output_tokens = row.get("output_tokens", 0)
        total_tokens = row.get("total_tokens", input_tokens + output_tokens)

        # Cost
        cost_info = cost_map.get(key, {"total_cost_usd": 0.0, "breakdown": {}})
        cost_usd = round(cost_info["total_cost_usd"], 6)

        requests = row.get("requests", 0)
        server_tools = row.get("server_tool_use", {})
        web_search_reqs = server_tools.get("web_search_requests", 0)

        record_id = f"claude:{actor_id}:{rec_date_str}:{product}:{model}"

        record = UnifiedUsageRecord(
            id=record_id,
            platform="claude",
            user_id=actor_id,
            user_name=user_name,
            user_email=user_email,
            group_id=group_id,
            date=rec_date_str,
            iso_week=iso_week,
            product_or_agent=product,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            requests=requests,
            metadata={
                "uncached_input_tokens": uncached_in,
                "cache_read_input_tokens": cache_read_in,
                "cache_creation_5m": ephem_5m,
                "cache_creation_1h": ephem_1h,
                "web_search_requests": web_search_reqs,
                "cost_breakdown_usd": cost_info["breakdown"],
                "speed": row.get("speed"),
                "context_window": row.get("context_window")
            }
        )
        records.append(record)

    return records
