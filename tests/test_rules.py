from fraud_engine.rules import check_r001
from unittest.mock import MagicMock
from fraud_engine.rules import check_r002
from fraud_engine.rules import (
    check_r003,
    check_r004,
    check_r005,
    check_r006,
    check_r007,
    check_r008,
    check_r009,
    check_r010,
)

# ---------------- R001----------------

def test_r001_should_trigger():
    ctx = {
        "program_id": "P2",
        "product_name": "iPhone 16 Pro"
    }

    triggered, reason = check_r001(None, ctx)

    assert triggered is True
    assert "R001" in reason


def test_r001_wrong_program():
    ctx = {
        "program_id": "P1",
        "product_name": "iPhone 16 Pro"
    }

    triggered, reason = check_r001(None, ctx)

    assert triggered is False
    assert reason is None


def test_r001_wrong_product():
    ctx = {
        "program_id": "P2",
        "product_name": "Samsung S25"
    }

    triggered, reason = check_r001(None, ctx)

    assert triggered is False
    assert reason is None

# ---------------- R002 ----------------


def test_r002_should_trigger():
    cursor = MagicMock()

    # Pretend the database found 3 previous orders
    cursor.fetchone.return_value = [3]

    ctx = {
        "email": "test@example.com",
        "order_timestamp": "2026-07-08 10:00:00"
    }

    triggered, reason = check_r002(cursor, ctx)

    assert triggered is True
    assert "R002" in reason


def test_r002_should_not_trigger():
    cursor = MagicMock()

    # Pretend only 2 previous orders exist
    cursor.fetchone.return_value = [2]

    ctx = {
        "email": "test@example.com",
        "order_timestamp": "2026-07-08 10:00:00"
    }

    triggered, reason = check_r002(cursor, ctx)

    assert triggered is False
    assert reason is None    


# ---------------- R003 ----------------

def test_r003_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [5]

    ctx = {
        "ip_address": "192.168.1.1",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r003(cursor, ctx)

    assert triggered is True
    assert "R003" in reason


def test_r003_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [4]

    ctx = {
        "ip_address": "192.168.1.1",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r003(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R004 ----------------

def test_r004_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [4]

    ctx = {
        "device_id": "DEV001",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r004(cursor, ctx)

    assert triggered is True
    assert "R004" in reason


def test_r004_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [3]

    ctx = {
        "device_id": "DEV001",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r004(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R005 ----------------

def test_r005_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [190000]

    ctx = {
        "user_id": "U001",
        "amount": 20000,
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r005(cursor, ctx)

    assert triggered is True
    assert "R005" in reason


def test_r005_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [100000]

    ctx = {
        "user_id": "U001",
        "amount": 10000,
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r005(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R006 ----------------

def test_r006_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [2]

    ctx = {
        "email": "test@example.com",
    }

    triggered, reason = check_r006(cursor, ctx)

    assert triggered is True
    assert "R006" in reason


def test_r006_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [1]

    ctx = {
        "email": "test@example.com",
    }

    triggered, reason = check_r006(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R007 ----------------

def test_r007_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = ["Fraud Activity"]

    ctx = {
        "ip_address": "192.168.1.100",
    }

    triggered, reason = check_r007(cursor, ctx)

    assert triggered is True
    assert "R007" in reason


def test_r007_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = None

    ctx = {
        "ip_address": "192.168.1.100",
    }

    triggered, reason = check_r007(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R008 ----------------

def test_r008_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [2]

    ctx = {
        "user_id": "U001",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r008(cursor, ctx)

    assert triggered is True
    assert "R008" in reason


def test_r008_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [1]

    ctx = {
        "user_id": "U001",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r008(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R009 ----------------

def test_r009_should_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [5]

    ctx = {
        "address": "Chennai",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r009(cursor, ctx)

    assert triggered is True
    assert "R009" in reason


def test_r009_should_not_trigger():
    cursor = MagicMock()
    cursor.fetchone.return_value = [4]

    ctx = {
        "address": "Chennai",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r009(cursor, ctx)

    assert triggered is False
    assert reason is None


# ---------------- R010 ----------------

def test_r010_should_trigger():
    cursor = MagicMock()

    # First fetchone() -> distinct devices
    # Second fetchone() -> current device not used before
    cursor.fetchone.side_effect = [
        [1],
        [0],
    ]

    ctx = {
        "user_id": "U001",
        "device_id": "DEV002",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r010(cursor, ctx)

    assert triggered is True
    assert "R010" in reason


def test_r010_should_not_trigger():
    cursor = MagicMock()

    cursor.fetchone.side_effect = [
        [1],
        [1],
    ]

    ctx = {
        "user_id": "U001",
        "device_id": "DEV001",
        "order_timestamp": "2026-07-08 10:00:00",
    }

    triggered, reason = check_r010(cursor, ctx)

    assert triggered is False
    assert reason is None