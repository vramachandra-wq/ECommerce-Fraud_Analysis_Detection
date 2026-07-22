"""
Centralized backlog order detection.

SINGLE SOURCE OF TRUTH
----------------------
Every module (Analyst Dashboard, Find Backlog Orders, backlog statistics,
Auto Approval Scheduler, bulk operations) MUST use the helpers in this
module. Do not reimplement backlog detection elsewhere.

Business rules
--------------
1. Candidate orders have status ON_HOLD or PENDING_REVIEW.
2. Applicable delay_minutes is read from master.rule_master via
   order_rule_hits — NEVER hardcoded.
3. When an order is associated with multiple rules, use the MAXIMUM
   delay_minutes among those rules so every triggered rule gets its
   full review window.
4. Fallback: if an order has no rule hits, use orders.delay_minutes
   (snapshot written at evaluation time), then default 60.
5. An order is backlog when:
       current_timestamp >= tagged_timestamp + delay_minutes
   where tagged_timestamp is orders.order_timestamp (Asia/Kolkata wall clock).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

DEFAULT_DELAY_MINUTES = 60
REVIEW_QUEUE_STATUSES = ("ON_HOLD", "PENDING_REVIEW")

# Interpret naive order_timestamp as Asia/Kolkata (matches app + DB session).
_TAGGED_TS = "(o.order_timestamp AT TIME ZONE 'Asia/Kolkata')"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_deadline(tagged_at: datetime, delay_minutes: int) -> datetime:
    """Return tagged_at + delay_minutes."""
    if tagged_at.tzinfo is not None:
        tagged_at = tagged_at.replace(tzinfo=None)
    return tagged_at + timedelta(minutes=int(delay_minutes or 0))


def is_backlog_order(
    tagged_at: datetime,
    delay_minutes: int,
    now: Optional[datetime] = None,
) -> bool:
    """True when Current Timestamp >= Tagged Timestamp + delay_minutes."""
    now = now or _utcnow()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return now >= compute_deadline(tagged_at, delay_minutes)


def get_applicable_delay_minutes(cursor: Any, order_id: str) -> int:
    """
    Resolve delay_minutes for one order from rule_master (max of hits).
    Falls back to orders.delay_minutes, then DEFAULT_DELAY_MINUTES.
    """
    cursor.execute(
        """
        SELECT COALESCE(
            (
                SELECT MAX(rm.delay_minutes)
                FROM master.order_rule_hits h
                JOIN master.rule_master rm ON rm.rule_id = h.rule_id
                WHERE h.order_id = o.order_id
            ),
            NULLIF(o.delay_minutes, 0),
            %s
        )
        FROM master.orders o
        WHERE o.order_id = %s
        """,
        (DEFAULT_DELAY_MINUTES, order_id),
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return DEFAULT_DELAY_MINUTES
    return int(row[0])


def _backlog_select_sql(order_ids: Optional[Sequence[str]] = None) -> str:
    """
    Shared SELECT with a single delay expression (CTE) reused for deadline
    and remaining-time calculations.
    """
    id_filter = ""
    if order_ids is not None:
        id_filter = " AND o.order_id = ANY(%s)"

    return f"""
        WITH base AS (
            SELECT
                o.order_id,
                o.user_id,
                o.customer_name,
                o.product_name,
                o.amount,
                o.order_status,
                o.flagged_reason,
                o.order_timestamp AS tagged_timestamp,
                o.delay_minutes AS order_delay_minutes,
                COALESCE(
                    (
                        SELECT MAX(rm.delay_minutes)
                        FROM master.order_rule_hits h
                        JOIN master.rule_master rm ON rm.rule_id = h.rule_id
                        WHERE h.order_id = o.order_id
                    ),
                    NULLIF(o.delay_minutes, 0),
                    {DEFAULT_DELAY_MINUTES}
                ) AS delay_minutes,
                COALESCE(
                    (
                        SELECT STRING_AGG(DISTINCT rm.rule_name, ', ' ORDER BY rm.rule_name)
                        FROM master.order_rule_hits h
                        JOIN master.rule_master rm ON rm.rule_id = h.rule_id
                        WHERE h.order_id = o.order_id
                    ),
                    COALESCE(o.flagged_reason, 'Unknown')
                ) AS rule_name,
                {_TAGGED_TS} AS tagged_tstz
            FROM master.orders o
            WHERE o.order_status IN ('ON_HOLD', 'PENDING_REVIEW')
              {id_filter}
        )
        SELECT
            order_id,
            user_id,
            customer_name,
            product_name,
            amount,
            order_status,
            flagged_reason,
            tagged_timestamp,
            order_delay_minutes,
            delay_minutes,
            rule_name,
            tagged_timestamp + (delay_minutes * INTERVAL '1 minute') AS review_deadline,
            EXTRACT(EPOCH FROM (
                (tagged_tstz + (delay_minutes * INTERVAL '1 minute')) - NOW()
            )) / 60.0 AS minutes_remaining
        FROM base
        ORDER BY tagged_timestamp ASC
    """


def _annotate_timing(df: pd.DataFrame, *, force_overdue: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    if force_overdue:
        df["is_overdue"] = True
        df["minutes_overdue"] = df["minutes_remaining"].apply(
            lambda m: abs(float(m)) if m is not None else 0.0
        )
        df["minutes_remaining_display"] = 0.0
    else:
        df["is_overdue"] = df["minutes_remaining"] <= 0
        df["minutes_overdue"] = df["minutes_remaining"].apply(
            lambda m: abs(float(m)) if m is not None and float(m) <= 0 else 0.0
        )
        df["minutes_remaining_display"] = df["minutes_remaining"].apply(
            lambda m: max(0.0, float(m)) if m is not None else 0.0
        )
    return df


def fetch_review_queue_with_delay(cursor: Any) -> pd.DataFrame:
    """
    All ON_HOLD / PENDING_REVIEW orders with live delay_minutes from
    rule_master and remaining/overdue timing. Used by dashboards.
    """
    cursor.execute(_backlog_select_sql())
    cols = [d.name for d in cursor.description]
    return _annotate_timing(pd.DataFrame(cursor.fetchall(), columns=cols))


def detect_backlog_orders(
    cursor: Any,
    order_ids: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """
    Identify backlog orders using the shared rule:

        NOW() >= tagged_timestamp + delay_minutes(from rule_master)
    """
    sql = _backlog_select_sql(order_ids)
    params: tuple = ()
    if order_ids is not None:
        params = (list(order_ids),)

    cursor.execute(
        f"""
        SELECT * FROM (
            {sql}
        ) q
        WHERE q.minutes_remaining <= 0
        ORDER BY q.tagged_timestamp ASC
        """,
        params,
    )
    cols = [d.name for d in cursor.description]
    return _annotate_timing(
        pd.DataFrame(cursor.fetchall(), columns=cols),
        force_overdue=True,
    )


def get_backlog_stats(cursor: Any) -> Dict[str, Any]:
    """Aggregate backlog metrics for dashboard cards."""
    df = detect_backlog_orders(cursor)
    if df.empty:
        return {
            "total_backlog": 0,
            "oldest_order_id": None,
            "oldest_tagged_at": None,
            "max_minutes_overdue": 0.0,
        }
    oldest = df.iloc[0]
    return {
        "total_backlog": int(len(df)),
        "oldest_order_id": oldest["order_id"],
        "oldest_tagged_at": oldest["tagged_timestamp"],
        "max_minutes_overdue": float(df["minutes_overdue"].max()),
    }


def lock_backlog_order_ids(cursor: Any, order_ids: Optional[Sequence[str]] = None) -> List[str]:
    """
    Lock backlog rows for update (SKIP LOCKED) to prevent concurrent
    analysts / scheduler from processing the same orders.
    """
    backlog = detect_backlog_orders(cursor, order_ids=order_ids)
    if backlog.empty:
        return []

    ids = backlog["order_id"].tolist()
    cursor.execute(
        """
        SELECT order_id
        FROM master.orders
        WHERE order_id = ANY(%s)
          AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        FOR UPDATE SKIP LOCKED
        """,
        (ids,),
    )
    return [row[0] for row in cursor.fetchall()]
