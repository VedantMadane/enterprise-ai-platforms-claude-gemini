import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple
from meridian.config import DATA_DIR
from meridian.ingestion.directory_loader import Directory
from meridian.models.unified import UnifiedUsageRecord

def ingest_gemini_data(data_dir: Path, directory: Directory) -> List[UnifiedUsageRecord]:
    """
    Ingests Google Cloud billing export for Vertex AI Gemini token SKUs into unified records.
    
    Pairs input and output token SKU rows for each (owner, date, project_id, agent, model).
    Converts timestamps from BigQuery format to ISO dates.
    Attributes to user and group via Directory.
    """
    gemini_dir = data_dir / "gemini"
    jsonl_files = list(gemini_dir.glob("gcp_billing_export_*.jsonl"))
    if not jsonl_files:
        return []
    
    # Key: (owner_email, date_str, project_id, agent, model)
    aggregated = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "billing_account_id": None,
        "location": None,
        "skus": []
    })

    for file_path in jsonl_files:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                row = json.loads(line_str)
                labels = {l["key"]: l["value"] for l in row.get("labels", [])}
                owner_email = labels.get("owner", "").lower()
                agent = labels.get("agent", "vertex-ai")
                model = labels.get("model", "gemini")
                
                # BigQuery format: '2026-08-05 00:00:00 UTC'
                usage_start_str = row["usage_start_time"]
                rec_date_str = usage_start_str[:10]
                project_id = row.get("project", {}).get("id", "")

                key = (owner_email, rec_date_str, project_id, agent, model)
                sku_desc = row.get("sku", {}).get("description", "")
                token_amount = int(row.get("usage", {}).get("amount", 0))
                cost = float(row.get("cost", 0.0))

                entry = aggregated[key]
                if "Input Tokens" in sku_desc:
                    entry["input_tokens"] += token_amount
                elif "Output Tokens" in sku_desc:
                    entry["output_tokens"] += token_amount
                else:
                    entry["input_tokens"] += token_amount

                entry["cost_usd"] += cost
                entry["billing_account_id"] = row.get("billing_account_id")
                entry["location"] = row.get("location", {}).get("location")
                entry["skus"].append({
                    "sku_id": row.get("sku", {}).get("id"),
                    "sku_desc": sku_desc,
                    "cost": cost,
                    "tokens": token_amount
                })

    records: List[UnifiedUsageRecord] = []
    for (owner_email, rec_date_str, project_id, agent, model), data in aggregated.items():
        rec_date = date.fromisoformat(rec_date_str)
        iso_year, iso_week_num, _ = rec_date.isocalendar()
        iso_week = f"{iso_year}-W{iso_week_num:02d}"

        # Resolve user
        user = directory.get_user(owner_email)
        user_id = user.user_id if user else f"user_{owner_email}"
        user_name = user.name if user else owner_email

        # Resolve group
        group = directory.get_group_for_gcp_project(project_id)
        if not group and user and user.group_ids:
            group = directory.get_group(user.group_ids[0])
        group_id = group.group_id if group else "unknown-group"

        input_toks = data["input_tokens"]
        output_toks = data["output_tokens"]
        total_toks = input_toks + output_toks
        cost_usd = round(data["cost_usd"], 6)

        record_id = f"gemini:{user_id}:{rec_date_str}:{agent}:{model}"

        records.append(UnifiedUsageRecord(
            id=record_id,
            platform="gemini",
            user_id=user_id,
            user_name=user_name,
            user_email=owner_email,
            group_id=group_id,
            date=rec_date_str,
            iso_week=iso_week,
            product_or_agent=agent,
            model=model,
            input_tokens=input_toks,
            output_tokens=output_toks,
            total_tokens=total_toks,
            cost_usd=cost_usd,
            requests=None, # BigQuery billing export does not provide request count
            metadata={
                "billing_account_id": data["billing_account_id"],
                "project_id": project_id,
                "location": data["location"],
                "skus": data["skus"]
            }
        ))

    return records
