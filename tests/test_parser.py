#!/usr/bin/env python3
"""FabAssetsManager — Parser Tests

Version: 0.13.5
"""
from models import Asset


def test_asset_parser_complete():
    raw_asset = {
        "listing": {
            "uid":
            "test-uid-123",
            "title":
            "Super Asset",
            "publisher": {
                "sellerName": "Dev Studio"
            },
            "assetFormats":
            [{
                "assetFormatType": {
                    "name": "Blender",
                    "code": "blender"
                },
                "technicalSpecs": {
                    "unrealEngineEngineVersions": ["UE_5.3", "UE_5.4"]
                }
            }],
            "thumbnails": [{
                "images": [{
                    "url": "http://img.com/small.jpg",
                    "width": 160
                }, {
                    "url": "http://img.com/main.jpg",
                    "width": 320
                }]
            }]
        },
        "entitlement": {
            "licenses": [{
                "name": "Standard License"
            }, {
                "name": "Personal"
            }]
        },
        "createdAt": "2026-01-01T00:00:00Z",
        "canRequestDownloadUrl": True
    }

    flat = Asset(raw_asset).to_dict()

    assert flat["uid"] == "test-uid-123"
    assert flat["title"] == "Super Asset"
    assert flat["seller_name"] == "Dev Studio"
    assert flat["asset_formats"] == "Blender"
    assert flat["asset_format_codes"] == "blender"
    assert flat["thumbnail_url"] == "http://img.com/main.jpg"
    assert flat["engine_versions"] == "5.3, 5.4"
    assert flat["ue_max"] == "5.4"
    assert flat["licenses"] == "Standard License, Personal"
    assert flat["can_download"] is True


def test_asset_merge_detail_payload_nested_listing_non_regression():
    raw_asset = {"listing": {"uid": "uid-nested-1", "title": "Nested Payload Asset"}}
    details = {
        "listing": {
            "description": "Detailed description",
            "reviewCount": 7,
            "medias": [{
                "mediaUrl": "https://media.test/image-a.jpg"
            }],
            "user": {
                "sellerName": "Nested Seller"
            }
        },
        "status": "ACTIVE",
        "createdAt": "2026-04-13T10:00:00Z",
        "capabilities": {
            "requestDownloadUrl": True
        }
    }

    asset = Asset(raw_asset)
    merged = asset.merge_detail_payload(details)

    assert merged is True
    assert asset.has_detail_listing_payload is True
    assert asset.raw_data["status"] == "ACTIVE"
    assert asset.raw_data["createdAt"] == "2026-04-13T10:00:00Z"
    assert asset.raw_data["listing"]["description"] == "Detailed description"

    flat = asset.to_dict()
    assert flat["description"] == "Detailed description"
    assert flat["seller_name"] == "Nested Seller"
    assert flat["review_count"] == 7
    assert flat["media_urls"] == ["https://media.test/image-a.jpg"]


def test_asset_merge_detail_payload_direct_listing_non_regression():
    raw_asset = {"listing": {"uid": "uid-direct-1", "title": "Direct Payload Asset"}}
    direct_listing_payload = {"description": "Direct description", "reviewCount": 2, "medias": [{"mediaUrl": "https://media.test/image-b.jpg"}]}

    asset = Asset(raw_asset)
    merged = asset.merge_detail_payload(direct_listing_payload)

    assert merged is True
    assert asset.has_detail_listing_payload is True
    assert asset.raw_data["listing"]["description"] == "Direct description"

    flat = asset.to_dict()
    assert flat["description"] == "Direct description"
    assert flat["review_count"] == 2
    assert flat["media_urls"] == ["https://media.test/image-b.jpg"]


def test_asset_to_dict_schema_non_regression():
    asset = Asset({"listing": {"uid": "schema-uid", "title": "Schema Asset"}})

    expected_keys = {
        "uid", "title", "seller_name", "seller_id", "seller_avatar_url", "listing_type", "created_at", "last_updated_at", "is_mature", "status",
        "asset_formats", "asset_format_codes", "tags", "description", "average_rating", "price", "currency_code", "discounted_price", "media_count",
        "image_count", "licenses", "engine_versions", "ue_max", "thumbnail_url", "image_urls", "can_download", "fab_url", "details_fetched",
        "details_updated_at", "technical_specs", "media_urls", "review_count",
    }

    assert set(asset.to_dict().keys()) == expected_keys
