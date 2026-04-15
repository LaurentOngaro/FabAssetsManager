#!/usr/bin/env python3
"""
FabAssetsManager — Local Flask Server
Launch: python app.py
Then open: http://localhost:5002

NOTE: 5002 is the default port for the web interface, but the it can be changed in `config/config.json`

Version: 0.13.3
"""

import csv
import io
import json
import sys
import logging
import time
import re
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, Response, g
from fetch_fab_library import fetch_all_assets, fetch_asset_details
from models import Asset
from errors import ErrorCode, create_error_response
from cache_manager import (load_all_assets, save_asset, save_update_metadata, load_update_metadata, get_asset)

app = Flask(__name__, static_folder="static", static_url_path="")

APP_DIR = Path(__file__).parent

# Configuration setup
_DEFAULT_CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = _DEFAULT_CONFIG_DIR / "config.json"


def _init_settings() -> dict:
    default_settings = {
        "config_dir": "config",
        "assets_dir": "assets",
        "previews_dir": "previews",
        "cookies_file": "config/cookies.txt",
        "ua_file": "config/user_agent.txt",
        "log_file": "app.log",
        "last_update_file": "assets/last_update.txt",
        "server_port": 5002,
        "log_level": "INFO",
        "log_output": "Both",
        "log_max_bytes": 5 * 1024 * 1024,
        "log_backup_count": 2
    }

    if not CONFIG_FILE.exists():
        _DEFAULT_CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        CONFIG_FILE.write_text(json.dumps(default_settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return default_settings

    try:
        current_settings = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        modified = False
        for k, v in default_settings.items():
            if k not in current_settings:
                current_settings[k] = v
                modified = True
        if modified:
            CONFIG_FILE.write_text(json.dumps(current_settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return current_settings
    except (OSError, json.JSONDecodeError):
        return default_settings


_startup_settings = _init_settings()


def _resolve_path(path_value: object | None, default: Path) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        return default
    p = Path(path_value.strip())
    return p if p.is_absolute() else (APP_DIR / p).resolve()


# Configuration paths mapped from settings
CONFIG_DIR = _resolve_path(_startup_settings.get("config_dir"), _DEFAULT_CONFIG_DIR)
ASSETS_DIR = _resolve_path(_startup_settings.get("assets_dir"), APP_DIR / "assets")
PREVIEWS_DIR = _resolve_path(_startup_settings.get("previews_dir"), APP_DIR / "previews")

COOKIES_FILE = _resolve_path(_startup_settings.get("cookies_file"), CONFIG_DIR / "cookies.txt")
UA_FILE = _resolve_path(_startup_settings.get("ua_file"), CONFIG_DIR / "user_agent.txt")
LOG_FILE = _resolve_path(_startup_settings.get("log_file"), APP_DIR / "app.log")
LAST_UPDATE_FILE = _resolve_path(_startup_settings.get("last_update_file"), ASSETS_DIR / "last_update.txt")

# Create directories if needed
CONFIG_DIR.mkdir(exist_ok=True, parents=True)
ASSETS_DIR.mkdir(exist_ok=True, parents=True)
PREVIEWS_DIR.mkdir(exist_ok=True, parents=True)

# ─── Logging Setup ───────────────────────────────────────────
logger = logging.getLogger("FabAssetsManager")


def configure_logger(level_str="INFO", output_str="Both"):
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)

    # Remove all handlers to reconfigure
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    if output_str in ("Console", "Both"):
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    if output_str in ("File", "Both"):
        try:
            current_settings = load_settings() if 'load_settings' in globals() else _startup_settings
            max_bytes = current_settings.get("log_max_bytes", 5 * 1024 * 1024)
            backup_count = current_settings.get("log_backup_count", 2)
            fh = RotatingFileHandler(LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            logger.info(f"Failed to create file logger: {e}")


# ─── Read / write config files ───────────────────────────────
def load_config():
    """Load cookies and user_agent from files, or None if missing."""
    cookies = COOKIES_FILE.read_text(encoding="utf-8").strip() if COOKIES_FILE.exists() else None
    user_agent = UA_FILE.read_text(encoding="utf-8").strip() if UA_FILE.exists() else None
    if cookies:
        logger.info(f"✅ Cookies loaded from {COOKIES_FILE}")
    if user_agent:
        logger.info(f"✅ User-Agent loaded from {UA_FILE}")
    return cookies, user_agent


def save_config(cookies: str, user_agent: str):
    COOKIES_FILE.write_text(cookies.strip(), encoding="utf-8")
    UA_FILE.write_text(user_agent.strip(), encoding="utf-8")


def load_settings() -> dict:
    """Load UI settings from CONFIG_FILE."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict) -> None:
    """Persist UI settings to CONFIG_FILE."""
    CONFIG_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def get_logging_settings() -> tuple[str, str]:
    settings = load_settings()
    level = str(settings.get("log_level", "INFO")).upper()
    output = str(settings.get("log_output", "Both"))
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        level = "INFO"
    if output not in {"Console", "File", "Both"}:
        output = "Both"
    return level, output


def save_logging_settings(level: str, output: str) -> None:
    settings = load_settings()
    settings["log_level"] = level
    settings["log_output"] = output
    save_settings(settings)


def prompt_config():
    """Interactively request cookies + user-agent if files are missing."""
    cookies, user_agent = load_config()

    if not cookies:
        logger.error("\n" + "=" * 60)
        logger.error("🍪  No config/cookies.txt file found.")
        logger.error("    Log in to fab.com in your browser,")
        logger.error("    open DevTools (F12) → Network → click a request")
        logger.error("    → Request Headers → copy the 'cookie:' line")
        logger.error("=" * 60)
        cookies = input("\nPaste your cookie string here: ").strip()
        if not cookies:
            logger.error("❌ Cookies empty — aborting.")
            sys.exit(1)

    if not user_agent:
        logger.error("\n" + "=" * 60)
        logger.error("🌐  No config/user_agent.txt file found.")
        logger.error("    DevTools → Network → click a request")
        logger.error("    → Request Headers → copy the 'user-agent:' value")
        logger.error("=" * 60)
        user_agent = input("\nPaste your User-Agent string here (optional): ").strip()
        if not user_agent:
            logger.warning("⚠️  User-Agent empty — using generic UA (may fail).")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

    save_config(cookies, user_agent)
    logger.info("\n✅ Configuration saved to config/cookies.txt and config/user_agent.txt\n")
    return cookies, user_agent


# ─── Cache assets ─────────────────────────────────────────────────────────────
def get_assets():
    """Load all assets from individual cache files (assets/*.json)"""
    assets = load_all_assets()
    if assets:
        logger.info(f"✅ {len(assets)} assets loaded from individual cache files")
    return assets


def normalize_lookup_uid_from_url(value: str) -> str:
    """Extract a Fab asset UID from a URL or raw text."""
    if not value:
        return ""

    text = value.strip()
    uid_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", text)
    if uid_match:
        return uid_match.group(0).lower()

    try:
        parsed = urlparse(text)
    except Exception:
        return ""

    if not parsed.netloc and not parsed.path:
        return ""

    path = parsed.path or text
    path_match = re.search(r"/listings/([0-9a-fA-F-]{36})", path)
    if path_match:
        return path_match.group(1).lower()

    return ""


def lookup_assets(uid: str = "", name: str = "", url: str = "") -> list[dict]:
    """Return matching assets from the local cache using uid, name, or url."""
    assets = get_assets()
    matches: list[dict] = []

    uid = uid.strip().lower()
    name = name.strip().lower()
    url_uid = normalize_lookup_uid_from_url(url)
    target_uid = uid or url_uid

    for asset in assets:
        flat_asset = Asset(asset).to_dict()
        asset_uid = str(flat_asset.get("uid", "")).strip().lower()
        asset_title = str(flat_asset.get("title", "")).strip().lower()
        asset_url = str(flat_asset.get("fab_url", "")).strip().lower()

        if target_uid and asset_uid == target_uid:
            matches.append(flat_asset)
            continue

        if url and not target_uid:
            normalized_url = url.strip().lower()
            if normalized_url == asset_url or normalized_url in asset_url or asset_uid in normalized_url:
                matches.append(flat_asset)
                continue

        if name and (name == asset_title or name in asset_title):
            matches.append(flat_asset)

    if target_uid:
        matches.sort(key=lambda item: 0 if str(item.get("uid", "")).strip().lower() == target_uid else 1)
    elif name:
        matches.sort(key=lambda item: (0 if str(item.get("title", "")).strip().lower() == name else 1, str(item.get("title", "")).lower()))

    return matches


@app.before_request
def log_route_call():
    """Log every Flask route call at DEBUG level."""
    g.request_started_at = time.perf_counter()
    endpoint = request.endpoint or "unknown"
    logger.debug("route_call method=%s endpoint=%s path=%s args=%s", request.method, endpoint, request.path, dict(request.args), )


@app.after_request
def log_route_result(response):
    """Log route completion at DEBUG level."""
    started_at = getattr(g, "request_started_at", None)
    duration_ms = None
    if started_at is not None:
        duration_ms = (time.perf_counter() - started_at) * 1000
    endpoint = request.endpoint or "unknown"
    logger.debug(
        "route_done method=%s endpoint=%s status=%s duration_ms=%s", request.method, endpoint, response.status_code,
        f"{duration_ms:.2f}" if duration_ms is not None else "n/a",
    )
    return response


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/export-templates")
def api_export_templates():
    import os
    path = os.path.join("config", "export_templates.json")
    logger.info("Export templates requested")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route("/api/assets")
def api_assets():
    assets = get_assets()
    flat = [Asset(a).to_dict() for a in assets]
    return jsonify(flat)


@app.route("/api/lookup", methods=["GET"])
def api_lookup():
    """Lookup a cached asset by uid, name, or url.

    Query params:
        uid: exact Fab UID
        name: title search (case-insensitive substring match)
        url: Fab listing URL or raw UID extracted from URL
    """
    uid = request.args.get("uid", "")
    name = request.args.get("name", "")
    url = request.args.get("url", "")

    if not any((uid.strip(), name.strip(), url.strip())):
        return create_error_response(
            ErrorCode.MISSING_PARAMETER,
            message="Required parameter missing. Provide at least one of: uid, name, or url",
            details={"expected_parameters": ["uid", "name", "url"]}
        )

    matches = lookup_assets(uid=uid, name=name, url=url)
    return jsonify(
        {
            "query": {
                "uid": uid.strip(),
                "name": name.strip(),
                "url": url.strip(),
                "normalized_uid": normalize_lookup_uid_from_url(url),
            },
            "count": len(matches),
            "matches": matches,
        }
    )


@app.route("/api/config", methods=["GET"])
def api_config():
    """Return current config (partially masks cookies)."""
    cookies, user_agent = load_config()
    log_level, log_output = get_logging_settings()
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


@app.route("/api/config", methods=["POST"])
def api_config_save():
    """Update cookies + user_agent from the web interface."""
    global _assets_cache
    data = request.get_json()
    cookies = data.get("cookies", "").strip()
    user_agent = data.get("user_agent", "").strip()
    log_level = str(data.get("log_level", "INFO")).upper()
    log_output = str(data.get("log_output", "Both"))
    if not cookies:
        return create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies are required to configure the connection to Fab.com",
            details={"hint": "Paste your browser cookies from DevTools → Network → Request Headers"}
        )
    save_config(cookies, user_agent)
    save_logging_settings(log_level, log_output)
    configure_logger(log_level, log_output)
    return jsonify({"message": "Configuration saved"})


@app.route("/api/config/logging", methods=["POST"])
def api_config_logging_save():
    """Persist logging UI options and reconfigure logger immediately."""
    data = request.get_json() or {}
    log_level = str(data.get("level", "INFO")).upper()
    log_output = str(data.get("output", "Both"))
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        log_level = "INFO"
    if log_output not in {"Console", "File", "Both"}:
        log_output = "Both"

    save_logging_settings(log_level, log_output)
    configure_logger(log_level, log_output)
    return jsonify({"message": "Logging configuration saved", "level": log_level, "output": log_output})


@app.route("/api/test")
def api_test():
    """Test route to verify Flask works."""
    return jsonify({"status": "OK", "message": "Flask is working correctly"})


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """Fetch fresh data from fab.com — uses config files if available."""
    data = request.get_json() or {}
    cookies = data.get("cookies", "").strip()
    user_agent = data.get("user_agent", "").strip()
    debug_mode = bool(data.get("debug", False))
    refresh_mode = data.get("refresh_mode", "partial")  # "partial" or "full"

    logger.info(f"\n🔄 /api/fetch called (mode: {refresh_mode}):")
    logger.info(f"   - Cookies received: {'Yes (' + str(len(cookies)) + ' chars)' if cookies else 'No'}")
    logger.info(f"   - User-Agent received: {'Yes' if user_agent else 'No'}")
    logger.info(f"   - Debug mode: {debug_mode}")

    # Fallback to config files
    if not cookies or not user_agent:
        logger.info("   → Fallback to config files...")
        saved_cookies, saved_ua = load_config()
        cookies = cookies or saved_cookies or ""
        user_agent = user_agent or saved_ua or ""
        logger.info(f"   → Config loaded: cookies={'OK' if saved_cookies else 'MISSING'}, UA={'OK' if saved_ua else 'MISSING'}")

    if not cookies:
        logger.info("   ❌ Cookies missing after fallback")
        return create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies not configured. Configure via web interface or create config/cookies.txt",
            context={"tried_interactive_fallback": True}
        )

    logger.info(f"   ✅ Final config: {len(cookies)} chars cookies, {len(user_agent)} chars UA")

    # Get last update metadata
    metadata = load_update_metadata()
    last_update_date = ""

    if refresh_mode == "partial" and metadata.get("last_update"):
        last_update_date = metadata.get("oldest_created_at", "")
        if last_update_date:
            logger.info(f"   📅 Partial update mode: stopping before {last_update_date}")

    logger.info("   🚀 Calling fetch_all_assets...")
    assets = fetch_all_assets(cookies, user_agent=user_agent, debug=debug_mode, last_update_date=last_update_date)

    if not assets and refresh_mode == "full":
        logger.info("   ❌ No assets retrieved (probably 403 error)")
        return create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Failed to fetch assets from Fab.com (HTTP 403 or invalid cookies)",
            details={"hint": "Verify that your cookies are still valid and haven't expired"}
        )

    if not assets and refresh_mode == "partial":
        logger.info("   ℹ️ No new assets found (library is up to date)")
        return jsonify(
            {
                "count": 0,
                "total_cached": len(load_all_assets()),
                "message": "No new assets — your library is up to date!",
                "mode": refresh_mode,
                "timestamp": datetime.now().isoformat()
            }
        )

    # Find oldest createdAt date from fetched assets
    oldest_created = max((a.get("createdAt", "") for a in assets), default="")

    logger.info(f"   ✅ {len(assets)} new/updated assets fetched")

    # Save each asset individually to assets/<UID>.json
    for asset in assets:
        save_asset(asset)

    # Save metadata
    total_cached = len(load_all_assets())
    save_update_metadata(total_cached, oldest_created)

    logger.info(f"   ✅ Assets saved to individual files (total: {total_cached})")
    return jsonify(
        {
            "count": len(assets),
            "total_cached": total_cached,
            "message": f"{len(assets)} new/updated, {total_cached} total",
            "mode": refresh_mode,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.route("/api/details/<uid>", methods=["GET"])
def api_details(uid):
    """Fetch additional details for a specific asset and update cache."""
    asset = get_asset(uid)
    if not asset:
        return create_error_response(ErrorCode.ASSET_NOT_FOUND, message=f"Asset with UID '{uid}' not found in cache", details={"requested_uid": uid})

    asset_model = Asset(asset)

    # If details already fetched and payload is complete, return cached flattened version
    if asset.get("details_fetched") and asset_model.has_detail_listing_payload:
        return jsonify(asset_model.to_dict())

    if asset.get("details_fetched") and not asset_model.has_detail_listing_payload:
        logger.info(f"⚠️ Stale details flag detected for {uid} — forcing refetch")

    # Get configuration silently
    cookies, user_agent = load_config()
    if not cookies:
        return create_error_response(
            ErrorCode.UNAUTHORIZED,
            message="Cookies not configured. Cannot fetch asset details from Fab.com without authentication",
            details={"endpoint": f"/api/details/{uid}"}
        )

    # Fetch details from API
    details = fetch_asset_details(uid, cookies, str(user_agent), debug=False)
    if not details:
        return create_error_response(
            ErrorCode.DETAIL_FETCH_FAILED,
            message=f"Failed to fetch details from Fab.com API for asset '{uid}'",
            details={
                "uid": uid,
                "endpoint": "https://api.fab.com/i/listings/{uid}"
            }
        )

    # Merge details and update detail metadata
    if not asset_model.merge_detail_payload(details):
        return create_error_response(
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
    save_asset(asset)

    # Needs to clear in-memory _assets_cache if we were using a global variable, but get_assets() loads individually each time
    return jsonify(asset_model.to_dict())


@app.route("/api/missing_details", methods=["GET", "POST"])
def api_missing_details():
    """Return a list of UIDs that don't have details fetched yet.

    Can be accessed via GET with 'uids' query parameter or POST with a JSON body
    containing a list of 'uids'.

    Query params / JSON payload:
        uids: list or comma-separated list of UIDs to check (optional).
              If provided, only check these UIDs.
              If omitted, check all cached assets.
    """
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
            asset = get_asset(uid)
            has_details = bool(asset and asset.get("details_fetched") and Asset(asset).has_detail_listing_payload)
            if asset and not has_details and asset.get("listing", {}).get("uid"):
                missing_uids.append(uid)
    else:
        # Check all cached assets
        assets = load_all_assets()
        missing_uids = [
            a.get("listing", {}).get("uid")
            for a in assets
            if not (a.get("details_fetched") and Asset(a).has_detail_listing_payload) and a.get("listing", {}).get("uid")
        ]

    return jsonify(missing_uids)


@app.route("/api/cache-info", methods=["GET"])
def api_cache_info():
    """Returns cache information."""
    metadata = load_update_metadata()

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
        except (Exception):
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


@app.route("/api/clear_previews", methods=["POST"])
def clear_previews():
    try:
        deleted_count = 0
        if PREVIEWS_DIR.exists():
            for file in PREVIEWS_DIR.iterdir():
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        return jsonify({"status": "success", "message": f"Successfully deleted {deleted_count} preview image(s).", "deleted_count": deleted_count})
    except Exception as e:
        logger.error(f"Error clearing previews: {e}", exc_info=True)
        return create_error_response(ErrorCode.CACHE_ERROR, message=f"Failed to clear previews: {str(e)}", details={"error": str(e)})


@app.route("/api/clear_cache", methods=["POST"])
def clear_cache():
    try:
        deleted_count = 0
        # Delete asset json files
        if ASSETS_DIR.exists():
            for file in ASSETS_DIR.glob("*.json"):
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        # Delete last_update file
        if LAST_UPDATE_FILE.exists():
            LAST_UPDATE_FILE.unlink()

        return jsonify(
            {
                "status": "success",
                "message": f"Successfully deleted {deleted_count} cached asset(s) and reset cache state.",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return create_error_response(ErrorCode.CACHE_ERROR, message=f"Failed to clear cache: {str(e)}", details={"error": str(e)})


@app.route("/api/export/json", methods=["POST"])
def export_json():
    """Export JSON with optional filtering by selected UIDs."""
    data = request.get_json() or {}
    selected_uids = data.get("selected_uids", [])

    assets = get_assets()

    # Filter if selected UIDs were provided
    if selected_uids:
        assets = [a for a in assets if a.get("listing", {}).get("uid") in selected_uids]

    flat = [Asset(a).to_dict() for a in assets]
    return Response(
        json.dumps(flat, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=fab_library_{len(flat)}_items.json"},
    )


@app.route("/api/export/csv", methods=["POST"])
def export_csv():
    """Export CSV with optional filtering by selected UIDs."""
    data = request.get_json() or {}
    selected_uids = data.get("selected_uids", [])
    columns = data.get("columns", [])

    assets = get_assets()

    # Filter if selected UIDs were provided
    if selected_uids:
        assets = [a for a in assets if a.get("listing", {}).get("uid") in selected_uids]

    flat = [Asset(a).to_dict() for a in assets]
    if not flat:
        # If no assets found and UIDs were provided, it's an error
        if selected_uids:
            return create_error_response(
                ErrorCode.NO_RESULTS, message="No assets found for the requested UIDs", details={"requested_uids": selected_uids}
            )
        return create_error_response(ErrorCode.NO_RESULTS, message="No assets available in cache")

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


@app.route("/api/status")
def api_status():
    assets = get_assets()
    return jsonify({"cached": len(assets), "has_cache": len(assets) > 0})


@app.route("/api/image/<uid>", methods=["GET"])
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

    # Build path to cached preview file (one file per asset)
    # Format: previews/<UID>.jpg (JPEG format used for all thumbnails)
    preview_file = PREVIEWS_DIR / f"{uid}.jpg"

    # ─────────────────────────────────────────────────────────────
    # CACHE CHECK: If image already downloaded, serve from disk cache
    # ─────────────────────────────────────────────────────────────
    if preview_file.exists():
        # File exists in cache → serve immediately without re-downloading
        # This handles the common case after first access (95% of requests)
        return send_from_directory(PREVIEWS_DIR, f"{uid}.jpg")

    # ─────────────────────────────────────────────────────────────
    # FIRST ACCESS: Find asset and extract thumbnail URL
    # ─────────────────────────────────────────────────────────────
    # Load all assets from individual cache files
    assets = load_all_assets()
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
        return create_error_response(ErrorCode.NOT_FOUND, message=f"No thumbnail image available for asset '{uid}'", details={"uid": uid})

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
        else:
            # HTTP error (403, 404, 500, etc.)
            # This shouldn't happen if fab.com API is healthy
            return create_error_response(
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
        return create_error_response(
            ErrorCode.CONNECTION_ERROR,
            message="Network error while downloading image from Fab.com",
            details={
                "uid": uid,
                "error_type": type(e).__name__
            },
            context={"error_message": str(e)}
        )


# ─── Startup ────────────────────────────────────────────────────────────────
# Default initialization
configure_logger(*get_logging_settings())

if __name__ == "__main__":
    logger.info("🚀 FabAssetsManager")
    logger.info("=" * 40)

    # Check if config exists (don't force interactive input)
    cookies, user_agent = load_config()
    if not cookies or not user_agent:
        logger.info("\n⚠️  Incomplete configuration:")
        if not cookies:
            logger.info("   - config/cookies.txt missing or empty")
        if not user_agent:
            logger.info("   - config/user_agent.txt missing or empty")
        logger.info("\n💡 You can:")
        logger.info("   1. Use web interface to enter cookies + user-agent")
        logger.info("   2. Manually create config/cookies.txt and config/user_agent.txt")
        logger.info("   3. Run tests/test_connection.py to diagnose\n")
    else:
        logger.info("✅ Configuration loaded from config/cookies.txt and config/user_agent.txt")

    assets_count = len(load_all_assets())
    if assets_count > 0:
        logger.info(f"📦 Cache found: {assets_count} assets")
    else:
        logger.info("⚠️  No cache — click 🔄 Get New Assets in interface")

    settings = load_settings()
    server_port = settings.get("server_port", 5002)

    logger.info(f"\n✅ Open: http://localhost:{server_port}\n")
    app.run(debug=True, host="127.0.0.1", port=server_port)
