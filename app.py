#!/usr/bin/env python3
"""FabAssetsManager — Local Flask Server

Version: 0.13.4

Launch: python app.py
Then open: http://localhost:5002

NOTE: 5002 is the default port for the web interface, but the it can be changed in `config/config.json`
"""

import json
import sys
import logging
import time
import re
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import Flask, request, g
from models import Asset
from cache_manager import load_all_assets
from routes import bp as main_bp

app = Flask(__name__, static_folder="static", static_url_path="")
sys.modules.setdefault("app", sys.modules[__name__])

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
