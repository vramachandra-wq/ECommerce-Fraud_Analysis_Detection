"""Connection pooling for PostgreSQL via psycopg2."""
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
import streamlit as st

from config import DB_CONFIG


@st.cache_resource
def get_pool():
    """Singleton threaded connection pool, cached across Streamlit reruns."""
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        **DB_CONFIG,
    )


@contextmanager
def get_connection():
    """Borrow a connection from the pool; always returns it, even on error."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor(commit: bool = False):
    """Yield a (conn, cursor) pair. Set commit=True for writes."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            yield conn, cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
