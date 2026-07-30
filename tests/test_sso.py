"""Unit tests for Keycloak SSO wiring (password login remains unchanged)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from auth.sso import (
    append_query_param,
    create_oauth_state,
    normalize_return_to,
    parse_oauth_state,
    sync_keycloak_password,
    username_from_userinfo,
)

client = TestClient(app)


def test_sso_config_endpoint_reports_flag():
    with patch("api.portal.sso_is_configured", return_value=True):
        response = client.get("/auth/sso/config")
    assert response.status_code == 200
    assert response.json() == {"enabled": True}

    with patch("api.portal.sso_is_configured", return_value=False):
        response = client.get("/auth/sso/config")
    assert response.json() == {"enabled": False}


def test_sso_login_redirects_when_configured():
    with patch("api.portal.sso_is_configured", return_value=True), patch(
        "api.portal.create_pkce_pair", return_value=("verifier", "challenge")
    ), patch(
        "api.portal.build_authorize_url",
        return_value="http://keycloak.test/auth",
    ), patch("api.portal.create_oauth_state", return_value="signed-state"):
        response = client.get("/auth/sso/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "http://keycloak.test/auth"


def test_sso_login_unavailable_when_disabled():
    with patch("api.portal.sso_is_configured", return_value=False):
        response = client.get("/auth/sso/login", follow_redirects=False)
    assert response.status_code == 503


def test_sso_callback_maps_keycloak_user_to_session():
    state = create_oauth_state(
        "http://127.0.0.1:8000/portal/", code_verifier="test-verifier"
    )
    session = {
        "analyst": {
            "analyst_id": "A1",
            "employee_name": "Jane Doe",
            "username": "analyst",
            "role": "Senior Fraud Analyst",
        },
        "granted_pages": ["FRAUD_DASHBOARD"],
        "is_admin": False,
        "token": "session-token",
    }

    with patch("api.portal.sso_is_configured", return_value=True), patch(
        "api.portal.parse_oauth_state",
        return_value={
            "return_to": "http://127.0.0.1:8000/portal/",
            "code_verifier": "test-verifier",
        },
    ), patch("api.portal.complete_sso_login", return_value=("analyst", "id.token", None)), patch(
        "api.portal.get_session_by_username", return_value=session
    ), patch("api.portal.log_system_event"):
        response = client.get(
            "/auth/sso/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "sso=1" in response.headers["location"]
    assert "sso_token=" not in response.headers["location"]
    set_cookie = response.headers.get("set-cookie", "")
    assert "metro_cart_sso_handoff=session-token" in set_cookie
    assert "metro_cart_kc_id=" in set_cookie


def test_sso_complete_exchanges_handoff_cookie():
    session = {
        "analyst": {
            "analyst_id": "A1",
            "employee_name": "Jane Doe",
            "username": "analyst",
            "role": "Senior Fraud Analyst",
        },
        "granted_pages": ["FRAUD_DASHBOARD"],
        "is_admin": False,
    }
    with patch("api.portal.verify_session_token", return_value="A1"), patch(
        "api.portal.get_analyst_by_id", return_value=session
    ):
        response = client.get(
            "/auth/sso/complete",
            cookies={"metro_cart_sso_handoff": "session-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "session-token"
    assert body["analyst"]["analyst_id"] == "A1"
    assert "metro_cart_sso_handoff=" in (response.headers.get("set-cookie") or "")


def test_sso_callback_rejects_unknown_local_user():
    with patch("api.portal.sso_is_configured", return_value=True), patch(
        "api.portal.parse_oauth_state",
        return_value={
            "return_to": "http://127.0.0.1:8000/portal/",
            "code_verifier": "v",
        },
    ), patch("api.portal.complete_sso_login", return_value=("unknown_user", None, None)), patch(
        "api.portal.get_session_by_username", return_value=None
    ), patch("api.portal.log_system_event"):
        response = client.get(
            "/auth/sso/callback",
            params={"code": "auth-code", "state": "x"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "sso_error=no_local_analyst" in response.headers["location"]


def test_sso_logout_redirects_to_keycloak():
    with patch("api.portal.sso_is_configured", return_value=True), patch(
        "api.portal.build_logout_url",
        return_value="http://keycloak.test/logout",
    ) as build_logout:
        response = client.get(
            "/auth/sso/logout",
            params={"return_to": "http://127.0.0.1:8000/portal/"},
            cookies={"metro_cart_kc_id": "id.token.value"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == "http://keycloak.test/logout"
    build_logout.assert_called_once()
    assert build_logout.call_args.kwargs["id_token_hint"] == "id.token.value"
    assert "metro_cart_kc_id=" in (response.headers.get("set-cookie") or "")

def test_oauth_state_roundtrip_and_return_to_allowlist():
    state = create_oauth_state(
        "http://127.0.0.1:8000/portal/", code_verifier="abc"
    )
    parsed = parse_oauth_state(state)
    assert parsed is not None
    assert parsed["return_to"] == "http://127.0.0.1:8000/portal/"
    assert parsed["code_verifier"] == "abc"

    assert normalize_return_to("http://evil.example/phish") == normalize_return_to(None)
    assert "sso=1" in append_query_param(
        "http://127.0.0.1:8000/portal/", "sso", "1"
    )


def test_username_from_userinfo_prefers_preferred_username():
    assert (
        username_from_userinfo(
            {"preferred_username": "admin", "email": "admin@metro-cart.local"}
        )
        == "admin"
    )
    assert username_from_userinfo({"email": "analyst@metro-cart.local"}) == "analyst"


def test_password_login_endpoint_still_wired():
    """Ensure classic login route remains available alongside SSO."""
    fake = {
        "analyst": {
            "analyst_id": "A0",
            "employee_name": "Admin",
            "username": "admin",
            "role": "Admin",
        },
        "granted_pages": ["ADMIN_PANEL"],
        "is_admin": True,
        "token": "tok",
    }
    with patch("api.portal.authenticate_credentials", return_value=fake), patch(
        "api.portal.log_system_event"
    ):
        response = client.post(
            "/auth/login", json={"username": "admin", "password": "admin123"}
        )
    assert response.status_code == 200
    assert response.json()["token"] == "tok"
    set_cookie = response.headers.get("set-cookie") or ""
    assert "metro_cart_kc_id=" in set_cookie
    assert "metro_cart_sso_handoff=" in set_cookie


def test_sync_keycloak_password_skips_when_admin_missing():
    with patch("auth.sso.sso_is_configured", return_value=True), patch(
        "auth.sso.KEYCLOAK_ADMIN", ""
    ), patch("auth.sso.KEYCLOAK_ADMIN_PASSWORD", ""):
        ok, reason = sync_keycloak_password("analyst", "newpass99")
    assert ok is True
    assert reason is None
