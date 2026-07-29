"""Tests for file-based system audit helper."""
import json
from pathlib import Path

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


def test_log_system_event_writes_json_line(tmp_path, monkeypatch):
    log_path = tmp_path / "system_audit.log"
    monkeypatch.setenv("SYSTEM_AUDIT_LOG_PATH", str(log_path))

    # Reset cached logger so the new path is used.
    import utils.system_audit as sa

    sa._FILE_LOGGER = None

    log_system_event(
        action="AUTH_LOGIN",
        actor_type="analyst",
        actor_id="A1",
        actor_name="Ada",
        outcome="success",
        details={"ok": True},
        request_path="/auth/login",
    )

    assert get_audit_log_path() == log_path
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    assert row["action"] == "AUTH_LOGIN"
    assert row["actor_id"] == "A1"
    assert row["details"]["ok"] is True

    rows = read_audit_logs(limit=10)
    assert len(rows) >= 1
    assert rows[0]["action"] == "AUTH_LOGIN"

    sa._FILE_LOGGER = None
