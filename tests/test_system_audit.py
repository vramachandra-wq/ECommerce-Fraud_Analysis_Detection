"""Tests for DB-backed system audit helper (with optional file backup)."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from utils.system_audit import (
    actor_from_session,
    get_audit_log_path,
    log_system_event,
    read_audit_logs,
)


def test_actor_from_session():
    session = {
        "analyst": {
            "analyst_id": "A1",
            "employee_name": "Ada",
            "username": "ada",
        }
    }
    assert actor_from_session(session) == {
        "actor_type": "analyst",
        "actor_id": "A1",
        "actor_name": "Ada",
    }


def test_log_system_event_inserts_via_cursor_and_file_backup(tmp_path, monkeypatch):
    log_path = tmp_path / "system_audit.log"
    monkeypatch.setenv("SYSTEM_AUDIT_LOG_PATH", str(log_path))
    monkeypatch.setenv("SYSTEM_AUDIT_FILE_BACKUP", "true")

    import utils.system_audit as sa

    sa._FILE_LOGGER = None

    cur = MagicMock()
    log_system_event(
        cur,
        action="AUTH_LOGIN",
        actor_type="analyst",
        actor_id="A1",
        actor_name="Ada",
        outcome="success",
        details={"ok": True},
        request_path="/auth/login",
    )

    assert cur.execute.called
    sql, params = cur.execute.call_args[0]
    assert "INSERT INTO master.system_audit_log" in sql
    assert params[4] == "AUTH_LOGIN"
    assert params[2] == "A1"

    assert get_audit_log_path() == log_path
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    assert row["action"] == "AUTH_LOGIN"
    assert row["details"]["ok"] is True

    sa._FILE_LOGGER = None


def test_log_system_event_swallows_db_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("SYSTEM_AUDIT_LOG_PATH", str(tmp_path / "a.log"))
    monkeypatch.setenv("SYSTEM_AUDIT_FILE_BACKUP", "false")
    import utils.system_audit as sa

    sa._FILE_LOGGER = None
    cur = MagicMock()
    cur.execute.side_effect = RuntimeError("db down")
    # Must not raise
    log_system_event(cur, action="AUTH_LOGIN", outcome="failure")


def test_read_audit_logs_from_cursor():
    created = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    cur = MagicMock()
    cur.fetchall.return_value = [
        (
            created,
            "analyst",
            "A1",
            "Ada",
            "AUTH_LOGIN",
            None,
            None,
            "success",
            {"ok": True},
            None,
            "/auth/login",
            42,
        )
    ]
    rows = read_audit_logs(limit=10, cur=cur)
    assert len(rows) == 1
    assert rows[0]["action"] == "AUTH_LOGIN"
    assert rows[0]["audit_id"] == 42
    assert rows[0]["details"]["ok"] is True
    assert "2026-07-31" in rows[0]["created_at"]
