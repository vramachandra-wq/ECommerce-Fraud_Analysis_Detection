from unittest.mock import MagicMock, patch

from fraud_engine.engine import clear_metadata_cache, evaluate_order


def _cursor_with_rule_meta(action: str, interval_value: int = 0, interval_unit: str = "MINUTE"):
    """Cursor that returns rule_master metadata for _get_rule_metadata."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (action, interval_value, interval_unit)
    return cursor


def setup_function():
    clear_metadata_cache()


def test_no_rules_triggered():
    with patch("fraud_engine.engine.RULE_CHECKS", []):
        result = evaluate_order(None, {})

    assert result["order_status"] == "APPROVED"
    assert result["delay_minutes"] == 0
    assert result["flagged_reason"] is None
    assert result["triggered_rules"] == []
    assert result["is_fraud"] is False


def test_r001_on_hold():
    def mock_rule(cursor, ctx):
        return True, "R001: iPhone Rule — Hold"

    cursor = _cursor_with_rule_meta("HOLD", 180, "MINUTE")

    with patch("fraud_engine.engine.RULE_CHECKS", [("R001", mock_rule)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 1
    assert result["triggered_rules"][0]["rule_id"] == "R001"


def test_r007_rejected():
    def mock_rule(cursor, ctx):
        return True, "R007: Blacklisted IP"

    cursor = _cursor_with_rule_meta("REJECTED")

    with patch("fraud_engine.engine.RULE_CHECKS", [("R007", mock_rule)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True


def test_blacklist_tier_beats_hold_rule():
    """Tier 0 blacklist (R007) decides status even when R001 also triggers."""

    def r001(cursor, ctx):
        return True, "R001: Hold"

    def r007(cursor, ctx):
        return True, "R007: Blacklisted"

    cursor = MagicMock()
    # Metadata lookups: R001 then R007 (or whichever deciding-tier rules)
    # Only R007 is in deciding tier 0, so only R007 metadata is fetched.
    cursor.fetchone.return_value = ("REJECTED", 0, "MINUTE")

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R001", r001),
            ("R007", r007),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True
    assert len(result["triggered_rules"]) == 2


def test_multiple_review_rules():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r003(cursor, ctx):
        return True, "R003: IP Velocity"

    cursor = _cursor_with_rule_meta("REVIEW")

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R003", r003),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "PENDING_REVIEW"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 2


def test_flagged_reason_contains_all_rules():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r005(cursor, ctx):
        return True, "R005: Spend Velocity"

    cursor = _cursor_with_rule_meta("REVIEW")

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R005", r005),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert "R002" in result["flagged_reason"]
    assert "R005" in result["flagged_reason"]


def test_hold_delay_converts_hours_to_minutes():
    def mock_rule(cursor, ctx):
        return True, "R001: Hold"

    cursor = _cursor_with_rule_meta("HOLD", 3, "HOUR")

    with patch("fraud_engine.engine.RULE_CHECKS", [("R001", mock_rule)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180
