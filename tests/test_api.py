#!/usr/bin/env python3
"""FabAssetsManager — API Tests

Version: 0.13.6
"""
from pathlib import Path

import pytest
import app


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200


def test_api_test_route(client):
    response = client.get('/api/test')
    assert response.status_code == 200
    assert response.json == {"status": "OK", "message": "Flask is working correctly"}


def test_api_status(client, monkeypatch):
    # Mock get_assets to return an empty list
    monkeypatch.setattr(app, "get_assets", lambda: [])
    response = client.get('/api/status')
    assert response.status_code == 200
    assert response.json == {"cached": 0, "has_cache": False}

    # Mock get_assets to return some dummy data
    monkeypatch.setattr(app, "get_assets", lambda: [{"listing": {"uid": "1"}}])
    response = client.get('/api/status')
    assert response.json == {"cached": 1, "has_cache": True}


def test_api_assets(client, monkeypatch):
    dummy_assets = [{"listing": {"uid": "123", "title": "Mocked Asset", }}]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)
    response = client.get('/api/assets')
    assert response.status_code == 200
    data = response.json
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["uid"] == "123"
    assert data[0]["title"] == "Mocked Asset"


def test_api_lookup_by_uid(client, monkeypatch):
    dummy_assets = [{"listing": {"uid": "uid-123", "title": "Alpha Asset"}}, {"listing": {"uid": "uid-456", "title": "Beta Asset"}}, ]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    response = client.get('/api/lookup?uid=uid-456')
    assert response.status_code == 200
    data = response.json
    assert data["count"] == 1
    assert data["matches"][0]["uid"] == "uid-456"


def test_api_lookup_by_name_and_url(client, monkeypatch):
    dummy_assets = [
        {
            "listing": {
                "uid": "uid-123",
                "title": "Stylized Dungeon Props Pack"
            }
        }, {
            "listing": {
                "uid": "uid-456",
                "title": "Stylized Dungeon Props Pack Extended"
            }
        },
    ]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    by_name = client.get('/api/lookup?name=dungeon props')
    assert by_name.status_code == 200
    assert by_name.json["count"] == 2

    by_url = client.get('/api/lookup?url=https://www.fab.com/listings/uid-123')
    assert by_url.status_code == 200
    assert by_url.json["count"] == 1
    assert by_url.json["matches"][0]["uid"] == "uid-123"


def test_api_config_rejects_invalid_json_payload(client):
    response = client.post('/api/config', data='{"cookies":', content_type='application/json')

    assert response.status_code == 400
    assert response.json["error"]["code"] == "INVALID_REQUEST"
    assert response.json["error"]["path"] == "/api/config"


def test_api_diagnostic(client, monkeypatch, tmp_path):
    assets_dir = tmp_path / "assets"
    previews_dir = tmp_path / "previews"
    config_dir = tmp_path / "config"
    assets_dir.mkdir()
    previews_dir.mkdir()
    config_dir.mkdir()

    (assets_dir / "one.json").write_text('{"listing": {"uid": "u1"}}', encoding='utf-8')
    (previews_dir / "one.jpg").write_bytes(b"jpg")

    monkeypatch.setattr(app, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(app, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(app, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(app, "load_config", lambda: ("cookie=abc", "ua-test"))
    monkeypatch.setattr(app, "load_update_metadata", lambda: {"count": "1", "last_update": "2026-04-15T00:00:00"})

    response = client.get('/api/diagnostic')
    assert response.status_code == 200
    assert response.json["auth"]["cookies_present"] is True
    assert response.json["storage"]["assets_dir"]["files_count"] == 1
    assert response.json["storage"]["previews_dir"]["files_count"] == 1
    assert response.json["cache"]["reported_count"] == 1


def test_api_export_headless_json(client, monkeypatch, tmp_path):
    dummy_assets = [{"listing": {"uid": "uid-1", "title": "Asset One"}}]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    out_file = tmp_path / "export.json"
    response = client.post('/api/export/headless', json={"format": "json", "output_path": str(out_file)})

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert out_file.exists()
    content = out_file.read_text(encoding='utf-8')
    assert "uid-1" in content


def test_api_export_headless_invalid_format_has_error_path(client):
    response = client.post('/api/export/headless', json={"format": "xml", "output_path": str(Path("out.xml"))})

    assert response.status_code == 400
    assert response.json["error"]["code"] == "INVALID_REQUEST"
    assert response.json["error"]["path"] == "/api/export/headless"


def test_api_assets_query_pagination_and_sort(client, monkeypatch):
    dummy_assets = [
        {
            "createdAt": "2026-01-01T10:00:00",
            "canRequestDownloadUrl": True,
            "entitlement": {
                "licenses": [{
                    "name": "Personal"
                }]
            },
            "listing": {
                "uid": "u-beta",
                "title": "Beta Asset",
                "publisher": {
                    "sellerName": "Seller B",
                    "sellerId": "s-b"
                },
                "listingType": "3D Model",
                "assetFormats": [{
                    "assetFormatType": {
                        "name": "FBX",
                        "code": "fbx"
                    },
                    "technicalSpecs": {
                        "unrealEngineEngineVersions": ["UE_5.1"]
                    }
                }],
                "startingPrice": {
                    "price": 10,
                    "discountedPrice": 8,
                    "currencyCode": "USD"
                },
                "isMature": False,
                "lastUpdatedAt": "2026-01-02T10:00:00"
            }
        }, {
            "createdAt": "2026-01-03T10:00:00",
            "canRequestDownloadUrl": True,
            "entitlement": {
                "licenses": [{
                    "name": "Personal"
                }]
            },
            "listing": {
                "uid": "u-alpha",
                "title": "Alpha Asset",
                "publisher": {
                    "sellerName": "Seller A",
                    "sellerId": "s-a"
                },
                "listingType": "Material",
                "assetFormats": [{
                    "assetFormatType": {
                        "name": "Unreal",
                        "code": "ue"
                    },
                    "technicalSpecs": {
                        "unrealEngineEngineVersions": ["UE_5.3"]
                    }
                }],
                "startingPrice": {
                    "price": 20,
                    "discountedPrice": 20,
                    "currencyCode": "USD"
                },
                "isMature": False,
                "lastUpdatedAt": "2026-01-04T10:00:00"
            }
        }
    ]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    response = client.post('/api/assets/query', json={"page": 0, "per_page": 1, "sort": "title_asc", "search": "", "filters": {}})

    assert response.status_code == 200
    data = response.json
    assert data["total_count"] == 2
    assert data["filtered_count"] == 2
    assert data["page_count"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["uid"] == "u-alpha"


def test_api_assets_query_filters_and_all_uids(client, monkeypatch):
    dummy_assets = [
        {
            "createdAt": "2026-01-01T10:00:00",
            "canRequestDownloadUrl": False,
            "entitlement": {
                "licenses": [{
                    "name": "Personal"
                }]
            },
            "listing": {
                "uid": "u-1",
                "title": "First",
                "publisher": {
                    "sellerName": "Seller A",
                    "sellerId": "s-a"
                },
                "listingType": "3D Model",
                "assetFormats": [{
                    "assetFormatType": {
                        "name": "FBX",
                        "code": "fbx"
                    },
                    "technicalSpecs": {
                        "unrealEngineEngineVersions": ["UE_5.1"]
                    }
                }],
                "startingPrice": {
                    "price": 15,
                    "discountedPrice": 12,
                    "currencyCode": "USD"
                },
                "isMature": False
            }
        }, {
            "createdAt": "2026-01-02T10:00:00",
            "canRequestDownloadUrl": True,
            "entitlement": {
                "licenses": [{
                    "name": "Personal"
                }]
            },
            "listing": {
                "uid": "u-2",
                "title": "Second",
                "publisher": {
                    "sellerName": "Seller B",
                    "sellerId": "s-b"
                },
                "listingType": "3D Model",
                "assetFormats": [{
                    "assetFormatType": {
                        "name": "Unreal",
                        "code": "ue"
                    },
                    "technicalSpecs": {
                        "unrealEngineEngineVersions": ["UE_5.3"]
                    }
                }],
                "startingPrice": {
                    "price": 30,
                    "discountedPrice": 20,
                    "currencyCode": "USD"
                },
                "isMature": False
            }
        }
    ]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    response = client.post(
        '/api/assets/query',
        json={
            "page": 0,
            "per_page": 50,
            "sort": "date_desc",
            "filters": {
                "engines": ["5.3"],
                "only_downloadable": True,
                "only_discounted": True,
                "hide_mature": True
            },
            "include_all_uids": True
        }
    )

    assert response.status_code == 200
    data = response.json
    assert data["filtered_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["uid"] == "u-2"
    assert data["all_uids"] == ["u-2"]


def test_api_assets_query_rejects_non_object_payload(client):
    response = client.post('/api/assets/query', json=["invalid"])

    assert response.status_code == 400
    assert response.json["error"]["code"] == "INVALID_REQUEST"
    assert response.json["error"]["path"] == "/api/assets/query"


def test_api_assets_query_clamps_page_to_last(client, monkeypatch):
    dummy_assets = [
        {
            "listing": {
                "uid": "u-a",
                "title": "A asset"
            }
        }, {
            "listing": {
                "uid": "u-b",
                "title": "B asset"
            }
        }, {
            "listing": {
                "uid": "u-c",
                "title": "C asset"
            }
        }
    ]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    response = client.post('/api/assets/query', json={"page": 99, "per_page": 2, "sort": "title_asc", "filters": {}})

    assert response.status_code == 200
    data = response.json
    assert data["page_count"] == 2
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["uid"] == "u-c"


def test_api_assets_query_include_all_items(client, monkeypatch):
    dummy_assets = [{"listing": {"uid": "u-b", "title": "Beta"}}, {"listing": {"uid": "u-a", "title": "Alpha"}}]
    monkeypatch.setattr(app, "get_assets", lambda: dummy_assets)

    response = client.post('/api/assets/query', json={"page": 0, "per_page": 1, "sort": "title_asc", "filters": {}, "include_all_items": True})

    assert response.status_code == 200
    data = response.json
    assert len(data["items"]) == 1
    assert data["items"][0]["uid"] == "u-a"
    assert [item["uid"] for item in data["all_items"]] == ["u-a", "u-b"]
