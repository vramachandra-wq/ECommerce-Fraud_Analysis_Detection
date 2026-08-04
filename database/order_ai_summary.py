"""Schema helpers for master.order_ai_summaries (cached AI order-review briefs)."""

from __future__ import annotations

from typing import Any, Dict, Optional

ORDER_AI_SUMMARY_DDL = """
CREATE TABLE IF NOT EXISTS master.order_ai_summaries (
    order_id          VARCHAR(20) PRIMARY KEY
                      REFERENCES master.orders(order_id) ON DELETE CASCADE,
    summary_text      TEXT        NOT NULL,
    context_snapshot  JSONB,
    model_name        VARCHAR(100),
    source            VARCHAR(30) NOT NULL DEFAULT 'heuristic',
    input_tokens      INTEGER     NOT NULL DEFAULT 0,
    output_tokens     INTEGER     NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

ORDER_AI_SUMMARY_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_order_ai_summaries_updated_at
        ON master.order_ai_summaries (updated_at DESC)
    """,
]


def ensure_order_ai_summaries_table(cur) -> None:
    """Create master.order_ai_summaries if missing (safe to call repeatedly)."""
    cur.execute(ORDER_AI_SUMMARY_DDL)
    for stmt in ORDER_AI_SUMMARY_INDEXES:
        cur.execute(stmt)


def fetch_order_ai_summary(cur, order_id: str) -> Optional[Dict[str, Any]]:
    cur.execute(
        """
        SELECT order_id, summary_text, context_snapshot, model_name, source,
               input_tokens, output_tokens, created_at, updated_at
        FROM master.order_ai_summaries
        WHERE order_id = %s
        """,
        (order_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d.name for d in cur.description]
    return dict(zip(cols, row))


def upsert_order_ai_summary(
    cur,
    *,
    order_id: str,
    summary_text: str,
    context_snapshot: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
    source: str = "heuristic",
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    import json

    cur.execute(
        """
        INSERT INTO master.order_ai_summaries (
            order_id, summary_text, context_snapshot, model_name, source,
            input_tokens, output_tokens, created_at, updated_at
        )
        VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (order_id) DO UPDATE SET
            summary_text = EXCLUDED.summary_text,
            context_snapshot = EXCLUDED.context_snapshot,
            model_name = EXCLUDED.model_name,
            source = EXCLUDED.source,
            input_tokens = EXCLUDED.input_tokens,
            output_tokens = EXCLUDED.output_tokens,
            updated_at = NOW()
        """,
        (
            order_id,
            summary_text,
            json.dumps(context_snapshot or {}),
            model_name,
            source,
            int(input_tokens or 0),
            int(output_tokens or 0),
        ),
    )
