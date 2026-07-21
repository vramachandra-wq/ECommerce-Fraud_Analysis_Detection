from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@patch("api.analyst.psycopg2.connect")
def test_get_pending_reviews(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    rows = [
        {
            "order_id": "ORD001",
            "order_timestamp": "2026-07-08 10:00:00",
            "amount": 1000,
            "order_status": "PENDING_REVIEW",
            "flagged_reason": "R002: Email velocity",
            "delay_minutes": 0,
        },
        {
            "order_id": "ORD002",
            "order_timestamp": "2026-07-08 11:00:00",
            "amount": 500,
            "order_status": "ON_HOLD",
            "flagged_reason": "R001: Hold",
            "delay_minutes": 180,
        },
    ]
    mock_cursor.fetchall.return_value = rows

    response = client.get("/pending-reviews")

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert len(body["data"]) == 2
    assert body["data"][0]["order_id"] == "ORD001"
    assert body["data"][1]["order_status"] == "ON_HOLD"
    mock_cursor.execute.assert_called_once()


@patch("api.analyst.psycopg2.connect")
def test_get_pending_reviews_empty(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    response = client.get("/pending-reviews")

    assert response.status_code == 200
    assert response.json() == {"data": []}


@patch("api.analyst.psycopg2.connect")
def test_get_pending_reviews_database_error(mock_connect):
    mock_connect.side_effect = Exception("Database Error")

    response = client.get("/pending-reviews")

    assert response.status_code == 500
