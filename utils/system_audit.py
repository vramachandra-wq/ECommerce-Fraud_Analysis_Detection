"""Append-only system audit trail written to a rotating log file (JSON Lines)."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_FILE_LOGGER: Optional[logging.Logger] = None

# Keep under .run/logs so start.ps1 / stop.ps1 already cover the directory.
DEFAULT_AUDIT_LOG_PATH = (
    Path(__file__).resolve().parent.parent / ".run" / "logs" / "system_audit.log"
)


def get_audit_log_path() -> Path:
    override = os.environ.get("SYSTEM_AUDIT_LOG_PATH", "").strip()
    return Path(override) if override else DEFAULT_AUDIT_LOG_PATH


def _file_logger() -> logging.Logger:
    """Singleton rotating file logger for audit events."""
    global _FILE_LOGGER
    path = get_audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if _FILE_LOGGER is not None:
        # Rebind if env path changed (tests / config reload).
        current = None
        for h in _FILE_LOGGER.handlers:
            if isinstance(h, RotatingFileHandler):
                current = Path(getattr(h, "baseFilename", "") or "")
                break
        if current == path.resolve():
            return _FILE_LOGGER
        for h in list(_FILE_LOGGER.handlers):
            _FILE_LOGGER.removeHandler(h)
            h.close()

    log = logging.getLogger("metro_cart.system_audit")
    log.setLevel(logging.INFO)
    log.propagate = False
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()

    handler = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)

    _FILE_LOGGER = log
    return log


def log_system_event(
    cur: Any = None,  # kept for call-site compatibility; unused (file-based)
    *,
    action: str,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: str = "success",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    request_path: Optional[str] = None,
) -> None:
    """Append one JSON audit event to the system audit log file.

    Failures are swallowed so audit must not break business flows.
    """
    _ = cur  # unused — audit is file-based
    event = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor_type": actor_type,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "details": details,
        "ip_address": ip_address,
        "request_path": request_path,
    }
    try:
        with _LOCK:
            _file_logger().info(json.dumps(event, default=str, ensure_ascii=False))
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to write system audit event action=%s", action
        )


def read_audit_logs(
    *,
    limit: int = 100,
    action: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read recent audit events from the log file (newest first)."""
    limit = max(1, min(int(limit or 100), 500))
    path = get_audit_log_path()
    if not path.exists():
        return []

    # Include rotated backups so recent history is not lost after rotation.
    candidates = [path]
    for i in range(1, 11):
        rotated = Path(f"{path}.{i}")
        if rotated.exists():
            candidates.append(rotated)

    rows: List[Dict[str, Any]] = []
    try:
        for file_path in candidates:
            with file_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if action and row.get("action") != action:
                        continue
                    rows.append(row)
    except OSError:
        logging.getLogger(__name__).exception("Failed to read system audit log")
        return []

    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows[:limit]


def actor_from_session(session: Dict[str, Any]) -> Dict[str, Optional[str]]:
    analyst = (session or {}).get("analyst") or {}
    return {
        "actor_type": "analyst",
        "actor_id": analyst.get("analyst_id"),
        "actor_name": analyst.get("employee_name") or analyst.get("username"),
    }


def actor_from_customer(customer: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "actor_type": "customer",
        "actor_id": customer.get("user_id"),
        "actor_name": customer.get("customer_name") or customer.get("user_id"),
    }
