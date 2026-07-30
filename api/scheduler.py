"""Background scheduler for automatic backlog approval (review timeout)."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2

from config import DB_CONFIG
from fraud_engine.auto_approval import sync_expired_holds

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 1800  # 30 minutes
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None
_status_lock = threading.Lock()
_status: dict[str, Any] = {
    "running": False,
    "interval_seconds": _DEFAULT_INTERVAL_SECONDS,
    "last_started_at": None,
    "last_finished_at": None,
    "last_success_at": None,
    "last_failure_at": None,
    "last_error": None,
    "last_processed_count": 0,
    "total_processed_count": 0,
    "run_count": 0,
    "success_count": 0,
    "failure_count": 0,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_status(**updates: Any) -> None:
    with _status_lock:
        _status.update(updates)


def _bump_status(*, processed: int = 0, success: bool = True, error: Optional[str] = None) -> None:
    """Atomically update counters after a scheduler cycle."""
    with _status_lock:
        _status["last_finished_at"] = _utc_now_iso()
        _status["run_count"] = int(_status["run_count"]) + 1
        if success:
            _status["last_success_at"] = _status["last_finished_at"]
            _status["last_error"] = None
            _status["last_processed_count"] = int(processed)
            _status["total_processed_count"] = int(_status["total_processed_count"]) + int(
                processed
            )
            _status["success_count"] = int(_status["success_count"]) + 1
        else:
            _status["last_failure_at"] = _status["last_finished_at"]
            _status["last_error"] = error
            _status["last_processed_count"] = 0
            _status["failure_count"] = int(_status["failure_count"]) + 1


def get_auto_approval_status() -> dict[str, Any]:
    with _status_lock:
        return dict(_status)


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
    _set_status(
        running=True,
        interval_seconds=interval_seconds,
        last_started_at=_utc_now_iso(),
    )
    while not _stop_event.is_set():
        try:
            updated = _run_once()
            _bump_status(processed=updated, success=True)
            if updated:
                logger.info(
                    "Auto-approved %s backlog order(s) due to review timeout.",
                    updated,
                )
        except Exception:
            _bump_status(
                success=False,
                error="Auto-approval scheduler cycle failed. Check application logs.",
            )
            logger.exception("Auto-approval scheduler cycle failed.")
        _stop_event.wait(interval_seconds)
    logger.info("Auto-approval scheduler stopped.")
    _set_status(running=False)


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
    _set_status(running=False)
