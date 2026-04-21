# ============================================================================
# FabAssetsManager - app_settings.py
# ============================================================================
# Description: Configuration constants and default application paths.
# Version: 1.0.3
# ============================================================================

from pathlib import Path

APP_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

DEFAULT_SETTINGS = {
    "config_dir": "config",
    "assets_dir": "assets",
    "previews_dir": "previews",
    "cookies_file": "config/cookies.txt",
    "ua_file": "config/user_agent.txt",
    "log_file": "app.log",
    "last_update_file": "assets/last_update.txt",
    "server_port": 5002,
    "server_host": "127.0.0.1",
    "flask_debug": False,
    "flask_threaded": True,
    "log_level": "INFO",
    "log_output": "both",
    "log_max_bytes": 5 * 1024 * 1024,
    "log_backup_count": 2
}
