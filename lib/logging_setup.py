# ============================================================================
# FabAssetsManager - logging_setup.py
# ============================================================================
# Description: Application logging configuration (console + file rotation).
# Version: 1.0.4
# ============================================================================

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_ALLOWED_LOG_OUTPUTS = {"console", "file", "both"}


def normalize_log_output(log_output: str | None) -> str:
    normalized = (log_output or "console").strip().lower()
    if normalized not in _ALLOWED_LOG_OUTPUTS:
        return "console"
    return normalized


def resolve_log_level(log_level: str | None) -> int:
    level_name = (log_level or "INFO").strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging(*, log_level: str, log_output: str, log_max_bytes: int, log_backup_count: int, log_file_path: Path, ) -> None:
    root_logger = logging.getLogger()
    # On vide les handlers existants pour éviter les doublons lors de re-configurations
    root_logger.handlers.clear()
    root_logger.setLevel(resolve_log_level(log_level))

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    normalized_output = normalize_log_output(log_output)

    if normalized_output in {"console", "both"}:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if normalized_output in {"file", "both"}:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file_handler = RotatingFileHandler(
                filename=log_file_path, maxBytes=max(1024, int(log_max_bytes)), backupCount=max(1, int(log_backup_count)), encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Fallback console if file logging fails during setup
            if normalized_output == "file":
                fallback_handler = logging.StreamHandler(sys.stdout)
                fallback_handler.setFormatter(formatter)
                root_logger.addHandler(fallback_handler)
                logging.error(f"Failed to initialize file logger: {e}. Falling back to console.")
