import pytest
from fastapi.testclient import TestClient
from meridian.api.app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app(env_name="prod", db_path=tmp_path / "test_api.db")
    with TestClient(app) as test_client:
        yield test_client

def test_api_me_profile(client):
    # As Team Lead Priya Nair
    res = client.get("/api/me", headers={"X-Actor-Email": "priya.nair@meridianls.example"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "priya.nair@meridianls.example"
    assert data["role"] == "team_lead"
    assert data["primary_group"] == "clinical-operations"
    assert data["permissions"]["can_read_usage"] is True
    assert data["permissions"]["can_write_capabilities"] is False # prod

def test_api_usage_summary_allowed_and_denied(client):
    # 1. Allowed: Lead queries own group (clinical-operations)
    res = client.get(
        "/api/usage/summary?period=last_30_days&group=clinical-operations",
        headers={"X-Actor-Email": "priya.nair@meridianls.example"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["group"] == "clinical-operations"
    assert len(data["platforms"]) == 2
    assert data["totals"]["total_tokens"] > 0
    assert data["totals"]["cost_usd"] > 0

    # 2. Denied: Lead queries cross-group (finance)
    res_denied = client.get(
        "/api/usage/summary?period=last_30_days&group=finance",
        headers={"X-Actor-Email": "priya.nair@meridianls.example"}
    )
    assert res_denied.status_code == 403
    err = res_denied.json()["detail"]
    assert err["error"] == "permission_denied"

def test_api_top_users(client):
    res = client.get(
        "/api/usage/top-users?period=last_30_days&limit=5",
        headers={"X-Actor-Email": "priya.nair@meridianls.example"}
    )
    assert res.status_code == 200
    users = res.json()
    assert len(users) <= 5
    # Ranked DESC
    assert users[0]["total_tokens"] >= users[-1]["total_tokens"]

def test_api_capabilities_admin_write(client):
    # 1. Non-admin team lead cannot update capability in prod
    res_lead = client.post(
        "/api/capabilities",
        headers={"X-Actor-Email": "priya.nair@meridianls.example"},
        json={"group": "clinical-operations", "capability": "code-execution", "enabled": True}
    )
    assert res_lead.status_code == 403

    # 2. Platform admin CAN update capability in prod
    res_admin = client.post(
        "/api/capabilities",
        headers={"X-Actor-Email": "chloe.dubois@meridianls.example"},
        json={"group": "clinical-operations", "capability": "code-execution", "enabled": True}
    )
    assert res_admin.status_code == 200
    res_data = res_admin.json()
    assert res_data["enabled"] is True
    assert res_data["capability"] == "code-execution"
    assert res_data["updated_by"] == "chloe.dubois@meridianls.example"

def test_api_directory_and_weekly_and_static(client):
    # Directory endpoints
    res_users = client.get("/api/directory/users")
    assert res_users.status_code == 200
    assert len(res_users.json()) == 22

    res_groups = client.get("/api/directory/groups")
    assert res_groups.status_code == 200
    assert len(res_groups.json()) == 6

    # Weekly endpoint as lead
    res_weekly = client.get(
        "/api/usage/by-group-and-week",
        headers={"X-Actor-Email": "priya.nair@meridianls.example"}
    )
    assert res_weekly.status_code == 200
    weekly_data = res_weekly.json()
    assert len(weekly_data) > 0
    # Lead in prod only sees own group
    assert all(r["group_id"] == "clinical-operations" for r in weekly_data)

    # Static UI page
    res_ui = client.get("/")
    assert res_ui.status_code == 200
    assert "Meridian Life Sciences" in res_ui.text
