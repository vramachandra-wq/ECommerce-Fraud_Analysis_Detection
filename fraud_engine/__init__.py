"""Fraud engine package — rule evaluation, backlog detection, auto-approval."""

from fraud_engine.engine import evaluate_order, clear_metadata_cache
from fraud_engine.auto_approval import sync_expired_holds
from fraud_engine.backlog import (
    detect_backlog_orders,
    fetch_review_queue_with_delay,
    get_backlog_stats,
    is_backlog_order,
)

__all__ = [
    "evaluate_order",
    "clear_metadata_cache",
    "sync_expired_holds",
    "detect_backlog_orders",
    "fetch_review_queue_with_delay",
    "get_backlog_stats",
    "is_backlog_order",
]
