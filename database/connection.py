"""Connection pooling for PostgreSQL via psycopg2."""
from contextlib import contextmanager
import threading

import psycopg2
import psycopg2.pool

from config import DB_CONFIG

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def get_pool():
    """Singleton threaded connection pool (thread-safe lazy init)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    **DB_CONFIG,
                )
    return _pool


def reset_pool_for_tests() -> None:
    """Close and clear the pool — for unit tests only."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


@contextmanager
def get_connection():
    """Borrow a connection from the pool; always returns it, even on error."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def get_pooled_connection():
    """Return a pooled database connection from the shared pool."""
    return get_pool().getconn()


def release_pooled_connection(conn):
    """Return a pooled database connection to the shared pool."""
    if conn is not None:
        get_pool().putconn(conn)


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
