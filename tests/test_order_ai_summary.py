"""Unit tests for AI order-review summary gating (rule hits only)."""

from unittest.mock import MagicMock, patch

from ai.order_review_summary import get_or_create_order_ai_summary, order_has_rule_hits


def test_order_has_rule_hits_true():
    cur = MagicMock()
    cur.fetchone.return_value = (1,)
    assert order_has_rule_hits(cur, "ORD1") is True


def test_order_has_rule_hits_false():
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert order_has_rule_hits(cur, "ORD1") is False


@patch("ai.order_review_summary.insert_order_ai_summary_log")
@patch("ai.order_review_summary.ensure_order_ai_summary_logs_table")
@patch("ai.order_review_summary.ensure_order_ai_summaries_table")
@patch("ai.order_review_summary.order_has_rule_hits", return_value=False)
def test_summary_skipped_without_rule_hits(_hits, _ensure, _ensure_logs, mock_db_log):
    cur = MagicMock()
    result = get_or_create_order_ai_summary(cur, "ORD-CLEAN")
    assert result is None
    mock_db_log.assert_called()
    kwargs = mock_db_log.call_args.kwargs
    assert kwargs["event"] == "skipped_no_hits"
    assert kwargs["order_id"] == "ORD-CLEAN"


@patch("ai.order_review_summary.insert_order_ai_summary_log")
@patch("ai.order_review_summary.ensure_order_ai_summary_logs_table")
@patch("ai.order_review_summary.ensure_order_ai_summaries_table")
@patch("ai.order_review_summary.fetch_order_ai_summary")
@patch("ai.order_review_summary.order_has_rule_hits", return_value=True)
def test_summary_cache_hit_logged(_hits, mock_fetch, _ensure, _ensure_logs, mock_db_log):
    cur = MagicMock()
    mock_fetch.return_value = {
        "summary_text": "Cached brief",
        "source": "groq",
        "model_name": "llama",
        "updated_at": None,
    }
    result = get_or_create_order_ai_summary(cur, "ORD-1")
    assert result["cached"] is True
    assert mock_db_log.call_args.kwargs["event"] == "cache_hit"
