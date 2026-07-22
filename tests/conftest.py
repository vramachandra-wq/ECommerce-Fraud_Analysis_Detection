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
