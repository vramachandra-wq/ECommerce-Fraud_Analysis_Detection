"""Tests for analyst change-password API."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_change_password_by_username():
    with patch("api.portal.psycopg2.connect") as connect, patch(
        "api.portal.change_analyst_password",
        return_value=(True, "password_change_success"),
    ) as change_pw, patch(
        "api.portal.sync_keycloak_password",
        return_value=(True, None),
    ) as sync_pw, patch("api.portal.log_system_event"):
        conn = MagicMock()
        cur = MagicMock()
        connect.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur

        response = client.post(
            "/auth/change-password",
            json={
                "username": "analyst",
                "current_password": "secure123",
                "new_password": "secure4567",
                "confirm_password": "secure4567",
            },
        )

    assert response.status_code == 200
    assert response.json()["message_key"] == "password_change_success"
    change_pw.assert_called_once()
    sync_pw.assert_called_once_with("analyst", "secure4567")
    conn.commit.assert_called_once()
    assert change_pw.call_args.kwargs["username"] == "analyst"
    assert change_pw.call_args.kwargs["analyst_id"] == ""


def test_change_password_while_logged_in():
    with patch("api.portal.verify_session_token", return_value="A1"), patch(
        "api.portal.psycopg2.connect"
    ) as connect, patch(
        "api.portal.change_analyst_password",
        return_value=(True, "password_change_success"),
    ) as change_pw, patch(
        "api.portal.sync_keycloak_password",
        return_value=(True, None),
    ) as sync_pw, patch("api.portal.log_system_event"):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = ("analyst",)
        connect.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur

        response = client.post(
            "/auth/change-password",
            headers={"Authorization": "Bearer fake-token"},
            json={
                "current_password": "secure123",
                "new_password": "secure4567",
                "confirm_password": "secure4567",
            },
        )

    assert response.status_code == 200
    assert change_pw.call_args.kwargs["analyst_id"] == "A1"
    sync_pw.assert_called_once_with("analyst", "secure4567")
    conn.commit.assert_called_once()


def test_change_password_validation_error():
    with patch("api.portal.psycopg2.connect") as connect, patch(
        "api.portal.change_analyst_password",
        return_value=(False, "password_change_wrong_current"),
    ), patch("api.portal.sync_keycloak_password") as sync_pw, patch("api.portal.log_system_event"):
        conn = MagicMock()
        cur = MagicMock()
        connect.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur

        response = client.post(
            "/auth/change-password",
            json={
                "username": "analyst",
                "current_password": "wrong",
                "new_password": "secure4567",
                "confirm_password": "secure4567",
            },
        )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()
    sync_pw.assert_not_called()


def test_change_password_rolls_back_when_keycloak_sync_fails():
    with patch("api.portal.psycopg2.connect") as connect, patch(
        "api.portal.change_analyst_password",
        return_value=(True, "password_change_success"),
    ), patch(
        "api.portal.sync_keycloak_password",
        return_value=(False, "boom"),
    ), patch("api.portal.log_system_event"):
        conn = MagicMock()
        cur = MagicMock()
        connect.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur

        response = client.post(
            "/auth/change-password",
            json={
                "username": "analyst",
                "current_password": "secure123",
                "new_password": "secure4567",
                "confirm_password": "secure4567",
            },
        )

    assert response.status_code == 502
    assert "rolled back" in response.json()["detail"].lower()
    conn.rollback.assert_called_once()
