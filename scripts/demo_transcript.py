#!/usr/bin/env python3
"""
Executes and records the required Part B demonstration scenarios:
1. Allowed read: Team lead querying own group's usage summary.
2. Denied cross-group read: Team lead querying another group's usage summary -> structured denial.
3. Denied write: Team lead attempting to set a capability in prod -> structured denial.
4. Allowed write: Platform admin updating a capability in prod.
5. Gated capability denial: Querying a group where 'usage-connector' is disabled.

Outputs formatted transcripts to stdout and saves to docs/TRANSCRIPT.md.
"""
import json
from pathlib import Path
from meridian.config import BASE_DIR, DATA_DIR
from meridian.ingestion.engine import IngestionEngine
from meridian.mcp.server import MeridianMCPServer
from meridian.store.sqlite_store import SQLiteStore

def run_demo():
    print("=" * 80)
    print("Meridian Life Sciences — MCP Connector Verification & Security Transcript")
    print("Environment: prod | Reference Date: 2026-09-28")
    print("=" * 80)

    db_path = BASE_DIR / "meridian_prod_demo.db"
    store = SQLiteStore(db_path)
    engine = IngestionEngine(DATA_DIR)
    _, records = engine.run_ingestion()
    store.seed_usage_records(records)
    store.seed_capabilities_from_env("prod")

    transcript_lines = [
        "# Part B Demonstration Transcript",
        "",
        "**Assignment ID**: `Fullstack-ClaudeGemini-UsageConnector-v1`  ",
        "**Environment**: `prod`  ",
        "**Host Target**: Claude Desktop / Gemini CLI MCP stdio connector  ",
        "",
        "This transcript records the exact execution traces of the Meridian MCP Connector across allowed and denied access patterns.",
        "",
        "---",
        ""
    ]

    # --- Scenario 1: Allowed Read (Team Lead own group) ---
    print("\n[Scenario 1] Allowed Read — Team Lead queries own group (clinical-operations)")
    lead_server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=store
    )
    s1_result = lead_server.usage_summary(period="last_30_days", group="clinical-operations")
    print(json.dumps(s1_result, indent=2))

    transcript_lines.extend([
        "## Scenario 1: Allowed Read (Team Lead — Own Group)",
        "- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`, Group: `clinical-operations`)",
        "- **Tool Call**: `usage_summary(period=\"last_30_days\", group=\"clinical-operations\")`",
        "- **Result**: **200 OK** — Returns platform token breakdown and dollar costs.",
        "",
        "```json",
        json.dumps(s1_result, indent=2),
        "```",
        "",
        "---",
        ""
    ])

    # --- Scenario 2: Denied Cross-Group Read (Team Lead queries another group) ---
    print("\n[Scenario 2] Denied Cross-Group Read — Team Lead queries unauthorized group (finance)")
    s2_result = lead_server.usage_summary(period="last_30_days", group="finance")
    print(json.dumps(s2_result, indent=2))

    transcript_lines.extend([
        "## Scenario 2: Denied Cross-Group Read (Boundary Enforcement)",
        "- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`, Group: `clinical-operations`)",
        "- **Tool Call**: `usage_summary(period=\"last_30_days\", group=\"finance\")`",
        "- **Result**: **Structured Denial** — Enforced in server code before reaching storage.",
        "",
        "```json",
        json.dumps(s2_result, indent=2),
        "```",
        "",
        "---",
        ""
    ])

    # --- Scenario 3: Denied Write (Team Lead attempts capability change in prod) ---
    print("\n[Scenario 3] Denied Write — Team Lead attempts set_capability in prod")
    s3_result = lead_server.set_capability(
        group="clinical-operations",
        capability="code-execution",
        enabled=True
    )
    print(json.dumps(s3_result, indent=2))

    transcript_lines.extend([
        "## Scenario 3: Denied Capability Write (Role Scope Enforcement)",
        "- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`)",
        "- **Tool Call**: `set_capability(group=\"clinical-operations\", capability=\"code-execution\", enabled=true)`",
        "- **Result**: **Structured Denial** — `capabilities:write` restricted to `platform_admin` in `prod`.",
        "",
        "```json",
        json.dumps(s3_result, indent=2),
        "```",
        "",
        "---",
        ""
    ])

    # --- Scenario 4: Allowed Write & Read (Platform Admin) ---
    print("\n[Scenario 4] Allowed Write & Read — Platform Admin")
    admin_server = MeridianMCPServer(
        user_identifier="chloe.dubois@meridianls.example",
        env_name="prod",
        store=store
    )
    s4_write_result = admin_server.set_capability(
        group="clinical-operations",
        capability="code-execution",
        enabled=True
    )
    print("Admin set_capability output:")
    print(json.dumps(s4_write_result, indent=2))

    transcript_lines.extend([
        "## Scenario 4: Allowed Capability Write (Platform Admin)",
        "- **Caller**: `chloe.dubois@meridianls.example` (Role: `platform_admin`)",
        "- **Tool Call**: `set_capability(group=\"clinical-operations\", capability=\"code-execution\", enabled=true)`",
        "- **Result**: **Success** — Control persisted with timestamp and audit attribution.",
        "",
        "```json",
        json.dumps(s4_write_result, indent=2),
        "```",
        "",
        "---",
        ""
    ])

    # --- Scenario 5: Gated Capability Denial (usage-connector disabled) ---
    print("\n[Scenario 5] Gated Capability Denial — Finance group has usage-connector disabled by default in prod")
    s5_result = admin_server.usage_summary(period="last_30_days", group="finance")
    print(json.dumps(s5_result, indent=2))

    transcript_lines.extend([
        "## Scenario 5: Capability Gating Denial (`usage-connector` disabled)",
        "- **Context**: In `prod.yaml`, `usage-connector` is default-enabled only for `clinical-operations` and `it-platform`.",
        "- **Caller**: `chloe.dubois@meridianls.example` querying `finance`",
        "- **Result**: **Structured Denial** — Query rejected because `usage-connector` capability is disabled for the target group.",
        "",
        "```json",
        json.dumps(s5_result, indent=2),
        "```",
        "",
        "---",
        ""
    ])

    # Save to docs/TRANSCRIPT.md
    docs_dir = BASE_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_file = docs_dir / "TRANSCRIPT.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(transcript_lines))
    print(f"\nTranscript successfully saved to {out_file}")

if __name__ == "__main__":
    run_demo()
