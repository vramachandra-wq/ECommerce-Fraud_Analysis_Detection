import json
from typing import Any, Optional

import pandas as pd

from database.connection import get_cursor


def log_chatbot_interaction(
    prompt: str,
    generated_sql: Optional[str],
    result_table: Optional[Any],
    generated_summary: Optional[str],
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Write a chatbot interaction record to master.ai_chat_logs."""
    stored_result = None

    if result_table is not None:
        if isinstance(result_table, pd.DataFrame):
            stored_result = result_table.to_dict(orient="records")
        else:
            stored_result = result_table

    with get_cursor(commit=True) as (conn, cur):
        cur.execute(
            """
            INSERT INTO master.ai_chat_logs (
                prompt, generated_sql, result_table,
                generated_summary, input_tokens, output_tokens
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                prompt,
                generated_sql,
                json.dumps(stored_result, default=str) if stored_result is not None else None,
                generated_summary,
                input_tokens,
                output_tokens,
            ),
        )
