"""Tests for auth hardening, /health, and schema migrator (no live DB required)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from auth.login_guard import LoginGuard, client_key
from config import validate_runtime_secrets


client = TestClient(app)


def test_health_ok_when_db_up():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    with patch("api.main.psycopg2.connect", return_value=mock_conn):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_degraded_when_db_down():
    with patch("api.main.psycopg2.connect", side_effect=RuntimeError("db down")):
        response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "down"


def test_root_still_reports_portals():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["analyst_portal"] == "/portal/"
    assert body["health"] == "/health"


def test_login_guard_lockout_and_clear():
    guard = LoginGuard(max_attempts=3, window_seconds=60, lockout_seconds=30)
    key = client_key("admin", "127.0.0.1")
    assert guard.status(key).locked is False
    guard.record_failure(key)
    guard.record_failure(key)
    locked = guard.record_failure(key)
    assert locked.locked is True
    assert locked.retry_after_seconds >= 1
    assert guard.status(key).locked is True
    guard.clear(key)
    assert guard.status(key).locked is False


def test_login_rate_limit_returns_429():
    import api.portal as portal_mod
    from auth.login_guard import LoginGuard

    previous = portal_mod.login_guard
    portal_mod.login_guard = LoginGuard(
        max_attempts=2, window_seconds=60, lockout_seconds=60
    )
    try:
        with patch("api.portal.authenticate_credentials", return_value=None), patch(
            "api.portal.log_system_event"
        ):
            r1 = client.post(
                "/auth/login", json={"username": "lockme", "password": "bad"}
            )
            r2 = client.post(
                "/auth/login", json={"username": "lockme", "password": "bad"}
            )
        assert r1.status_code == 401
        assert r2.status_code == 429
        assert "Retry-After" in r2.headers
    finally:
        portal_mod.login_guard = previous


def test_local_logout_clears_cookies_without_keycloak():
    client.cookies.clear()
    with patch("api.portal.sso_is_configured", return_value=True):
        response = client.get(
            "/auth/logout",
            params={"return_to": "http://127.0.0.1:8000/portal/"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert response.headers["location"] == "http://127.0.0.1:8000/portal/"
    set_cookie = response.headers.get("set-cookie") or ""
    assert "metro_cart_session=" in set_cookie


def test_logout_with_sso_cookie_redirects_to_keycloak():
    client.cookies.clear()
    with patch("api.portal.sso_is_configured", return_value=True), patch(
        "api.portal.build_logout_url",
        return_value="http://keycloak.test/logout",
    ) as build_logout:
        response = client.get(
            "/auth/logout",
            params={"return_to": "http://127.0.0.1:8000/portal/"},
            cookies={"metro_cart_kc_id": "id.token.value"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert response.headers["location"] == "http://keycloak.test/logout"
    build_logout.assert_called_once()


def test_validate_runtime_secrets_rejects_weak_in_strict_mode():
    with patch("config.PORTAL_SECRET", "metro-cart-dev-portal-secret"), patch(
        "config.KEYCLOAK_ENABLED", False
    ):
        with pytest.raises(RuntimeError, match="PORTAL_SECRET"):
            validate_runtime_secrets(strict=True)


def test_apply_sql_migrations_records_files(tmp_path):
    from database.migrate import apply_sql_migrations

    mig = tmp_path / "001_demo.sql"
    mig.write_text(
        "CREATE TABLE IF NOT EXISTS master.demo_mig (id INT);\n",
        encoding="utf-8",
    )

    executed = []

    class FakeCursor:
        def __init__(self):
            self.applied = set()

        def execute(self, sql, params=None):
            executed.append((sql.strip().splitlines()[0], params))
            text = sql.strip().lower()
            if text.startswith("select filename"):
                self._rows = [(name,) for name in sorted(self.applied)]
            elif "insert into master.schema_migrations" in text and params:
                self.applied.add(params[0])
                self._rows = []
            else:
                self._rows = []

        def fetchall(self):
            return list(getattr(self, "_rows", []))

    cur = FakeCursor()
    applied, skipped = apply_sql_migrations(cur, directory=tmp_path)
    assert applied == ["001_demo.sql"]
    assert skipped == []

    applied2, skipped2 = apply_sql_migrations(cur, directory=tmp_path)
    assert applied2 == []
    assert skipped2 == ["001_demo.sql"]
    assert any("CREATE TABLE IF NOT EXISTS master.demo_mig" in sql for sql, _ in executed)
