"""Schema helpers and writers for master.order_ai_summary_logs."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

ORDER_AI_SUMMARY_LOG_DDL = """
CREATE TABLE IF NOT EXISTS master.order_ai_summary_logs (
    log_id         BIGSERIAL PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    order_id       VARCHAR(20),
    event          VARCHAR(64)  NOT NULL,
    level          VARCHAR(16)  NOT NULL DEFAULT 'INFO',
    message        TEXT         NOT NULL,
    source         VARCHAR(30),
    model_name     VARCHAR(100),
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    details        JSONB
);
"""

ORDER_AI_SUMMARY_LOG_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_created_at
        ON master.order_ai_summary_logs (created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_order_id
        ON master.order_ai_summary_logs (order_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_event
        ON master.order_ai_summary_logs (event)
    """,
]


def ensure_order_ai_summary_logs_table(cur) -> None:
    """Create master.order_ai_summary_logs if missing (safe to call repeatedly)."""
    cur.execute(ORDER_AI_SUMMARY_LOG_DDL)
    for stmt in ORDER_AI_SUMMARY_LOG_INDEXES:
        cur.execute(stmt)


def insert_order_ai_summary_log(
    cur,
    *,
    order_id: Optional[str],
    event: str,
    message: str,
    level: str = "INFO",
    source: Optional[str] = None,
    model_name: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one AI-summary lifecycle event. Failures are swallowed."""
    try:
        ensure_order_ai_summary_logs_table(cur)
        cur.execute(
            """
            INSERT INTO master.order_ai_summary_logs (
                order_id, event, level, message, source, model_name,
                input_tokens, output_tokens, details
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                order_id,
                event,
                (level or "INFO").upper(),
                message,
                source,
                model_name,
                input_tokens,
                output_tokens,
                json.dumps(details) if details is not None else None,
            ),
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to write order_ai_summary_log event=%s order_id=%s",
            event,
            order_id,
        )
