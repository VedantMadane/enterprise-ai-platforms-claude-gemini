import pytest
from meridian.config import DATA_DIR
from meridian.ingestion.directory_loader import load_directory
from meridian.ingestion.claude_ingest import ingest_claude_data
from meridian.ingestion.gemini_ingest import ingest_gemini_data
from meridian.ingestion.engine import IngestionEngine

def test_directory_loading():
    directory = load_directory(DATA_DIR)
    assert len(directory.users) == 22
    assert len(directory.groups) == 6

    # Test key users
    priya = directory.get_user("priya.nair@meridianls.example")
    assert priya is not None
    assert priya.role == "team_lead"
    assert "clinical-operations" in priya.group_ids

    chloe = directory.get_user("chloe.dubois@meridianls.example")
    assert chloe is not None
    assert chloe.role == "platform_admin"

    # Test group lookups
    clinops = directory.get_group("clinical-operations")
    assert clinops is not None
    assert clinops.claude_rbac_group_id == "rbac_group_33DEEC83113481C9BD69498282"
    assert clinops.gcp_project_id == "meridian-clinops-prod"

def test_claude_ingestion():
    directory = load_directory(DATA_DIR)
    records = ingest_claude_data(DATA_DIR, directory)
    assert len(records) == 1346

    # Verify every record attributes to a valid user and group
    for r in records:
        assert r.platform == "claude"
        assert r.user_id.startswith("user_")
        assert r.group_id in [g.group_id for g in directory.groups]
        assert r.total_tokens == r.input_tokens + r.output_tokens
        assert r.cost_usd >= 0.0
        assert r.requests is not None and r.requests >= 0

    # Check a specific record
    priya_first = [r for r in records if r.user_email == "priya.nair@meridianls.example" and r.date == "2026-08-03" and r.model == "claude-opus-5-5"][0]
    assert priya_first.total_tokens == 57516
    assert priya_first.requests == 7
    # Amount was 88.900050 cents tokens + 1.000000 cents web_search = 89.900050 cents = $0.899001 USD
    assert pytest.approx(priya_first.cost_usd, 0.0001) == 0.899001

def test_gemini_ingestion():
    directory = load_directory(DATA_DIR)
    records = ingest_gemini_data(DATA_DIR, directory)
    # 990 rows paired into 495 aggregated records
    assert len(records) == 495

    for r in records:
        assert r.platform == "gemini"
        assert r.user_id.startswith("user_")
        assert r.group_id in [g.group_id for g in directory.groups]
        assert r.total_tokens == r.input_tokens + r.output_tokens
        assert r.cost_usd >= 0.0
        assert r.requests is None # GCP BigQuery billing export does not provide request count

def test_unified_ingestion_engine():
    engine = IngestionEngine(DATA_DIR)
    directory, records = engine.run_ingestion()
    assert len(directory.users) == 22
    assert len(records) == 1841 # 1346 claude + 495 gemini

    total_tokens = sum(r.total_tokens for r in records)
    total_cost = sum(r.cost_usd for r in records)
    assert total_tokens == 370311940
    assert pytest.approx(total_cost, 0.01) == 3118.13
