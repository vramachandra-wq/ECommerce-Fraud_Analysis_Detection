# tests/conftest.py

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: end-to-end tests that require a live PostgreSQL database",
    )
    config.addinivalue_line(
        "markers",
        "live_groq: optional smoke tests that call the real Groq API (set RUN_LIVE_GROQ=1)",
    )


def pytest_collection_modifyitems(config, items):
    """Allow `pytest -m integration` / `pytest -m \"not integration\"`."""
    return


def make_analyst_session(
    *,
    role: str = "Admin",
    pages: list[str] | None = None,
    analyst_id: str = "A001",
):
    from auth.analyst_auth import ALL_PAGES, PAGE_FRAUD_DASHBOARD

    if pages is None:
        pages = list(ALL_PAGES) if role == "Admin" else [PAGE_FRAUD_DASHBOARD]

    return {
        "analyst": {
            "analyst_id": analyst_id,
            "employee_name": "Test Analyst",
            "username": "tester",
            "role": role,
        },
        "granted_pages": pages,
        "is_admin": role == "Admin",
    }
