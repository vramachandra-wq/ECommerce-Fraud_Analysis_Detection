from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _mock_locked_cursor(mock_connect, *, orders=1):
    """Wire psycopg2 connect/cursor so lock+update succeeds for N orders."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Each approve/reject: SELECT lock fetchone, then audit context may fetch again.
    # Returning a row for every fetchone keeps the lock path succeeding.
    mock_cursor.fetchone.return_value = ("ORD001",)
    mock_cursor.rowcount = 1
    return mock_conn, mock_cursor


# ---------------- approve-order ----------------

@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_approve_order(mock_connect, mock_audit_ctx, mock_log):
    _mock_locked_cursor(mock_connect)

    payload = {
        "approved_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Approved",
        "order_id": "ORD001",
    }

    response = client.put("/approve-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Approved"
    mock_log.assert_called_once()


@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_approve_order_conflict_when_not_in_queue(mock_connect, mock_audit_ctx):
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


# ---------------- reject-order ----------------

@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_reject_order(mock_connect, mock_audit_ctx, mock_log):
    _mock_locked_cursor(mock_connect)

    payload = {
        "rejected_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Fraud",
        "order_id": "ORD001",
    }

    response = client.put("/reject-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Rejected"


# ---------------- batch approve ----------------

@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_batch_approve(mock_connect, mock_audit_ctx, mock_log):
    _mock_locked_cursor(mock_connect)

    payload = {
        "approved_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Approved",
        "order_ids": ["ORD001", "ORD002"],
    }

    response = client.put("/batch-approve", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Batch Approved 2 orders"
    assert body["processed"] == ["ORD001", "ORD002"]
    assert body["skipped"] == []


# ---------------- batch reject ----------------

@patch("api.analyst.log_review_action")
@patch("api.analyst.fetch_order_audit_context", return_value={"rule_name": None, "delay_minutes": 0})
@patch("api.analyst.psycopg2.connect")
def test_batch_reject(mock_connect, mock_audit_ctx, mock_log):
    _mock_locked_cursor(mock_connect)

    payload = {
        "rejected_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Fraud",
        "order_ids": ["ORD001", "ORD002"],
    }

    response = client.put("/batch-reject", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Batch Rejected 2 orders"
    assert body["processed"] == ["ORD001", "ORD002"]
