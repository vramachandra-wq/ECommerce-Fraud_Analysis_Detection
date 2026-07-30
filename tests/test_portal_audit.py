"""Tests for GET /portal/audit."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.auth import get_current_session
from api.main import app
from auth.analyst_auth import PAGE_ADMIN_PANEL

client = TestClient(app)


def _override_session():
    def _dep():
        return {
            "analyst": {
                "analyst_id": "A001",
                "employee_name": "Admin User",
                "username": "admin",
                "role": "Admin",
            },
            "granted_pages": [PAGE_ADMIN_PANEL],
            "is_admin": True,
        }

    return _dep


@patch("api.portal.get_review_audit_log")
def test_audit_log_returns_entries(mock_get_audit):
    mock_get_audit.return_value = {
        "entries": [
            {
                "audit_id": 1,
                "order_id": "ORD001",
                "analyst_id": "SYSTEM",
                "analyst_name": None,
                "action": "AUTO_APPROVE",
                "rule_name": "Email Velocity",
                "delay_minutes": 60,
                "reason": "Timeout",
                "review_comments": None,
                "created_at": "2026-01-01T12:00:00",
                "customer_name": "Test User",
                "order_status": "APPROVED",
            }
        ],
        "total": 1,
        "limit": 100,
        "offset": 0,
    }

    app.dependency_overrides[get_current_session] = _override_session()
    try:
        response = client.get("/portal/audit")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["entries"][0]["action"] == "AUTO_APPROVE"
    mock_get_audit.assert_called_once()


def test_audit_log_requires_auth():
    response = client.get("/portal/audit")
    assert response.status_code == 401
