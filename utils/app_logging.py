"""Application file logging under .run/logs (covered by start.ps1 / stop.ps1)."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_APP_LOG_PATH = (
    Path(__file__).resolve().parent.parent / ".run" / "logs" / "metro_cart.log"
)

_CONFIGURED = False


def get_app_log_path() -> Path:
    override = os.environ.get("METRO_CART_LOG_PATH", "").strip()
    return Path(override) if override else DEFAULT_APP_LOG_PATH


def configure_app_logging(level: Optional[str] = None) -> Path:
    """
    Attach a rotating file handler to the metro_cart logger tree.

    Safe to call repeatedly. Returns the log file path.
    """
    global _CONFIGURED
    path = get_app_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    level_name = (level or os.environ.get("METRO_CART_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("metro_cart")
    root.setLevel(log_level)

    # Avoid duplicate handlers on reload.
    for h in list(root.handlers):
        if isinstance(h, RotatingFileHandler):
            existing = Path(getattr(h, "baseFilename", "") or "")
            if existing.resolve() == path.resolve():
                _CONFIGURED = True
                return path
            root.removeHandler(h)
            h.close()

    handler = RotatingFileHandler(
        path,
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.setLevel(log_level)
    root.addHandler(handler)

    # Also mirror to stderr so uvicorn console shows the same events.
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        stream = logging.StreamHandler()
        stream.setLevel(log_level)
        stream.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S")
        )
        root.addHandler(stream)

    root.propagate = False
    _CONFIGURED = True
    root.info("Application file logging enabled → %s", path)
    return path


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under metro_cart.* (ensures config once)."""
    if not _CONFIGURED:
        configure_app_logging()
    if name.startswith("metro_cart."):
        return logging.getLogger(name)
    return logging.getLogger(f"metro_cart.{name}")
