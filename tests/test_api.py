#!/usr/bin/env python3
"""
Version: 0.13.3
"""
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
