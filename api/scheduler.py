"""Background scheduler for automatic backlog approval (review timeout)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import psycopg2

from config import DB_CONFIG
from fraud_engine.auto_approval import sync_expired_holds

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 60
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


def _run_once() -> int:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            updated = sync_expired_holds(conn, cur)
        conn.commit()
    return updated


def _loop(interval_seconds: int) -> None:
    logger.info(
        "Auto-approval scheduler started (interval=%ss).", interval_seconds
    )
    while not _stop_event.is_set():
        try:
            updated = _run_once()
            if updated:
                logger.info(
                    "Auto-approved %s backlog order(s) due to review timeout.",
                    updated,
                )
        except Exception:
            logger.exception("Auto-approval scheduler cycle failed.")
        _stop_event.wait(interval_seconds)
    logger.info("Auto-approval scheduler stopped.")


def start_auto_approval_scheduler(interval_seconds: int = _DEFAULT_INTERVAL_SECONDS) -> None:
    """Start the daemon thread (idempotent)."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(
        target=_loop,
        args=(interval_seconds,),
        name="auto-approval-scheduler",
        daemon=True,
    )
    _thread.start()


def stop_auto_approval_scheduler() -> None:
    """Signal the scheduler thread to stop."""
    _stop_event.set()
