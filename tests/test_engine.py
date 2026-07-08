from unittest.mock import patch

from fraud_engine.engine import evaluate_order


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

    with patch("fraud_engine.engine.RULE_CHECKS", [("R001", mock_rule)]):
        result = evaluate_order(None, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 1


def test_r007_rejected():
    def mock_rule(cursor, ctx):
        return True, "R007: Blacklisted IP"

    with patch("fraud_engine.engine.RULE_CHECKS", [("R007", mock_rule)]):
        result = evaluate_order(None, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True


def test_multiple_rules_highest_priority_wins():
    def r001(cursor, ctx):
        return True, "R001: Hold"

    def r007(cursor, ctx):
        return True, "R007: Blacklisted"

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R001", r001),
            ("R007", r007),
        ],
    ):
        result = evaluate_order(None, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True
    assert len(result["triggered_rules"]) == 2


def test_multiple_review_rules():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r003(cursor, ctx):
        return True, "R003: IP Velocity"

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R003", r003),
        ],
    ):
        result = evaluate_order(None, {})

    assert result["order_status"] == "PENDING_REVIEW"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 2


def test_flagged_reason_contains_all_rules():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r005(cursor, ctx):
        return True, "R005: Spend Velocity"

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R005", r005),
        ],
    ):
        result = evaluate_order(None, {})

    assert "R002" in result["flagged_reason"]
    assert "R005" in result["flagged_reason"]