"""Portal order-detail PII masking (Admin full, others masked)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.auth import get_current_session
from api.main import app
from auth.analyst_auth import PAGE_FRAUD_DASHBOARD

client = TestClient(app)

SAMPLE_ORDER = {
    "order_id": "ORD-PII-1",
    "user_id": "U1",
    "customer_name": "Rahul",
    "email": "rahul.mehta@example.com",
    "phone_number": "9876543210",
    "address": "21 MG Road, Bengaluru, Karnataka 560001",
    "ip_address": "192.168.1.100",
    "product_name": "Phone",
    "quantity": 1,
    "amount": 1000.0,
    "device_id": "D1",
    "order_status": "PENDING_REVIEW",
    "flagged_reason": "Email Velocity",
    "order_timestamp": None,
}


def _session(role: str):
    return {
        "analyst": {
            "analyst_id": "A1",
            "employee_name": "Tester",
            "username": "tester",
            "role": role,
        },
        "granted_pages": [PAGE_FRAUD_DASHBOARD],
        "is_admin": role == "Admin",
    }


def _override_session(role: str):
    def _dep():
        return _session(role)

    return _dep


@patch("api.portal.get_order_detail", return_value=dict(SAMPLE_ORDER))
@patch("api.portal.get_active_blacklist_entry", return_value=None)
@patch("api.portal.get_active_phone_blacklist_entry", return_value=None)
@patch("api.portal.get_active_email_blacklist_entry", return_value=None)
@patch("api.portal._order_timing", return_value={"delay_minutes": 60})
@patch("api.portal.get_cursor")
def test_portal_order_detail_masks_for_fraud_analyst(
    mock_cursor,
    _timing,
    _email_bl,
    _phone_bl,
    _ip_bl,
    _order,
):
    mock_cursor.return_value.__enter__.return_value = (MagicMock(), MagicMock())
    app.dependency_overrides[get_current_session] = _override_session("Fraud Analyst")
    try:
        response = client.get("/portal/orders/ORD-PII-1")
    finally:
        app.dependency_overrides.pop(get_current_session, None)

    assert response.status_code == 200
    order = response.json()["order"]
    assert order["email"] == "ra*********@example.com"
    assert order["phone_number"] == "98******10"
    assert order["address"] == "21********, Bengaluru, Karnataka 560001"
    assert order["ip_address"] == "192.168.***.***"


@patch("api.portal.get_order_detail", return_value=dict(SAMPLE_ORDER))
@patch("api.portal.get_active_blacklist_entry", return_value=None)
@patch("api.portal.get_active_phone_blacklist_entry", return_value=None)
@patch("api.portal.get_active_email_blacklist_entry", return_value=None)
@patch("api.portal._order_timing", return_value={"delay_minutes": 60})
@patch("api.portal.get_cursor")
def test_portal_order_detail_full_for_admin(
    mock_cursor,
    _timing,
    _email_bl,
    _phone_bl,
    _ip_bl,
    _order,
):
    mock_cursor.return_value.__enter__.return_value = (MagicMock(), MagicMock())
    app.dependency_overrides[get_current_session] = _override_session("Admin")
    try:
        response = client.get("/portal/orders/ORD-PII-1")
    finally:
        app.dependency_overrides.pop(get_current_session, None)

    assert response.status_code == 200
    order = response.json()["order"]
    assert order["email"] == "rahul.mehta@example.com"
    assert order["phone_number"] == "9876543210"
    assert order["ip_address"] == "192.168.1.100"


@patch("api.admin.log_system_event")
@patch("api.admin.blacklist_entity_from_order", return_value=("email", "rahul.mehta@example.com"))
@patch("api.admin.psycopg2.connect")
def test_blacklist_from_order_endpoint(mock_connect, _bl, _log):
    from api.auth import get_current_session
    from auth.analyst_auth import ALL_PAGES
    from tests.conftest import make_analyst_session

    session = make_analyst_session(pages=list(ALL_PAGES))
    app.dependency_overrides[get_current_session] = lambda: session
    try:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        response = client.post(
            "/blacklist-from-order",
            json={
                "order_id": "ORD-PII-1",
                "entity_type": "email",
                "reason": "fraud",
                "blacklisted_by": "A1",
            },
        )
        assert response.status_code == 200
        assert "EMAIL" in response.json()["message"]
    finally:
        app.dependency_overrides.pop(get_current_session, None)
