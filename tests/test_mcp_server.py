import json
import pytest
import jsonschema
from meridian.config import CONTRACTS_DIR, DATA_DIR
from meridian.ingestion.engine import IngestionEngine
from meridian.mcp.server import MeridianMCPServer
from meridian.store.sqlite_store import SQLiteStore

@pytest.fixture(scope="module")
def tools_schema():
    schema_path = CONTRACTS_DIR / "tools.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def seeded_store(tmp_path):
    store = SQLiteStore(tmp_path / "test_mcp.db")
    engine = IngestionEngine(DATA_DIR)
    _, records = engine.run_ingestion()
    store.seed_usage_records(records)
    store.seed_capabilities_from_env("prod")
    return store

def test_mcp_usage_summary_allowed_and_schema(seeded_store, tools_schema):
    # Team lead Priya Nair (Clinical Operations) in prod
    server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=seeded_store
    )

    # 1. Allowed: querying own group
    res = server.usage_summary(period="last_30_days", group="clinical-operations")
    assert "error" not in res
    assert res["group"] == "clinical-operations"

    # Validate against tool output schema
    summary_output_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["tools"]["usage_summary"]["output"]
    }
    jsonschema.validate(instance=res, schema=summary_output_schema)

def test_mcp_usage_summary_denied_cross_group(seeded_store, tools_schema):
    # Team lead Priya Nair (Clinical Operations) tries to query Finance
    server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=seeded_store
    )

    res = server.usage_summary(period="last_30_days", group="finance")
    assert res["error"] == "permission_denied"
    assert "restricted to own group" in res["reason"]

    # Validate against denial schema
    denial_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["denial"]
    }
    jsonschema.validate(instance=res, schema=denial_schema)

def test_mcp_top_users_and_schema(seeded_store, tools_schema):
    server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=seeded_store
    )

    res = server.top_users(period="last_30_days", limit=5)
    assert isinstance(res, list)
    assert len(res) <= 5

    top_users_output_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["tools"]["top_users"]["output"]
    }
    jsonschema.validate(instance=res, schema=top_users_output_schema)

def test_mcp_capability_status_and_schema(seeded_store, tools_schema):
    server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=seeded_store
    )

    res = server.capability_status(group="clinical-operations")
    assert isinstance(res, list)

    cap_status_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["tools"]["capability_status"]["output"]
    }
    jsonschema.validate(instance=res, schema=cap_status_schema)

def test_mcp_set_capability_denied_and_allowed(seeded_store, tools_schema):
    # 1. Denied write: Team lead Priya Nair in prod
    lead_server = MeridianMCPServer(
        user_identifier="priya.nair@meridianls.example",
        env_name="prod",
        store=seeded_store
    )
    res_denied = lead_server.set_capability(
        group="clinical-operations",
        capability="code-execution",
        enabled=True
    )
    assert res_denied["error"] == "permission_denied"
    assert res_denied["required_scope"] == "capabilities:write"

    denial_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["denial"]
    }
    jsonschema.validate(instance=res_denied, schema=denial_schema)

    # 2. Allowed write: Platform Admin Chloe Dubois in prod
    admin_server = MeridianMCPServer(
        user_identifier="chloe.dubois@meridianls.example",
        env_name="prod",
        store=seeded_store
    )
    res_allowed = admin_server.set_capability(
        group="clinical-operations",
        capability="code-execution",
        enabled=True
    )
    assert res_allowed["enabled"] is True
    assert res_allowed["capability"] == "code-execution"

    set_cap_schema = {
        "$schema": tools_schema["$schema"],
        "$defs": tools_schema["$defs"],
        **tools_schema["tools"]["set_capability"]["output"]
    }
    jsonschema.validate(instance=res_allowed, schema=set_cap_schema)
