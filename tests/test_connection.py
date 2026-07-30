from unittest.mock import MagicMock, patch

from database.connection import (
    get_pool,
    get_connection,
    get_cursor,
    get_pooled_connection,
    release_pooled_connection,
    reset_pool_for_tests,
)


# ---------- get_pool ----------

@patch("database.connection.psycopg2.pool.ThreadedConnectionPool")
def test_get_pool(mock_pool):
    reset_pool_for_tests()

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
def test_pooled_connection_helpers(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    assert get_pooled_connection() == conn
    pool.getconn.assert_called_once()

    release_pooled_connection(conn)
    pool.putconn.assert_called_once_with(conn)


@patch("database.connection.get_pool")
def test_release_pooled_connection_none(mock_get_pool):
    release_pooled_connection(None)
    mock_get_pool.assert_not_called()


# ---------- get_cursor ----------

@patch("database.connection.get_pool")
def test_get_cursor_commits(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    with get_cursor(commit=True) as (connection, cur):
        assert connection == conn
        assert cur == cursor

    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    cursor.close.assert_called_once()


@patch("database.connection.get_pool")
def test_get_cursor_rolls_back_on_error(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    with patch("database.connection.get_cursor", wraps=get_cursor):
        try:
            with get_cursor(commit=True) as (_, cur):
                cur.execute("SELECT 1")
                raise RuntimeError("boom")
        except RuntimeError:
            pass

    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    cursor.close.assert_called_once()


@patch("database.connection.get_pool")
def test_get_cursor_read_only(mock_get_pool):
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    pool.getconn.return_value = conn
    mock_get_pool.return_value = pool

    with get_cursor() as (connection, cur):
        assert connection == conn
        assert cur == cursor

    conn.commit.assert_not_called()
    conn.rollback.assert_not_called()
    cursor.close.assert_called_once()
