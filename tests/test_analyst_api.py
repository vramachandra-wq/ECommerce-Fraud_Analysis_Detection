from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)

# ---------------- approve-order ----------------

@patch("api.analyst.psycopg2.connect")
def test_approve_order(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "approved_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Approved",
        "order_id": "ORD001"
    }

    response = client.put("/approve-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Approved"


# ---------------- reject-order ----------------

@patch("api.analyst.psycopg2.connect")
def test_reject_order(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "rejected_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Fraud",
        "order_id": "ORD001"
    }

    response = client.put("/reject-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Rejected"


# ---------------- batch approve ----------------

@patch("api.analyst.psycopg2.connect")
def test_batch_approve(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "approved_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Approved",
        "order_ids": ["ORD001", "ORD002"]
    }

    response = client.put("/batch-approve", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Batch Approved"


# ---------------- batch reject ----------------

@patch("api.analyst.psycopg2.connect")
def test_batch_reject(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "rejected_at": "2026-07-08",
        "reviewed_by": "A001",
        "review_comments": "Fraud",
        "order_ids": ["ORD001", "ORD002"]
    }

    response = client.put("/batch-reject", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Batch Rejected"