# ============================================================================
# FabAssetsManager - config_manager.py
# ============================================================================
# Description: Centralized configuration parsing, validation, and path resolution.
# Version: 1.0.4
# ============================================================================

import json
from pathlib import Path
from .app_settings import APP_DIR, DEFAULT_CONFIG_DIR as _DEFAULT_CONFIG_DIR, CONFIG_FILE, DEFAULT_SETTINGS


def load_settings() -> dict:
    """Load settings from CONFIG_FILE with validation and defaults."""
    settings = dict(DEFAULT_SETTINGS)

    if not CONFIG_FILE.exists():
        _DEFAULT_CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        save_settings(settings)
        return settings

    try:
        current_settings = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(current_settings, dict):
            current_settings = {}
    except (OSError, json.JSONDecodeError):
        current_settings = {}

    modified = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in current_settings:
            current_settings[k] = v
            modified = True

    # Type coercion and validation
    try:
        port = int(current_settings.get("server_port", 5002))
        current_settings["server_port"] = max(1024, min(65535, port))
    except (ValueError, TypeError):
        current_settings["server_port"] = 5002
        modified = True

    try:
        log_max_bytes = int(current_settings.get("log_max_bytes", 5 * 1024 * 1024))
        current_settings["log_max_bytes"] = max(1024, log_max_bytes)  # minimum 1KB
    except (ValueError, TypeError):
        current_settings["log_max_bytes"] = 5 * 1024 * 1024
        modified = True

    try:
        log_backup_count = int(current_settings.get("log_backup_count", 2))
        current_settings["log_backup_count"] = max(0, log_backup_count)
    except (ValueError, TypeError):
        current_settings["log_backup_count"] = 2
        modified = True

    log_level = str(current_settings.get("log_level", "INFO")).upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        current_settings["log_level"] = "INFO"
        modified = True
    else:
        current_settings["log_level"] = log_level

    log_output = str(current_settings.get("log_output", "both")).lower()
    if log_output not in {"console", "file", "both"}:
        current_settings["log_output"] = "both"
        modified = True
    else:
        current_settings["log_output"] = log_output

    if modified:
        save_settings(current_settings)

    return current_settings


def save_settings(settings: dict) -> None:
    """Persist settings to CONFIG_FILE."""
    CONFIG_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def get_logging_settings() -> tuple[str, str]:
    settings = load_settings()
    return settings["log_level"], settings["log_output"]


def save_logging_settings(level: str, output: str) -> None:
    settings = load_settings()
    settings["log_level"] = level
    settings["log_output"] = output
    save_settings(settings)


def _resolve_path(path_value: object | None, default: Path) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        return default
    p = Path(path_value.strip())
    return p if p.is_absolute() else (APP_DIR / p).resolve()


def get_paths() -> dict:
    """Resolve and return all configured paths."""
    settings = load_settings()
    config_dir = _resolve_path(settings.get("config_dir"), _DEFAULT_CONFIG_DIR)
    assets_dir = _resolve_path(settings.get("assets_dir"), APP_DIR / "assets")
    previews_dir = _resolve_path(settings.get("previews_dir"), APP_DIR / "previews")

    paths = {
        "CONFIG_DIR": config_dir,
        "ASSETS_DIR": assets_dir,
        "PREVIEWS_DIR": previews_dir,
        "COOKIES_FILE": _resolve_path(settings.get("cookies_file"), config_dir / "cookies.txt"),
        "UA_FILE": _resolve_path(settings.get("ua_file"), config_dir / "user_agent.txt"),
        "LOG_FILE": _resolve_path(settings.get("log_file"), APP_DIR / "app.log"),
        "LAST_UPDATE_FILE": _resolve_path(settings.get("last_update_file"), assets_dir / "last_update.txt"),
    }

    paths["CONFIG_DIR"].mkdir(exist_ok=True, parents=True)
    paths["ASSETS_DIR"].mkdir(exist_ok=True, parents=True)
    paths["PREVIEWS_DIR"].mkdir(exist_ok=True, parents=True)

    return paths


def load_credentials(cookies_file: Path, ua_file: Path) -> tuple[str | None, str | None]:
    """Load cookies and user_agent from files, or None if missing."""
    cookies = cookies_file.read_text(encoding="utf-8").strip() if cookies_file.exists() else None
    user_agent = ua_file.read_text(encoding="utf-8").strip() if ua_file.exists() else None
    return cookies, user_agent


def save_credentials(cookies_file: Path, ua_file: Path, cookies: str, user_agent: str):
    """Save cookies and user_agent to files."""
    cookies_file.write_text(cookies.strip(), encoding="utf-8")
    ua_file.write_text(user_agent.strip(), encoding="utf-8")
