#!/usr/bin/env python3
"""FabAssetsManager — Cache Tests

Version: 0.13.4
"""
import pytest
import cache_manager


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    assets_dir = tmp_path / "assets"
    last_update_file = tmp_path / "last_update.txt"
    import app
    monkeypatch.setattr(app, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(app, "LAST_UPDATE_FILE", last_update_file)
    return assets_dir


def test_save_and_get_asset(temp_cache):
    fake_asset = {"listing": {"uid": "test-1234", "title": "Test Asset"}, "createdAt": "2026-04-13T10:00:00"}
    cache_manager.save_asset(fake_asset)

    # Verify file was created
    assert (temp_cache / "test-1234.json").exists()

    # Verify it can be loaded specifically
    loaded = cache_manager.get_asset("test-1234")
    assert loaded is not None
    assert loaded["listing"]["title"] == "Test Asset"


def test_load_all_assets(temp_cache):
    cache_manager.save_asset({"listing": {"uid": "1", "title": "A1"}})
    cache_manager.save_asset({"listing": {"uid": "2", "title": "A2"}})

    assets = cache_manager.load_all_assets()
    assert len(assets) == 2
    uids = [a.get("listing", {}).get("uid") for a in assets]
    assert "1" in uids and "2" in uids


def test_metadata(temp_cache):
    cache_manager.save_update_metadata(42, "2026-04-13T00:00:00")
    meta = cache_manager.load_update_metadata()

    assert meta.get("count") == "42"
    assert meta.get("oldest_created_at") == "2026-04-13T00:00:00"
    assert "last_update" in meta
