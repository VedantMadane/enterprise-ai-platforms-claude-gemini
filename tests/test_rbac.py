import pytest
from meridian.auth.rbac import RBACPolicy
from meridian.ingestion.directory_loader import load_directory
from meridian.config import DATA_DIR
from meridian.store.sqlite_store import SQLiteStore

@pytest.fixture
def directory():
    return load_directory(DATA_DIR)

def test_rbac_dev_environment(directory, tmp_path):
    rbac = RBACPolicy(env_name="dev")
    store = SQLiteStore(tmp_path / "dev.db")
    store.seed_capabilities_from_env("dev")

    member = directory.get_user("daniel.okafor@meridianls.example") # member
    lead = directory.get_user("priya.nair@meridianls.example") # team_lead
    admin = directory.get_user("chloe.dubois@meridianls.example") # platform_admin

    # In dev: member may read any group
    allowed, group, denial = rbac.check_usage_read(member, "finance", store=store)
    assert allowed is True
    assert denial is None

    # In dev: lead may write capabilities for own group
    allowed, denial = rbac.check_capabilities_write(lead, "clinical-operations")
    assert allowed is True

def test_rbac_prod_environment(directory, tmp_path):
    rbac = RBACPolicy(env_name="prod")
    store = SQLiteStore(tmp_path / "prod.db")
    store.seed_capabilities_from_env("prod")

    member = directory.get_user("daniel.okafor@meridianls.example")
    lead_clinops = directory.get_user("priya.nair@meridianls.example")
    admin = directory.get_user("chloe.dubois@meridianls.example")

    # 1. Member cannot read usage in prod
    allowed, _, denial = rbac.check_usage_read(member, "clinical-operations", store=store)
    assert allowed is False
    assert denial.error == "permission_denied"
    assert denial.required_scope == "usage:read"

    # 2. Team lead may read their own group
    allowed, resolved_group, denial = rbac.check_usage_read(lead_clinops, "clinical-operations", store=store)
    assert allowed is True
    assert resolved_group == "clinical-operations"
    assert denial is None

    # 3. Team lead CANNOT read another group in prod (Structured Denial)
    allowed, _, denial = rbac.check_usage_read(lead_clinops, "finance", store=store)
    assert allowed is False
    assert denial.error == "permission_denied"
    assert "restricted to own group" in denial.reason

    # 4. Team lead CANNOT write capabilities in prod (Only platform_admin)
    allowed, denial = rbac.check_capabilities_write(lead_clinops, "clinical-operations")
    assert allowed is False
    assert denial.error == "permission_denied"
    assert denial.required_scope == "capabilities:write"

    # 5. Platform admin CAN write capabilities in prod
    allowed, denial = rbac.check_capabilities_write(admin, "clinical-operations")
    assert allowed is True
    assert denial is None

    # 6. Platform admin CAN read any group in prod
    allowed, resolved_group, denial = rbac.check_usage_read(admin, "clinical-operations", store=store)
    assert allowed is True
    assert resolved_group == "clinical-operations"

def test_capability_disabled_denial(directory, tmp_path):
    # In prod, usage-connector is disabled by default for finance!
    rbac = RBACPolicy(env_name="prod")
    store = SQLiteStore(tmp_path / "prod.db")
    store.seed_capabilities_from_env("prod")

    admin = directory.get_user("chloe.dubois@meridianls.example")

    # In prod, finance has usage-connector disabled
    allowed, _, denial = rbac.check_usage_read(admin, "finance", store=store)
    assert allowed is False
    assert denial.error == "permission_denied"
    assert "Capability 'usage-connector' is disabled" in denial.reason
