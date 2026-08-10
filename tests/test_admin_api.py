from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.auth import get_current_session
from api.main import app
from auth.analyst_auth import ALL_PAGES, PAGE_ADMIN_PANEL
from tests.conftest import make_analyst_session

client = TestClient(app)


def _auth(role="Admin", pages=None):
    session = make_analyst_session(role=role, pages=pages or list(ALL_PAGES))

    def _dep():
        return session

    app.dependency_overrides[get_current_session] = _dep
    return session


def _clear():
    app.dependency_overrides.pop(get_current_session, None)


def _mock_db(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@patch("api.admin.sync_keycloak_user", return_value=(True, None))
@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_create_analyst(mock_connect, mock_log, mock_sync_kc):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "analyst_id": "A001",
            "employee_name": "Vinay",
            "username": "vinay",
            "password": "password",
            "role": "Admin",
        }
        response = client.post("/create-analyst", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Analyst Vinay Created"
        mock_sync_kc.assert_called_once_with(
            username="vinay",
            password="password",
            employee_name="Vinay",
        )
    finally:
        _clear()


@patch("api.admin.sync_keycloak_user", return_value=(False, "keycloak down"))
@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_create_analyst_rolls_back_when_keycloak_sync_fails(
    mock_connect, mock_log, mock_sync_kc
):
    _auth()
    try:
        mock_conn, _ = _mock_db(mock_connect)
        payload = {
            "analyst_id": "A002",
            "employee_name": "Sam Analyst",
            "username": "sam",
            "password": "password123",
            "role": "Fraud Analyst",
        }
        response = client.post("/create-analyst", json=payload)
        assert response.status_code == 502
        assert "Keycloak sync failed" in response.json()["detail"]
        mock_conn.rollback.assert_called()
        mock_sync_kc.assert_called_once()
    finally:
        _clear()

@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_blacklist_ip(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "ip_address": "192.168.1.10",
            "reason": "Fraud Activity",
            "blacklisted_by": "A001",
        }
        response = client.post("/blacklist-ip", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "IP Blacklisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_whitelist_ip(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "removed_by": "A001",
            "removed_at": "2026-07-08 10:00:00",
            "blacklist_id": 1,
        }
        response = client.put("/whitelist-ip", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "IP Whitelisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
@patch("api.admin.execute_batch")
def test_update_permissions_bulk(mock_execute_batch, mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "analyst_id": "A001",
            "permissions": {"ADMIN_PANEL": True, "REPORTS": False},
            "granted_by": "ADMIN",
        }
        response = client.put("/permissions/bulk", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully updated 2 permissions."
        mock_execute_batch.assert_called_once()
    finally:
        _clear()


def test_admin_endpoints_require_auth():
    _clear()
    response = client.post(
        "/blacklist-ip",
        json={"ip_address": "1.1.1.1", "reason": "x", "blacklisted_by": "A1"},
    )
    assert response.status_code == 401


@patch("api.admin.clear_metadata_cache")
@patch("api.admin.clear_interval_cache")
@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_update_rule_logs_before_after_diff(
    mock_connect,
    mock_log,
    mock_clear_interval,
    mock_clear_metadata,
):
    _auth()
    try:
        _mock_db(mock_connect)
        cursor = mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            ("R002", "Email Velocity", "REVIEW", 3.0, 30, "MINUTE", 60),
            ("R002", "Email Velocity", "HOLD", 5.0, 45, "HOUR", 90),
        ]
        response = client.put(
            "/update-rule",
            json={
                "rule_id": "R002",
                "action": "HOLD",
                "threshold_value": 5.0,
                "time_interval_value": 45,
                "time_interval_unit": "HOUR",
                "delay_minutes": 90,
            },
        )
        assert response.status_code == 200
        details = mock_log.call_args.kwargs["details"]
        assert details["before"]["action"] == "REVIEW"
        assert details["after"]["action"] == "HOLD"
        assert details["changes"]["delay_minutes"]["after"] == 90
    finally:
        _clear()
