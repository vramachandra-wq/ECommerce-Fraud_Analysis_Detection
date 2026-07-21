from unittest.mock import MagicMock, patch

from database.connection import (
    get_pool,
    get_connection,
    get_cursor,
    get_pooled_connection,
    release_pooled_connection,
)


# ---------- get_pool ----------

@patch("database.connection.psycopg2.pool.ThreadedConnectionPool")
def test_get_pool(mock_pool):
    get_pool.clear()

    pool = get_pool()

    mock_pool.assert_called_once()
    assert pool == mock_pool.return_value


# ---------- get_connection ----------

@patch("database.connection.get_pool")
def test_get_connection(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()

    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    with get_connection() as connection:
        assert connection == conn

    pool.getconn.assert_called_once()
    pool.putconn.assert_called_once_with(conn)


# ---------- get_pooled_connection / release_pooled_connection ----------

@patch("database.connection.get_pool")
def test_get_pooled_connection(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    result = get_pooled_connection()

    assert result == conn
    pool.getconn.assert_called_once()


@patch("database.connection.get_pool")
def test_release_pooled_connection(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    mock_get_pool.return_value = pool

    release_pooled_connection(conn)

    pool.putconn.assert_called_once_with(conn)


@patch("database.connection.get_pool")
def test_release_pooled_connection_ignores_none(mock_get_pool):
    release_pooled_connection(None)

    mock_get_pool.assert_not_called()


# ---------- get_cursor (commit=True) ----------

@patch("database.connection.get_connection")
def test_get_cursor_commit(mock_get_connection):
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value = cursor
    mock_get_connection.return_value.__enter__.return_value = conn

    with get_cursor(commit=True) as (connection, cur):
        assert connection == conn
        assert cur == cursor

    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    cursor.close.assert_called_once()


# ---------- get_cursor (rollback on exception) ----------

@patch("database.connection.get_connection")
def test_get_cursor_rollback(mock_get_connection):
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value = cursor
    mock_get_connection.return_value.__enter__.return_value = conn

    try:
        with get_cursor(commit=True):
            raise Exception("Test Exception")
    except Exception:
        pass

    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    cursor.close.assert_called_once()


# ---------- get_cursor (commit=False) ----------

@patch("database.connection.get_connection")
def test_get_cursor_without_commit(mock_get_connection):
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value = cursor
    mock_get_connection.return_value.__enter__.return_value = conn

    with get_cursor(commit=False) as (connection, cur):
        assert connection == conn
        assert cur == cursor

    conn.commit.assert_not_called()
    conn.rollback.assert_not_called()
    cursor.close.assert_called_once()
