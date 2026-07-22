"""Shared opportunistic hold-sync for Streamlit portals.

Primary auto-approval runs in the API scheduler (api/scheduler.py).
These UI helpers are a lightweight fallback when the API is idle; they
share one implementation so Analyst and Admin do not diverge.
"""

import streamlit as st

from database.connection import get_cursor
from fraud_engine.auto_approval import sync_expired_holds


@st.cache_data(ttl=60)
def sync_database_holds() -> int:
    """Auto-approve expired backlog holds at most once per minute per session cache."""
    with get_cursor(commit=True) as (conn, cur):
        return sync_expired_holds(conn, cur)
