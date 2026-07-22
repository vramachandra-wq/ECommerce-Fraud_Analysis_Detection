"""Unit tests for pure helpers in ai/chatbot.py (mocked Groq / Streamlit)."""

from unittest.mock import MagicMock, patch

import pandas as pd

from ai.chatbot import (
    _classify_intent,
    _detect_chart_columns,
    _extract_sql,
    _extract_usage,
    _friendly_error_message,
    _get_best_axis,
    _get_followup_context,
    _get_last_result_context,
    _generate_ai_recommendations,
    _mask_address,
    _mask_email,
    _mask_ip,
    _mask_phone,
    _mask_value,
    _repair_sql,
    _restore_dataframe_types,
    _strip_sql_comments,
    _validate_sql,
    _wants_strategy_answer,
    mask_sensitive_dataframe,
    sanitize_dataframe_for_llm,
)


# ---------- strategy detection ----------

def test_wants_strategy_answer_true():
    assert _wants_strategy_answer("How can we grow revenue in weak states?") is True
    assert _wants_strategy_answer("Recommend an action plan to reduce fraud") is True


def test_wants_strategy_answer_false():
    assert _wants_strategy_answer("Show fraud rate by city") is False


# ---------- SQL extraction / validation ----------

def test_extract_sql_from_sql_fence():
    text = "Here:\n```sql\nSELECT 1;\n```\nThanks"
    assert _extract_sql(text) == "SELECT 1;"


def test_extract_sql_from_generic_fence():
    text = "```\nWITH x AS (SELECT 1) SELECT * FROM x\n```"
    assert "WITH x AS" in _extract_sql(text)


def test_extract_sql_from_bare_select():
    text = "Sure. SELECT order_id FROM master.orders LIMIT 10"
    assert _extract_sql(text).lower().startswith("select")


def test_strip_sql_comments():
    sql = """
    -- update interpretation note
    /* block comment mentioning delete */
    SELECT order_id FROM master.orders
    """
    cleaned = _strip_sql_comments(sql)
    assert cleaned.lower().startswith("select")
    assert "update interpretation" not in cleaned.lower()


def test_validate_sql_allows_select_and_with():
    ok, msg = _validate_sql("SELECT order_id FROM master.orders LIMIT 10")
    assert ok is True
    assert msg == ""

    ok, msg = _validate_sql("WITH cte AS (SELECT 1 AS n) SELECT n FROM cte")
    assert ok is True


def test_validate_sql_blocks_non_select():
    ok, msg = _validate_sql("DELETE FROM master.orders")
    assert ok is False
    assert "SELECT" in msg


def test_validate_sql_blocks_drop_keyword():
    ok, msg = _validate_sql("SELECT 1; DROP TABLE master.orders")
    assert ok is False
    assert "DROP" in msg


def test_validate_sql_comment_with_update_word_is_allowed():
    ok, msg = _validate_sql(
        "-- update the fraud flag interpretation\nSELECT order_id FROM master.orders"
    )
    assert ok is True


def test_validate_sql_duplicate_dimension_join():
    sql = """
    SELECT c.customer_name
    FROM master.orders o
    JOIN master.customers c ON c.user_id = o.user_id
    JOIN master.customers c2 ON c2.user_id = o.user_id
    """
    ok, msg = _validate_sql(sql)
    assert ok is False
    assert "customers" in msg


def test_validate_sql_cte_reusing_orders_is_allowed():
    sql = """
    WITH fraud AS (
        SELECT user_id FROM master.orders WHERE is_fraud = TRUE
    )
    SELECT o.order_id
    FROM master.orders o
    JOIN fraud f ON f.user_id = o.user_id
    """
    ok, msg = _validate_sql(sql)
    assert ok is True


# ---------- friendly errors / usage ----------

def test_friendly_error_message_by_stage():
    assert "trouble reaching" in _friendly_error_message(Exception("connection refused"), "pipeline").lower()
    assert "permission" in _friendly_error_message(Exception("permission denied"), "execution").lower()
    assert "isn't available" in _friendly_error_message(Exception("undefined column"), "execution").lower()
    assert "rephrasing" in _friendly_error_message(Exception("oops"), "generation").lower()
    assert "fix" in _friendly_error_message(Exception("oops"), "repair").lower()
    assert "summary" in _friendly_error_message(Exception("oops"), "summary").lower()
    assert "chart" in _friendly_error_message(Exception("oops"), "chart").lower()
    assert "suggestions" in _friendly_error_message(Exception("oops"), "recommendations").lower()


def test_extract_usage_present_and_missing():
    completion = MagicMock()
    completion.usage.prompt_tokens = 11
    completion.usage.completion_tokens = 7
    assert _extract_usage(completion) == (11, 7)

    empty = MagicMock()
    empty.usage = None
    assert _extract_usage(empty) == (0, 0)


# ---------- intent classification ----------

def test_classify_intent_no_history_is_new_query():
    label, in_tok, out_tok = _classify_intent(MagicMock(), "fraud by city", [])
    assert label == "NEW_QUERY"
    assert (in_tok, out_tok) == (0, 0)


@patch("ai.chatbot.create_chat_completion")
def test_classify_intent_followup(mock_create):
    completion = MagicMock()
    completion.choices[0].message.content = "FOLLOWUP_QUERY"
    completion.usage.prompt_tokens = 5
    completion.usage.completion_tokens = 2
    mock_create.return_value = completion

    history = [{"role": "user", "content": "fraud by city"}]
    label, in_tok, out_tok = _classify_intent(MagicMock(), "break that down by state", history)
    assert label == "FOLLOWUP_QUERY"
    assert (in_tok, out_tok) == (5, 2)


@patch("ai.chatbot.create_chat_completion")
def test_classify_intent_general(mock_create):
    completion = MagicMock()
    completion.choices[0].message.content = "GENERAL"
    completion.usage.prompt_tokens = 3
    completion.usage.completion_tokens = 1
    mock_create.return_value = completion

    history = [{"role": "assistant", "content": "Chennai leads"}]
    label, _, _ = _classify_intent(MagicMock(), "why might this be happening?", history)
    assert label == "GENERAL"


@patch("ai.chatbot.create_chat_completion")
def test_classify_intent_failure_falls_back_to_new_query(mock_create):
    mock_create.side_effect = Exception("API down")
    history = [{"role": "user", "content": "prior"}]
    label, in_tok, out_tok = _classify_intent(MagicMock(), "anything", history)
    assert label == "NEW_QUERY"
    assert (in_tok, out_tok) == (0, 0)


# ---------- history context helpers ----------

def test_get_last_result_context_masks_and_returns_markdown():
    history = [
        {
            "role": "assistant",
            "content": "summary",
            "df": [{"email": "john@example.com", "amount": 100}],
        }
    ]
    md = _get_last_result_context(history)
    assert "example.com" in md
    assert "100" in md
    assert "john@" not in md


def test_get_last_result_context_empty_when_no_df():
    assert _get_last_result_context([{"role": "user", "content": "hi"}]) == ""


def test_get_followup_context_includes_previous_sql_and_columns():
    history = [
        {"role": "user", "content": "fraud by city"},
        {
            "role": "assistant",
            "content": "done",
            "sql": "SELECT city, COUNT(*) FROM master.orders GROUP BY city",
            "df": [{"city": "Chennai", "count": 5}],
        },
    ]
    ctx = _get_followup_context(history)
    assert "fraud by city" in ctx
    assert "SELECT city" in ctx
    assert "Chennai" in ctx


def test_get_followup_context_empty_without_prior_result():
    assert _get_followup_context([{"role": "user", "content": "hello"}]) == ""


# ---------- masking / sanitize ----------

def test_mask_email_phone_address_ip():
    assert _mask_email("john@example.com") == "j***@example.com"
    assert _mask_phone("9876543210") == "98******10"
    assert _mask_phone("1234") == "***"
    assert _mask_address("12 Main Street Chennai") == "12 Main ***"
    assert _mask_ip("192.168.1.100") == "192.168.***.***"


def test_mask_value_by_column():
    assert _mask_value("email", "jane@test.com") == "j***@test.com"
    assert _mask_value("phone_number", "9876543210") == "98******10"
    assert _mask_value("address", "12 Main Street Chennai") == "12 Main ***"
    assert _mask_value("ip_address", "10.0.0.1") == "10.0.***.***"
    assert _mask_value("city", "Chennai") == "Chennai"


def test_mask_sensitive_dataframe_and_alias():
    df = pd.DataFrame(
        {
            "email": ["alice@example.com"],
            "phone_number": ["9876543210"],
            "ip_address": ["10.0.0.5"],
            "city": ["Chennai"],
        }
    )
    out = mask_sensitive_dataframe(df)
    assert out.loc[0, "email"] == "a****@example.com"
    assert out.loc[0, "phone_number"] == "98******10"
    assert out.loc[0, "ip_address"] == "10.0.***.***"
    assert out.loc[0, "city"] == "Chennai"
    assert df.loc[0, "email"] == "alice@example.com"

    aliased = sanitize_dataframe_for_llm(df)
    assert aliased.loc[0, "email"] == "a****@example.com"


# ---------- dataframe / chart helpers ----------

def test_restore_dataframe_types():
    df = pd.DataFrame(
        {
            "order_timestamp": ["2026-07-08 10:00:00"],
            "amount": ["1000.50"],
            "city": ["Chennai"],
        }
    )
    restored = _restore_dataframe_types(df.copy())
    assert pd.api.types.is_datetime64_any_dtype(restored["order_timestamp"])
    assert pd.api.types.is_numeric_dtype(restored["amount"])


def test_get_best_axis_and_detect_chart_columns():
    df = pd.DataFrame({"order_count": [1], "amount": [2], "other": [3]})
    assert _get_best_axis(df, ["other", "amount", "order_count"], ["count", "amount"]) == "order_count"
    assert _get_best_axis(df, [], ["count"]) is None

    chart_df = pd.DataFrame(
        {
            "order_timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "amount": [100, 200],
            "city": ["A", "B"],
        }
    )
    x, y = _detect_chart_columns(chart_df)
    assert x == "order_timestamp"
    assert y == "amount"

    status_df = pd.DataFrame({"status": ["APPROVED", "REJECTED"], "count": [10, 2]})
    x, y = _detect_chart_columns(status_df)
    assert x == "status"
    assert y == "count"

    no_num = pd.DataFrame({"city": ["A", "B"]})
    assert _detect_chart_columns(no_num) == (None, None)


# ---------- repair / recommendations with mocks ----------

@patch("ai.chatbot.st")
@patch("ai.chatbot.get_groq_client", return_value=None)
def test_repair_sql_without_client(mock_get_client, mock_st):
    sql, in_tok, out_tok = _repair_sql("SELECT 1", "error")
    assert sql == "SELECT 1"
    assert (in_tok, out_tok) == (0, 0)
    mock_st.warning.assert_called()


@patch("ai.chatbot.create_chat_completion")
@patch("ai.chatbot.get_groq_client")
def test_repair_sql_extracts_fixed_query(mock_get_client, mock_create):
    mock_get_client.return_value = MagicMock()
    completion = MagicMock()
    completion.choices[0].message.content = "```sql\nSELECT order_id FROM master.orders\n```"
    completion.usage.prompt_tokens = 9
    completion.usage.completion_tokens = 4
    mock_create.return_value = completion

    sql, in_tok, out_tok = _repair_sql("BAD SQL", "Only SELECT")
    assert sql.lower().startswith("select")
    assert (in_tok, out_tok) == (9, 4)


@patch("ai.chatbot.create_chat_completion")
def test_generate_ai_recommendations_parses_json(mock_create):
    completion = MagicMock()
    completion.choices[0].message.content = """
    ```json
    {"followups": ["Break down by state"], "business_advice": ["Focus on Chennai"]}
    ```
    """
    mock_create.return_value = completion

    df = pd.DataFrame({"city": ["Chennai"], "count": [5]})
    result = _generate_ai_recommendations(
        client=MagicMock(),
        user_query="fraud by city",
        sql_query="SELECT city, COUNT(*) FROM master.orders GROUP BY city",
        sanitized_df=df,
        executive_summary="Chennai leads",
        conversation_history="prior",
    )
    assert result["followups"] == ["Break down by state"]
    assert result["business_advice"] == ["Focus on Chennai"]


@patch("ai.chatbot.st")
@patch("ai.chatbot.create_chat_completion", side_effect=Exception("boom"))
def test_generate_ai_recommendations_failure_returns_empty(mock_create, mock_st):
    df = pd.DataFrame({"city": ["Chennai"], "count": [5]})
    result = _generate_ai_recommendations(
        client=MagicMock(),
        user_query="q",
        sql_query="SELECT 1",
        sanitized_df=df,
        executive_summary="s",
        conversation_history="",
    )
    assert result == {"followups": [], "business_advice": []}
    mock_st.caption.assert_called()
