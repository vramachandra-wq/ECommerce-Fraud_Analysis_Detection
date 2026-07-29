from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from auth.analyst_auth import ALL_PAGES, PAGE_FRAUD_DASHBOARD
from tests.conftest import make_analyst_session

client = TestClient(app)


def _auth(role="Admin", pages=None, analyst_id="A001"):
    from api.auth import get_current_session

    session = make_analyst_session(role=role, pages=pages, analyst_id=analyst_id)

    def _dep():
        return session

    app.dependency_overrides[get_current_session] = _dep
    return session


def _clear_auth():
    from api.auth import get_current_session

    app.dependency_overrides.pop(get_current_session, None)


def _mock_locked_cursor(mock_connect, *, orders=1):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchone.return_value = ("ORD001",)
    mock_cursor.rowcount = 1
    return mock_conn, mock_cursor


@patch("api.analyst.log_system_event")
@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_approve_order(mock_connect, mock_audit_ctx, mock_log, mock_sys):
    _auth(pages=[PAGE_FRAUD_DASHBOARD])
    try:
        _mock_locked_cursor(mock_connect)
        payload = {
            "approved_at": "2026-07-08",
            "reviewed_by": "ignored",
            "review_comments": "Approved",
            "order_id": "ORD001",
        }
        response = client.put("/approve-order", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Approved"
        mock_log.assert_called_once()
    finally:
        _clear_auth()


def test_approve_order_requires_auth():
    _clear_auth()
    response = client.put(
        "/approve-order",
        json={
            "approved_at": "2026-07-08",
            "review_comments": "Approved",
            "order_id": "ORD001",
        },
    )
    assert response.status_code == 401


@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_approve_order_conflict_when_not_in_queue(mock_connect, mock_audit_ctx):
    _auth(pages=[PAGE_FRAUD_DASHBOARD])
    try:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = client.put(
            "/approve-order",
            json={
                "approved_at": "2026-07-08",
                "reviewed_by": "A001",
                "review_comments": "Approved",
                "order_id": "ORD001",
            },
        )
        assert response.status_code == 409
        assert "no longer in the review queue" in response.json()["detail"]
    finally:
        _clear_auth()


@patch("api.analyst.log_system_event")
@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_reject_order(mock_connect, mock_audit_ctx, mock_log, mock_sys):
    _auth(pages=[PAGE_FRAUD_DASHBOARD])
    try:
        _mock_locked_cursor(mock_connect)
        payload = {
            "rejected_at": "2026-07-08",
            "reviewed_by": "ignored",
            "review_comments": "Fraud",
            "order_id": "ORD001",
            "is_fraud": True,
        }
        response = client.put("/reject-order", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Rejected"
        mock_log.assert_called_once()
    finally:
        _clear_auth()


@patch("api.analyst.log_system_event")
@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_batch_approve(mock_connect, mock_audit_ctx, mock_log, mock_sys):
    _auth(pages=[PAGE_FRAUD_DASHBOARD])
    try:
        _mock_locked_cursor(mock_connect)
        payload = {
            "order_ids": ["ORD001", "ORD002"],
            "approved_at": "2026-07-08",
            "reviewed_by": "ignored",
            "review_comments": "Batch",
        }
        response = client.put("/batch-approve", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert "Batch Approved" in body["message"]
    finally:
        _clear_auth()


@patch("api.analyst.log_system_event")
@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_batch_reject(mock_connect, mock_audit_ctx, mock_log, mock_sys):
    _auth(pages=[PAGE_FRAUD_DASHBOARD])
    try:
        _mock_locked_cursor(mock_connect)
        payload = {
            "order_ids": ["ORD001"],
            "rejected_at": "2026-07-08",
            "reviewed_by": "ignored",
            "review_comments": "Batch",
            "is_fraud": True,
        }
        response = client.put("/batch-reject", json=payload)
        assert response.status_code == 200
        assert "Batch Rejected" in response.json()["message"]
    finally:
        _clear_auth()
