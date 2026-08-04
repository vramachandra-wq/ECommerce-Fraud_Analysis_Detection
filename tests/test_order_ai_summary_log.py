"""Tests for master.order_ai_summary_logs helpers."""

from unittest.mock import MagicMock

from database.order_ai_summary_log import (
    ORDER_AI_SUMMARY_LOG_DDL,
    ensure_order_ai_summary_logs_table,
    insert_order_ai_summary_log,
)


def test_ddl_targets_order_ai_summary_logs():
    assert "master.order_ai_summary_logs" in ORDER_AI_SUMMARY_LOG_DDL


def test_ensure_creates_table_and_indexes():
    cur = MagicMock()
    ensure_order_ai_summary_logs_table(cur)
    assert cur.execute.call_count >= 2
    assert "order_ai_summary_logs" in cur.execute.call_args_list[0].args[0]


def test_insert_writes_event():
    cur = MagicMock()
    insert_order_ai_summary_log(
        cur,
        order_id="ORD-1",
        event="created",
        message="stored",
        source="heuristic",
        input_tokens=1,
        output_tokens=2,
        details={"force_refresh": True},
    )
    # ensure + insert
    assert cur.execute.call_count >= 2
    insert_sql = cur.execute.call_args_list[-1].args[0]
    assert "INSERT INTO master.order_ai_summary_logs" in insert_sql
    params = cur.execute.call_args_list[-1].args[1]
    assert params[0] == "ORD-1"
    assert params[1] == "created"
