#!/usr/bin/env python3
"""FabAssetsManager — Local Flask Server

Version: 0.13.6

Launch: python app.py
Then open: http://localhost:5002

NOTE: 5002 is the default port for the web interface, but the it can be changed in `config/config.json`
"""

import sys
import logging
import time
import re
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler
from flask import Flask, request, g
from models import Asset
import cache_manager
import fetch_fab_library
import errors
from routes import bp as main_bp
import config_manager

app = Flask(__name__, static_folder="static", static_url_path="")
sys.modules.setdefault("app", sys.modules[__name__])

APP_DIR = config_manager.APP_DIR

_startup_settings = config_manager.load_settings()

paths = config_manager.get_paths()
CONFIG_DIR = paths["CONFIG_DIR"]
ASSETS_DIR = paths["ASSETS_DIR"]
PREVIEWS_DIR = paths["PREVIEWS_DIR"]
COOKIES_FILE = paths["COOKIES_FILE"]
UA_FILE = paths["UA_FILE"]
LOG_FILE = paths["LOG_FILE"]
LAST_UPDATE_FILE = paths["LAST_UPDATE_FILE"]

# Expose runtime helpers for routes via _app_module() without circular imports.
load_all_assets = cache_manager.load_all_assets
save_asset = cache_manager.save_asset
save_update_metadata = cache_manager.save_update_metadata
load_update_metadata = cache_manager.load_update_metadata
get_asset = cache_manager.get_asset
fetch_all_assets = fetch_fab_library.fetch_all_assets
fetch_asset_details = fetch_fab_library.fetch_asset_details
create_error_response = errors.create_error_response

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
            current_settings = config_manager.load_settings()
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
    cookies, user_agent = config_manager.load_credentials(COOKIES_FILE, UA_FILE)
    if cookies:
        logger.info(f"✅ Cookies loaded from {COOKIES_FILE}")
    if user_agent:
        logger.info(f"✅ User-Agent loaded from {UA_FILE}")
    return cookies, user_agent


def save_config(cookies: str, user_agent: str):
    config_manager.save_credentials(COOKIES_FILE, UA_FILE, cookies, user_agent)


def load_settings() -> dict:
    return config_manager.load_settings()


def save_settings(settings: dict) -> None:
    config_manager.save_settings(settings)


def get_logging_settings() -> tuple[str, str]:
    return config_manager.get_logging_settings()


def save_logging_settings(level: str, output: str) -> None:
    config_manager.save_logging_settings(level, output)


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


app.register_blueprint(main_bp)

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
