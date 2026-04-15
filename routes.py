#!/usr/bin/env python3
"""FabAssetsManager — API and web routes

Version: 0.13.4
"""

import csv
import io
import json
from datetime import datetime

from flask import Blueprint, Response, jsonify, request, send_from_directory

from errors import ErrorCode
from models import Asset

bp = Blueprint("main", __name__)


def _app_module():
    """Access the runtime app module to avoid circular imports and keep monkeypatch compatibility in tests."""
    import importlib

    return importlib.import_module("app")


@bp.route("/")
def index():
    return send_from_directory("static", "index.html")


@bp.route("/api/export-templates")
def api_export_templates():
    import os

    path = os.path.join("config", "export_templates.json")
    _app = _app_module()
    _app.logger.info("Export templates requested")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})


@bp.route("/api/assets")
def api_assets():
    _app = _app_module()
    assets = _app.get_assets()
    flat = [Asset(a).to_dict() for a in assets]
    return jsonify(flat)


@bp.route("/api/lookup", methods=["GET"])
def api_lookup():
    """Lookup a cached asset by uid, name, or url.

    Query params:
        uid: exact Fab UID
        name: title search (case-insensitive substring match)
        url: Fab listing URL or raw UID extracted from URL
    """
    _app = _app_module()
    uid = request.args.get("uid", "")
    name = request.args.get("name", "")
    url = request.args.get("url", "")

    if not any((uid.strip(), name.strip(), url.strip())):
        return _app.create_error_response(
            ErrorCode.MISSING_PARAMETER,
            message="Required parameter missing. Provide at least one of: uid, name, or url",
            details={"expected_parameters": ["uid", "name", "url"]}
        )

    matches = _app.lookup_assets(uid=uid, name=name, url=url)
    return jsonify(
        {
            "query": {
                "uid": uid.strip(),
                "name": name.strip(),
                "url": url.strip(),
                "normalized_uid": _app.normalize_lookup_uid_from_url(url),
            },
            "count": len(matches),
            "matches": matches,
        }
    )


@bp.route("/api/config", methods=["GET"])
def api_config():
    """Return current config (partially masks cookies)."""
    _app = _app_module()
    cookies, user_agent = _app.load_config()
    log_level, log_output = _app.get_logging_settings()
    return jsonify(
        {
            "has_cookies": bool(cookies),
            "has_user_agent": bool(user_agent),
            "user_agent": user_agent or "",
            "cookies_preview": (cookies[:40] + "...") if cookies else "",
            "log_level": log_level,
            "log_output": log_output,
            "debug_mode": log_level == "DEBUG",
        }
    )


@bp.route("/api/config", methods=["POST"])
def api_config_save():
    """Update cookies + user_agent from the web interface."""
    _app = _app_module()
    data = request.get_json()
    cookies = data.get("cookies", "").strip()
    user_agent = data.get("user_agent", "").strip()
    log_level = str(data.get("log_level", "INFO")).upper()
    log_output = str(data.get("log_output", "Both"))
    if not cookies:
        return _app.create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies are required to configure the connection to Fab.com",
            details={"hint": "Paste your browser cookies from DevTools → Network → Request Headers"}
        )
    _app.save_config(cookies, user_agent)
    _app.save_logging_settings(log_level, log_output)
    _app.configure_logger(log_level, log_output)
    return jsonify({"message": "Configuration saved"})


@bp.route("/api/config/logging", methods=["POST"])
def api_config_logging_save():
    """Persist logging UI options and reconfigure logger immediately."""
    _app = _app_module()
    data = request.get_json() or {}
    log_level = str(data.get("level", "INFO")).upper()
    log_output = str(data.get("output", "Both"))
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        log_level = "INFO"
    if log_output not in {"Console", "File", "Both"}:
        log_output = "Both"

    _app.save_logging_settings(log_level, log_output)
    _app.configure_logger(log_level, log_output)
    return jsonify({"message": "Logging configuration saved", "level": log_level, "output": log_output})


@bp.route("/api/test")
def api_test():
    """Test route to verify Flask works."""
    return jsonify({"status": "OK", "message": "Flask is working correctly"})


@bp.route("/api/fetch", methods=["POST"])
def api_fetch():
    """Fetch fresh data from fab.com — uses config files if available."""
    _app = _app_module()
    data = request.get_json() or {}
    cookies = data.get("cookies", "").strip()
    user_agent = data.get("user_agent", "").strip()
    debug_mode = bool(data.get("debug", False))
    refresh_mode = data.get("refresh_mode", "partial")  # "partial" or "full"

    _app.logger.info(f"\n🔄 /api/fetch called (mode: {refresh_mode}):")
    _app.logger.info(f"   - Cookies received: {'Yes (' + str(len(cookies)) + ' chars)' if cookies else 'No'}")
    _app.logger.info(f"   - User-Agent received: {'Yes' if user_agent else 'No'}")
    _app.logger.info(f"   - Debug mode: {debug_mode}")

    # Fallback to config files
    if not cookies or not user_agent:
        _app.logger.info("   → Fallback to config files...")
        saved_cookies, saved_ua = _app.load_config()
        cookies = cookies or saved_cookies or ""
        user_agent = user_agent or saved_ua or ""
        _app.logger.info(f"   → Config loaded: cookies={'OK' if saved_cookies else 'MISSING'}, UA={'OK' if saved_ua else 'MISSING'}")

    if not cookies:
        _app.logger.info("   ❌ Cookies missing after fallback")
        return _app.create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies not configured. Configure via web interface or create config/cookies.txt",
            context={"tried_interactive_fallback": True}
        )

    _app.logger.info(f"   ✅ Final config: {len(cookies)} chars cookies, {len(user_agent)} chars UA")

    # Get last update metadata
    metadata = _app.load_update_metadata()
    last_update_date = ""

    if refresh_mode == "partial" and metadata.get("last_update"):
        last_update_date = metadata.get("oldest_created_at", "")
        if last_update_date:
            _app.logger.info(f"   📅 Partial update mode: stopping before {last_update_date}")

    _app.logger.info("   🚀 Calling fetch_all_assets...")
    assets = _app.fetch_all_assets(cookies, user_agent=user_agent, debug=debug_mode, last_update_date=last_update_date)

    if not assets and refresh_mode == "full":
        _app.logger.info("   ❌ No assets retrieved (probably 403 error)")
        return _app.create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Failed to fetch assets from Fab.com (HTTP 403 or invalid cookies)",
            details={"hint": "Verify that your cookies are still valid and haven't expired"}
        )

    if not assets and refresh_mode == "partial":
        _app.logger.info("   ℹ️ No new assets found (library is up to date)")
        return jsonify(
            {
                "count": 0,
                "total_cached": len(_app.load_all_assets()),
                "message": "No new assets — your library is up to date!",
                "mode": refresh_mode,
                "timestamp": datetime.now().isoformat()
            }
        )

    # Find oldest createdAt date from fetched assets
    oldest_created = max((a.get("createdAt", "") for a in assets), default="")

    _app.logger.info(f"   ✅ {len(assets)} new/updated assets fetched")

    # Save each asset individually to assets/<UID>.json
    for asset in assets:
        _app.save_asset(asset)

    # Save metadata
    total_cached = len(_app.load_all_assets())
    _app.save_update_metadata(total_cached, oldest_created)

    _app.logger.info(f"   ✅ Assets saved to individual files (total: {total_cached})")
    return jsonify(
        {
            "count": len(assets),
            "total_cached": total_cached,
            "message": f"{len(assets)} new/updated, {total_cached} total",
            "mode": refresh_mode,
            "timestamp": datetime.now().isoformat()
        }
    )


@bp.route("/api/details/<uid>", methods=["GET"])
def api_details(uid):
    """Fetch additional details for a specific asset and update cache."""
    _app = _app_module()
    asset = _app.get_asset(uid)
    if not asset:
        return _app.create_error_response(
            ErrorCode.ASSET_NOT_FOUND, message=f"Asset with UID '{uid}' not found in cache", details={"requested_uid": uid}
        )

    asset_model = Asset(asset)

    # If details already fetched and payload is complete, return cached flattened version
    if asset.get("details_fetched") and asset_model.has_detail_listing_payload:
        return jsonify(asset_model.to_dict())

    if asset.get("details_fetched") and not asset_model.has_detail_listing_payload:
        _app.logger.info(f"⚠️ Stale details flag detected for {uid} — forcing refetch")

    # Get configuration silently
    cookies, user_agent = _app.load_config()
    if not cookies:
        return _app.create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies not configured. Cannot fetch asset details from Fab.com without authentication",
            details={"endpoint": f"/api/details/{uid}"}
        )

    # Fetch details from API
    details = _app.fetch_asset_details(uid, cookies, str(user_agent), debug=False)
    if not details:
        return _app.create_error_response(
            ErrorCode.DETAIL_FETCH_FAILED,
            message=f"Failed to fetch details from Fab.com API for asset '{uid}'",
            details={
                "uid": uid,
                "endpoint": "https://api.fab.com/i/listings/{uid}"
            }
        )

    # Merge details and update detail metadata
    if not asset_model.merge_detail_payload(details):
        return _app.create_error_response(
            ErrorCode.CORRUPTED_ASSET_DATA,
            message="Unexpected detail payload structure from Fab.com API",
            details={
                "uid": uid,
                "received_keys": list(details.keys()) if isinstance(details, dict) else type(details).__name__
            }
        )

    asset["details_fetched"] = asset_model.has_detail_listing_payload
    asset["details_updated_at"] = datetime.now().isoformat()

    # Save to JSON
    _app.save_asset(asset)

    # Needs to clear in-memory _assets_cache if we were using a global variable, but get_assets() loads individually each time
    return jsonify(asset_model.to_dict())


@bp.route("/api/missing_details", methods=["GET", "POST"])
def api_missing_details():
    """Return a list of UIDs that don't have details fetched yet.

    Can be accessed via GET with 'uids' query parameter or POST with a JSON body
    containing a list of 'uids'.

    Query params / JSON payload:
        uids: list or comma-separated list of UIDs to check (optional).
              If provided, only check these UIDs.
              If omitted, check all cached assets.
    """
    _app = _app_module()
    selected_uids = []

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        selected_uids = data.get("uids", [])
    else:
        uids_param = request.args.get("uids", "").strip()
        selected_uids = [u.strip() for u in uids_param.split(",") if u.strip()] if uids_param else []

    if selected_uids:
        # Only check the requested UIDs
        missing_uids = []
        for uid in selected_uids:
            asset = _app.get_asset(uid)
            has_details = bool(asset and asset.get("details_fetched") and Asset(asset).has_detail_listing_payload)
            if asset and not has_details and asset.get("listing", {}).get("uid"):
                missing_uids.append(uid)
    else:
        # Check all cached assets
        assets = _app.load_all_assets()
        missing_uids = [
            a.get("listing", {}).get("uid")
            for a in assets
            if not (a.get("details_fetched") and Asset(a).has_detail_listing_payload) and a.get("listing", {}).get("uid")
        ]

    return jsonify(missing_uids)


@bp.route("/api/cache-info", methods=["GET"])
def api_cache_info():
    """Returns cache information."""
    _app = _app_module()
    metadata = _app.load_update_metadata()

    if not metadata:
        return jsonify({"has_cache": False, "count": 0, "timestamp": None, "last_sync_at": None, "last_sync_label": None, "age_seconds": None})

    timestamp = metadata.get("last_update", "")
    count = int(metadata.get("count", "0"))
    last_sync_label = None

    if timestamp:
        try:
            last_sync_label = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            last_sync_label = timestamp

    age_seconds = 0
    if timestamp:
        try:
            age_seconds = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds()
        except Exception:
            pass

    return jsonify(
        {
            "has_cache": True,
            "count": count,
            "timestamp": timestamp,
            "last_sync_at": timestamp,
            "last_sync_label": last_sync_label,
            "age_seconds": age_seconds,
            "age_human": f"{int(age_seconds // 3600)}h {int((age_seconds % 3600) // 60)}m" if age_seconds else None
        }
    )


@bp.route("/api/clear_previews", methods=["POST"])
def clear_previews():
    _app = _app_module()
    try:
        deleted_count = 0
        if _app.PREVIEWS_DIR.exists():
            for file in _app.PREVIEWS_DIR.iterdir():
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        return jsonify({"status": "success", "message": f"Successfully deleted {deleted_count} preview image(s).", "deleted_count": deleted_count})
    except Exception as e:
        _app.logger.error(f"Error clearing previews: {e}", exc_info=True)
        return _app.create_error_response(ErrorCode.CACHE_ERROR, message=f"Failed to clear previews: {str(e)}", details={"error": str(e)})


@bp.route("/api/clear_cache", methods=["POST"])
def clear_cache():
    _app = _app_module()
    try:
        deleted_count = 0
        # Delete asset json files
        if _app.ASSETS_DIR.exists():
            for file in _app.ASSETS_DIR.glob("*.json"):
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        # Delete last_update file
        if _app.LAST_UPDATE_FILE.exists():
            _app.LAST_UPDATE_FILE.unlink()

        return jsonify(
            {
                "status": "success",
                "message": f"Successfully deleted {deleted_count} cached asset(s) and reset cache state.",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        _app.logger.error(f"Error clearing cache: {e}", exc_info=True)
        return _app.create_error_response(ErrorCode.CACHE_ERROR, message=f"Failed to clear cache: {str(e)}", details={"error": str(e)})


@bp.route("/api/export/json", methods=["POST"])
def export_json():
    """Export JSON with optional filtering by selected UIDs."""
    _app = _app_module()
    data = request.get_json() or {}
    selected_uids = data.get("selected_uids", [])

    assets = _app.get_assets()

    # Filter if selected UIDs were provided
    if selected_uids:
        assets = [a for a in assets if a.get("listing", {}).get("uid") in selected_uids]

    flat = [Asset(a).to_dict() for a in assets]
    return Response(
        json.dumps(flat, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=fab_library_{len(flat)}_items.json"},
    )


@bp.route("/api/export/csv", methods=["POST"])
def export_csv():
    """Export CSV with optional filtering by selected UIDs."""
    _app = _app_module()
    data = request.get_json() or {}
    selected_uids = data.get("selected_uids", [])
    columns = data.get("columns", [])

    assets = _app.get_assets()

    # Filter if selected UIDs were provided
    if selected_uids:
        assets = [a for a in assets if a.get("listing", {}).get("uid") in selected_uids]

    flat = [Asset(a).to_dict() for a in assets]
    if not flat:
        # If no assets found and UIDs were provided, it's an error
        if selected_uids:
            return _app.create_error_response(
                ErrorCode.NO_RESULTS, message="No assets found for the requested UIDs", details={"requested_uids": selected_uids}
            )
        return _app.create_error_response(ErrorCode.NO_RESULTS, message="No assets available in cache")

    if columns:
        fieldnames = [c for c in columns if isinstance(c, str) and c]
    else:
        fieldnames = list(flat[0].keys())

    if "uid" in fieldnames:
        fieldnames = ["uid"] + [c for c in fieldnames if c != "uid"]
    else:
        fieldnames = ["uid"] + fieldnames

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for asset in flat:
        writer.writerow({key: asset.get(key, "") for key in fieldnames})
    return Response(
        output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=fab_library_{len(flat)}_items.csv"},
    )


@bp.route("/api/status")
def api_status():
    _app = _app_module()
    assets = _app.get_assets()
    return jsonify({"cached": len(assets), "has_cache": len(assets) > 0})


@bp.route("/api/image/<uid>", methods=["GET"])
def get_image(uid: str):
    """Serve cached preview image or lazy-download it on first access.

    Implements a lazy-loading strategy for preview images:
    1. If image already cached locally (previews/<UID>.jpg), serve immediately
    2. Otherwise, find asset in cache, extract thumbnail_url, download from fab.com
    3. Save download to local cache for future requests (persistent across sessions)
    4. Return image data to browser

    This approach ensures:
    - Fast page load (no image blocking, lazy trigger on click)
    - No redundant downloads (persistent cache)
    - Small memory footprint (streaming, not loading all images)
    - Resumable sessions (cache survives app restart)

    Args:
        uid: Asset unique identifier (from listing.uid)

    Returns:
        - 200 OK + JPEG image data if successful
        - 404 if asset or thumbnail not found
        - 400/500 if image download fails

    Example:
        GET /api/image/001d83fe-a1b2-4c3d-... → returns JPEG bytes or cached file

    Performance:
        - First access: ~200-500ms (download from fab.com)
        - Subsequent accesses: <10ms (serve from disk cache)
    """
    import requests

    _app = _app_module()

    # Build path to cached preview file (one file per asset)
    # Format: previews/<UID>.jpg (JPEG format used for all thumbnails)
    preview_file = _app.PREVIEWS_DIR / f"{uid}.jpg"

    # ─────────────────────────────────────────────────────────────
    # CACHE CHECK: If image already downloaded, serve from disk cache
    # ─────────────────────────────────────────────────────────────
    if preview_file.exists():
        # File exists in cache → serve immediately without re-downloading
        # This handles the common case after first access (95% of requests)
        return send_from_directory(_app.PREVIEWS_DIR, f"{uid}.jpg")

    # ─────────────────────────────────────────────────────────────
    # FIRST ACCESS: Find asset and extract thumbnail URL
    # ─────────────────────────────────────────────────────────────
    # Load all assets from individual cache files
    assets = _app.load_all_assets()
    asset = None

    # Linear search for matching UID (acceptable for 3480 assets)
    # Could optimize with indexed cache if > 10k assets
    for a in assets:
        if a.get("listing", {}).get("uid") == uid:
            asset = a
            break

    if not asset:
        # Asset not found in cache (shouldn't happen if UID is valid)
        return jsonify({"error": "Asset not found"}), 404

    # ─────────────────────────────────────────────────────────────
    # EXTRACT THUMBNAIL: Get image URL from flattened asset
    # ─────────────────────────────────────────────────────────────
    # Asset() extracts thumbnail_url following priority:
    # 1. 320x180 image (standard preview size)
    # 2. First available image (fallback)
    # 3. Empty string if no images
    flat = Asset(asset).to_dict()
    thumbnail_url = flat.get("thumbnail_url", "")

    if not thumbnail_url:
        # No image available for this asset (rare, but possible)
        return _app.create_error_response(ErrorCode.NOT_FOUND, message=f"No thumbnail image available for asset '{uid}'", details={"uid": uid})

    # ─────────────────────────────────────────────────────────────
    # DOWNLOAD & CACHE: Fetch image from fab.com and save locally
    # ─────────────────────────────────────────────────────────────
    try:
        # Request image from fab.com with 10-second timeout
        resp = requests.get(thumbnail_url, timeout=10)

        # Check for successful HTTP 200 response
        if resp.status_code == 200:
            # Save to local cache (binary JPEG data)
            # Subsequent requests will serve from cache (see above)
            preview_file.write_bytes(resp.content)

            # Return downloaded image data to browser
            return Response(resp.content, mimetype="image/jpeg")

        # HTTP error (403, 404, 500, etc.)
        # This shouldn't happen if fab.com API is healthy
        return _app.create_error_response(
            ErrorCode.CONNECTION_ERROR,
            message=f"Failed to download image from Fab.com (HTTP {resp.status_code})",
            details={
                "uid": uid,
                "thumbnail_url": thumbnail_url,
                "http_status": resp.status_code
            }
        )
    except Exception as e:
        # Network error: timeout, connection refused, DNS failure, etc.
        # Log and return error (UI will display placeholder)
        return _app.create_error_response(
            ErrorCode.CONNECTION_ERROR,
            message="Network error while downloading image from Fab.com",
            details={
                "uid": uid,
                "error_type": type(e).__name__
            },
            context={"error_message": str(e)}
        )
