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


def pytest_collection_modifyitems(config, items):
    """Allow `pytest -m integration` / `pytest -m \"not integration\"`."""
    return
