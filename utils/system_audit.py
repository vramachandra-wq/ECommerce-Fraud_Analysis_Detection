"""Append-only system audit trail — primary store is PostgreSQL.

Optional rotating JSON file backup remains for local diagnostics.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from psycopg2.extras import Json

_LOCK = threading.Lock()
_FILE_LOGGER: Optional[logging.Logger] = None
_IMPORT_DONE = False

# Keep under .run/logs so start.ps1 / stop.ps1 already cover the directory.
DEFAULT_AUDIT_LOG_PATH = (
    Path(__file__).resolve().parent.parent / ".run" / "logs" / "system_audit.log"
)

_INSERT_SQL = """
INSERT INTO master.system_audit_log (
    created_at, actor_type, actor_id, actor_name,
    action, resource_type, resource_id, outcome,
    details, ip_address, request_path
) VALUES (
    %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s
)
"""


def get_audit_log_path() -> Path:
    override = os.environ.get("SYSTEM_AUDIT_LOG_PATH", "").strip()
    return Path(override) if override else DEFAULT_AUDIT_LOG_PATH


def _file_backup_enabled() -> bool:
    flag = os.environ.get("SYSTEM_AUDIT_FILE_BACKUP", "true").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def _file_logger() -> logging.Logger:
    """Singleton rotating file logger for optional audit backup."""
    global _FILE_LOGGER
    path = get_audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if _FILE_LOGGER is not None:
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


def _build_event(
    *,
    action: str,
    actor_type: str,
    actor_id: Optional[str],
    actor_name: Optional[str],
    resource_type: Optional[str],
    resource_id: Optional[str],
    outcome: str,
    details: Optional[Dict[str, Any]],
    ip_address: Optional[str],
    request_path: Optional[str],
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    when = created_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return {
        "created_at": when,
        "actor_type": actor_type or "system",
        "actor_id": actor_id,
        "actor_name": actor_name,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome or "success",
        "details": details,
        "ip_address": ip_address,
        "request_path": request_path,
    }


def _insert_event(cur: Any, event: Dict[str, Any]) -> None:
    cur.execute(
        _INSERT_SQL,
        (
            event["created_at"],
            event["actor_type"],
            event["actor_id"],
            event["actor_name"],
            event["action"],
            event["resource_type"],
            event["resource_id"],
            event["outcome"],
            Json(event["details"]) if event["details"] is not None else None,
            event["ip_address"],
            event["request_path"],
        ),
    )


def _write_file_backup(event: Dict[str, Any]) -> None:
    if not _file_backup_enabled():
        return
    payload = {
        **event,
        "created_at": event["created_at"].isoformat()
        if hasattr(event["created_at"], "isoformat")
        else event["created_at"],
    }
    with _LOCK:
        _file_logger().info(json.dumps(payload, default=str, ensure_ascii=False))


def _write_db(cur: Any, event: Dict[str, Any]) -> None:
    """Persist event using provided cursor or a short-lived connection."""
    if cur is not None:
        _insert_event(cur, event)
        return

    import psycopg2
    from config import DB_CONFIG
    from database.system_audit import ensure_system_audit_table

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as own_cur:
            ensure_system_audit_table(own_cur)
            _insert_event(own_cur, event)
        conn.commit()


def log_system_event(
    cur: Any = None,
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
    """Insert one audit event into master.system_audit_log (and optional file backup).

    Failures are swallowed so audit must not break business flows.
    When ``cur`` is provided, the insert joins the caller's transaction.
    """
    event = _build_event(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        details=details,
        ip_address=ip_address,
        request_path=request_path,
    )
    try:
        _write_db(cur, event)
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to write system audit event to DB action=%s", action
        )
    try:
        _write_file_backup(event)
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to write system audit file backup action=%s", action
        )


def _row_to_dict(row: tuple) -> Dict[str, Any]:
    (
        created_at,
        actor_type,
        actor_id,
        actor_name,
        action,
        resource_type,
        resource_id,
        outcome,
        details,
        ip_address,
        request_path,
        audit_id,
    ) = row
    if hasattr(created_at, "isoformat"):
        created_at_out: Any = created_at.isoformat()
    else:
        created_at_out = created_at
    return {
        "audit_id": audit_id,
        "created_at": created_at_out,
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


def read_audit_logs(
    *,
    limit: int = 100,
    action: Optional[str] = None,
    cur: Any = None,
) -> List[Dict[str, Any]]:
    """Read recent audit events from the database (newest first)."""
    limit = max(1, min(int(limit or 100), 500))

    def _query(active_cur: Any) -> List[Dict[str, Any]]:
        if action:
            active_cur.execute(
                """
                SELECT created_at, actor_type, actor_id, actor_name,
                       action, resource_type, resource_id, outcome,
                       details, ip_address, request_path, audit_id
                FROM master.system_audit_log
                WHERE action = %s
                ORDER BY created_at DESC, audit_id DESC
                LIMIT %s
                """,
                (action, limit),
            )
        else:
            active_cur.execute(
                """
                SELECT created_at, actor_type, actor_id, actor_name,
                       action, resource_type, resource_id, outcome,
                       details, ip_address, request_path, audit_id
                FROM master.system_audit_log
                ORDER BY created_at DESC, audit_id DESC
                LIMIT %s
                """,
                (limit,),
            )
        return [_row_to_dict(r) for r in active_cur.fetchall()]

    try:
        if cur is not None:
            return _query(cur)

        import psycopg2
        from config import DB_CONFIG
        from database.system_audit import ensure_system_audit_table

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as own_cur:
                ensure_system_audit_table(own_cur)
                rows = _query(own_cur)
            conn.commit()
        return rows
    except Exception:
        logging.getLogger(__name__).exception("Failed to read system audit log from DB")
        return []


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _read_file_events() -> List[Dict[str, Any]]:
    path = get_audit_log_path()
    candidates = [path]
    for i in range(1, 11):
        rotated = Path(f"{path}.{i}")
        if rotated.exists():
            candidates.append(rotated)

    rows: List[Dict[str, Any]] = []
    for file_path in candidates:
        if not file_path.exists():
            continue
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not row.get("action"):
                        continue
                    rows.append(row)
        except OSError:
            continue
    return rows


def import_file_audit_logs_if_empty(cur: Any) -> int:
    """One-time import of JSONL file history when the DB table is empty."""
    global _IMPORT_DONE
    if _IMPORT_DONE:
        return 0

    from database.system_audit import ensure_system_audit_table

    ensure_system_audit_table(cur)
    cur.execute("SELECT COUNT(*) FROM master.system_audit_log")
    count = int(cur.fetchone()[0] or 0)
    if count > 0:
        _IMPORT_DONE = True
        return 0

    file_rows = _read_file_events()
    if not file_rows:
        _IMPORT_DONE = True
        return 0

    imported = 0
    for row in file_rows:
        event = _build_event(
            action=str(row.get("action")),
            actor_type=str(row.get("actor_type") or "system"),
            actor_id=row.get("actor_id"),
            actor_name=row.get("actor_name"),
            resource_type=row.get("resource_type"),
            resource_id=row.get("resource_id"),
            outcome=str(row.get("outcome") or "success"),
            details=row.get("details") if isinstance(row.get("details"), dict) else None,
            ip_address=row.get("ip_address"),
            request_path=row.get("request_path"),
            created_at=_parse_created_at(row.get("created_at")),
        )
        try:
            _insert_event(cur, event)
            imported += 1
        except Exception:
            logging.getLogger(__name__).exception(
                "Skipped corrupt audit file row during import"
            )
    _IMPORT_DONE = True
    return imported


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
