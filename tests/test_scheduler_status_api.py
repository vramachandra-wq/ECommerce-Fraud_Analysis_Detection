from unittest.mock import patch

from fastapi.testclient import TestClient

from api.auth import get_current_session
from api.main import app
from auth.analyst_auth import ALL_PAGES
from tests.conftest import make_analyst_session

client = TestClient(app)


def _auth():
    session = make_analyst_session(role="Admin", pages=list(ALL_PAGES))

    def _dep():
        return session

    app.dependency_overrides[get_current_session] = _dep


def _clear():
    app.dependency_overrides.pop(get_current_session, None)


@patch("api.portal.get_auto_approval_status")
def test_scheduler_status_endpoint(mock_status):
    _auth()
    mock_status.return_value = {
        "running": True,
        "interval_seconds": 1800,
        "last_started_at": "2026-01-01T00:00:00+00:00",
        "last_finished_at": "2026-01-01T00:00:10+00:00",
        "last_success_at": "2026-01-01T00:00:10+00:00",
        "last_failure_at": None,
        "last_error": None,
        "last_processed_count": 2,
        "total_processed_count": 12,
        "run_count": 6,
        "success_count": 6,
        "failure_count": 0,
    }
    try:
        response = client.get("/portal/scheduler-status")
        assert response.status_code == 200
        body = response.json()["scheduler"]
        assert body["running"] is True
        assert body["total_processed_count"] == 12
    finally:
        _clear()
