# ============================================================================
# FabAssetsManager - Export Tests
# ============================================================================
# Description: Unit tests for JSON, CSV, and Headless export endpoints.
# Version: 1.1.1
# ============================================================================

import pytest
import app
import json

DUMMY_ASSETS = [{"listing": {"uid": "1", "title": "Asset 1"}}, {"listing": {"uid": "2", "title": "Asset 2"}}, ]


@pytest.fixture
def mock_assets(monkeypatch):
    monkeypatch.setattr(app, "get_assets", lambda: DUMMY_ASSETS)
    return DUMMY_ASSETS


def test_export_json(client, mock_assets):
    resp = client.post("/api/export/json")
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]["uid"] == "1"


def test_export_csv(client, mock_assets):
    resp = client.post("/api/export/csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    text = resp.get_data(as_text=True)
    assert "uid,title" in text
    assert "1,Asset 1" in text


def test_export_headless(client, mock_assets, tmp_path):
    output_path = tmp_path / "test_export.json"
    payload = {"output_path": str(output_path), "format": "json"}
    resp = client.post("/api/export/headless", json=payload)
    assert resp.status_code == 200
    assert output_path.exists()

    with open(output_path, "r") as f:
        data = json.load(f)
        assert len(data) == 2
