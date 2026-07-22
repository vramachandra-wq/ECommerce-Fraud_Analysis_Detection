"""
Chatbot integration tests — best-practice mix:

1. Default (`integration`): mock Groq, hit real PostgreSQL for SQL execution + logging.
2. Optional (`live_groq`): call real Groq when RUN_LIVE_GROQ=1 and a key is configured.

Run:
  .\\.venv\\Scripts\\python.exe -m pytest -m integration -q
  $env:RUN_LIVE_GROQ=1; .\\.venv\\Scripts\\python.exe -m pytest -m live_groq -q
"""

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ai.chatbot import (
    _classify_intent,
    _extract_sql,
    _strip_sql_comments,
    _validate_sql,
    mask_sensitive_dataframe,
)
from config import is_groq_api_key_configured
from database.transaction_repository import log_chatbot_interaction


pytestmark = pytest.mark.integration


SAFE_AGG_SQL = """
SELECT order_status, COUNT(*) AS order_count
FROM master.orders
GROUP BY order_status
ORDER BY order_count DESC
LIMIT 20
"""


@pytest.fixture
def cleanup_chat_logs(db_cursor):
    """Delete ai_chat_logs rows created by a test (matched on prompt prefix)."""
    prompts = []

    def register(prompt: str):
        prompts.append(prompt)
        return prompt

    yield register

    for prompt in prompts:
        db_cursor.execute(
            "DELETE FROM master.ai_chat_logs WHERE prompt = %s",
            (prompt,),
        )


def test_chatbot_validate_and_execute_sql_on_real_db(db_conn):
    """Mocked-LLM path step: validated SELECT runs against live Postgres."""
    ok, err = _validate_sql(SAFE_AGG_SQL)
    assert ok is True, err

    sql = _strip_sql_comments(SAFE_AGG_SQL)
    df = pd.read_sql_query(sql, db_conn)

    assert isinstance(df, pd.DataFrame)
    assert "order_status" in df.columns
    assert "order_count" in df.columns
    assert len(df) >= 1


def test_chatbot_masks_pii_then_logs_to_ai_chat_logs(
    db_conn, db_cursor, cleanup_chat_logs, unique_suffix
):
    """Full non-UI pipeline: SQL -> real DB -> mask -> write ai_chat_logs."""
    prompt = cleanup_chat_logs(f"E2E chatbot fraud-by-status {unique_suffix}")

    ok, err = _validate_sql(SAFE_AGG_SQL)
    assert ok is True, err

    result_df = pd.read_sql_query(_strip_sql_comments(SAFE_AGG_SQL), db_conn)
    # Attach a fake PII column to prove masking before log
    result_df = result_df.copy()
    result_df["email"] = "analyst.check@example.com"
    sanitized = mask_sensitive_dataframe(result_df)

    assert "analyst.check@" not in sanitized["email"].astype(str).iloc[0]
    assert "@example.com" in sanitized["email"].astype(str).iloc[0]

    summary = "E2E summary: order statuses aggregated successfully."
    log_chatbot_interaction(
        prompt=prompt,
        generated_sql=_strip_sql_comments(SAFE_AGG_SQL),
        result_table=sanitized.head(5),
        generated_summary=summary,
        input_tokens=12,
        output_tokens=34,
    )

    db_cursor.execute(
        """
        SELECT generated_sql, generated_summary, input_tokens, output_tokens, result_table
        FROM master.ai_chat_logs
        WHERE prompt = %s
        ORDER BY created_at DESC NULLS LAST, ctid DESC
        LIMIT 1
        """,
        (prompt,),
    )
    row = db_cursor.fetchone()
    assert row is not None
    generated_sql, generated_summary, in_tok, out_tok, result_table = row
    assert "order_status" in (generated_sql or "")
    assert generated_summary == summary
    assert in_tok == 12
    assert out_tok == 34
    assert result_table is not None


@patch("ai.chatbot.create_chat_completion")
def test_chatbot_mocked_llm_sql_then_real_db_execution(mock_create, db_conn):
    """Simulate Groq returning SQL, then execute that SQL on the real DB."""
    completion = MagicMock()
    completion.choices[0].message.content = f"```sql\n{SAFE_AGG_SQL.strip()}\n```"
    completion.usage.prompt_tokens = 20
    completion.usage.completion_tokens = 40
    mock_create.return_value = completion

    # Intent with history forces a Groq call; return NEW_QUERY label via mock
    # is not needed here — we only exercise SQL generation shape.
    raw = completion.choices[0].message.content
    sql = _extract_sql(raw)
    ok, err = _validate_sql(sql)
    assert ok is True, err

    df = pd.read_sql_query(_strip_sql_comments(sql), db_conn)
    assert not df.empty


@patch("ai.chatbot.create_chat_completion")
def test_chatbot_mocked_intent_classifier_with_history(mock_create):
    completion = MagicMock()
    completion.choices[0].message.content = "FOLLOWUP_QUERY"
    completion.usage.prompt_tokens = 5
    completion.usage.completion_tokens = 2
    mock_create.return_value = completion

    label, in_tok, out_tok = _classify_intent(
        MagicMock(),
        "break that down by state",
        [{"role": "user", "content": "fraud by city"}],
    )
    assert label == "FOLLOWUP_QUERY"
    assert (in_tok, out_tok) == (5, 2)


def test_chatbot_blocks_unsafe_sql_before_db():
    ok, err = _validate_sql("DELETE FROM master.orders WHERE true")
    assert ok is False
    assert "SELECT" in err or "DELETE" in err or "Blocked" in err


# ---------- optional live Groq smoke (off by default) ----------

@pytest.mark.live_groq
def test_live_groq_intent_smoke():
    """Real Groq call — skipped unless RUN_LIVE_GROQ=1 and API key is configured."""
    if os.environ.get("RUN_LIVE_GROQ", "").strip() != "1":
        pytest.skip("Set RUN_LIVE_GROQ=1 to enable live Groq smoke tests")
    if not is_groq_api_key_configured():
        pytest.skip("GROQ_API_KEY is not configured")

    from ai.groq_client import get_groq_client

    client = get_groq_client()
    assert client is not None

    history = [
        {"role": "user", "content": "Show fraud rate by city"},
        {"role": "assistant", "content": "Chennai leads with 12%."},
    ]
    label, in_tok, out_tok = _classify_intent(
        client,
        "why might this be happening?",
        history,
    )
    assert label in {"NEW_QUERY", "FOLLOWUP_QUERY", "GENERAL"}
    assert in_tok >= 0
    assert out_tok >= 0
