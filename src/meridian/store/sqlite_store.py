import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from meridian.config import SQLITE_PATH, ENVIRONMENTS_DIR, CURRENT_ENV
from meridian.models.capabilities import Capability, CapabilityControl
from meridian.models.unified import (
    UnifiedUsageRecord,
    PlatformTotals,
    OverallTotals,
    UsageSummaryResponse,
    TopUser,
    PeriodWindow
)

class SQLiteStore:
    def __init__(self, db_path: Path = SQLITE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unified_usage (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    iso_week TEXT NOT NULL,
                    product_or_agent TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    requests INTEGER,
                    metadata_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_group_date ON unified_usage (group_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_date ON unified_usage (user_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_iso_week ON unified_usage (iso_week, group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_platform_date ON unified_usage (platform, date)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capability_controls (
                    group_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    updated_at TEXT,
                    updated_by TEXT,
                    PRIMARY KEY (group_id, capability)
                )
            """)
            conn.commit()

    def seed_usage_records(self, records: List[UnifiedUsageRecord]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO unified_usage (
                    id, platform, user_id, user_name, user_email, group_id,
                    date, iso_week, product_or_agent, model, input_tokens,
                    output_tokens, total_tokens, cost_usd, requests, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    r.id, r.platform, r.user_id, r.user_name, r.user_email, r.group_id,
                    r.date, r.iso_week, r.product_or_agent, r.model, r.input_tokens,
                    r.output_tokens, r.total_tokens, r.cost_usd, r.requests,
                    json.dumps(r.metadata)
                ) for r in records
            ])
            conn.commit()

    def seed_capabilities_from_env(self, env_name: str = CURRENT_ENV, groups: List[str] = None):
        """
        Seeds default capabilities from environment yaml if not already configured.
        """
        env_file = ENVIRONMENTS_DIR / f"{env_name}.yaml"
        if not env_file.exists():
            return
        
        with open(env_file, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f)

        if not groups:
            groups = [
                "clinical-operations",
                "regulatory-affairs",
                "finance",
                "hr",
                "medical-writing",
                "it-platform"
            ]

        cap_defaults = env_config.get("capability_defaults", {})
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for group in groups:
                for cap_enum in Capability:
                    cap_key = cap_enum.value
                    conf_val = cap_defaults.get(cap_key)
                    enabled = False

                    if isinstance(conf_val, dict) and "enabled_for" in conf_val:
                        enabled = group in conf_val["enabled_for"]
                    elif conf_val == "enabled":
                        enabled = True
                    elif conf_val == "disabled":
                        enabled = False
                    else:
                        enabled = True # default open if unspecified

                    cursor.execute("""
                        INSERT OR IGNORE INTO capability_controls (
                            group_id, capability, enabled, updated_at, updated_by
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (group, cap_key, 1 if enabled else 0, now_iso, "system_seed"))
            conn.commit()

    def get_usage_summary(
        self,
        group_id: Optional[str],
        window: PeriodWindow
    ) -> UsageSummaryResponse:
        query = """
            SELECT
                platform,
                SUM(requests) as total_requests,
                SUM(input_tokens) as sum_input,
                SUM(output_tokens) as sum_output,
                SUM(total_tokens) as sum_total,
                SUM(cost_usd) as sum_cost
            FROM unified_usage
            WHERE date >= ? AND date < ?
        """
        params: List[Any] = [window.start, window.end_exclusive]
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        query += " GROUP BY platform"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()

        platforms_map: Dict[str, PlatformTotals] = {}
        for r in rows:
            plat = r["platform"]
            reqs = r["total_requests"] if plat == "claude" else None
            platforms_map[plat] = PlatformTotals(
                platform=plat,
                requests=reqs,
                input_tokens=int(r["sum_input"] or 0),
                output_tokens=int(r["sum_output"] or 0),
                total_tokens=int(r["sum_total"] or 0),
                cost_usd=round(float(r["sum_cost"] or 0.0), 6)
            )

        # Ensure both platforms are represented even if zero
        for p in ["claude", "gemini"]:
            if p not in platforms_map:
                platforms_map[p] = PlatformTotals(
                    platform=p,
                    requests=0 if p == "claude" else None,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0
                )

        platforms_list = [platforms_map["claude"], platforms_map["gemini"]]
        overall_tokens = sum(p.total_tokens for p in platforms_list)
        overall_cost = round(sum(p.cost_usd for p in platforms_list), 6)

        return UsageSummaryResponse(
            group=group_id if group_id else "all",
            period=window,
            platforms=platforms_list,
            totals=OverallTotals(
                total_tokens=overall_tokens,
                cost_usd=overall_cost
            )
        )

    def get_top_users(
        self,
        group_id: Optional[str],
        window: PeriodWindow,
        limit: int = 10
    ) -> List[TopUser]:
        query = """
            SELECT
                user_id,
                user_name,
                user_email,
                group_id,
                SUM(total_tokens) as sum_tokens,
                SUM(cost_usd) as sum_cost
            FROM unified_usage
            WHERE date >= ? AND date < ?
        """
        params: List[Any] = [window.start, window.end_exclusive]
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        query += """
            GROUP BY user_id, user_name, user_email, group_id
            ORDER BY sum_tokens DESC
            LIMIT ?
        """
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()

        return [
            TopUser(
                user_id=r["user_id"],
                name=r["user_name"],
                email=r["user_email"],
                group=r["group_id"],
                total_tokens=int(r["sum_tokens"] or 0),
                cost_usd=round(float(r["sum_cost"] or 0.0), 6)
            ) for r in rows
        ]

    def get_usage_by_group_and_week(self) -> List[Dict[str, Any]]:
        query = """
            SELECT
                group_id,
                iso_week,
                platform,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as cost_usd,
                SUM(requests) as requests
            FROM unified_usage
            GROUP BY group_id, iso_week, platform
            ORDER BY iso_week ASC, group_id ASC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query).fetchall()
        
        return [
            {
                "group_id": r["group_id"],
                "iso_week": r["iso_week"],
                "platform": r["platform"],
                "total_tokens": int(r["total_tokens"] or 0),
                "cost_usd": round(float(r["cost_usd"] or 0.0), 4),
                "requests": r["requests"]
            } for r in rows
        ]

    def get_capabilities(self, group_id: Optional[str] = None) -> List[CapabilityControl]:
        query = "SELECT group_id, capability, enabled, updated_at, updated_by FROM capability_controls"
        params = []
        if group_id:
            query += " WHERE group_id = ?"
            params.append(group_id)
        query += " ORDER BY group_id ASC, capability ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()

        return [
            CapabilityControl(
                group=r["group_id"],
                capability=Capability(r["capability"]),
                enabled=bool(r["enabled"]),
                updated_at=r["updated_at"],
                updated_by=r["updated_by"]
            ) for r in rows
        ]

    def is_capability_enabled(self, group_id: str, capability: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT enabled FROM capability_controls
                WHERE group_id = ? AND capability = ?
            """, (group_id, capability)).fetchone()
            if row is None:
                return False
            return bool(row["enabled"])

    def set_capability(
        self,
        group_id: str,
        capability: str,
        enabled: bool,
        actor: str
    ) -> CapabilityControl:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO capability_controls (group_id, capability, enabled, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(group_id, capability) DO UPDATE SET
                    enabled=excluded.enabled,
                    updated_at=excluded.updated_at,
                    updated_by=excluded.updated_by
            """, (group_id, capability, 1 if enabled else 0, now_iso, actor))
            conn.commit()

        return CapabilityControl(
            group=group_id,
            capability=Capability(capability),
            enabled=enabled,
            updated_at=now_iso,
            updated_by=actor
        )
