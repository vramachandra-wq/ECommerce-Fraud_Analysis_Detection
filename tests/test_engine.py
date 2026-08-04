from unittest.mock import MagicMock, patch

from fraud_engine.engine import clear_metadata_cache, evaluate_order


def _cursor_with_rule_meta(action: str, delay_minutes: int = 60):
    """Cursor that returns rule_master metadata for _get_rule_metadata."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (action, delay_minutes)
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

    cursor = _cursor_with_rule_meta("HOLD", 180)

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

    cursor = _cursor_with_rule_meta("REJECTED", 60)

    with patch("fraud_engine.engine.RULE_CHECKS", [("R007", mock_rule)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True


def test_r001_hold_beats_other_flagged_rules():
    """P2 iPhone (R001) forces ON_HOLD for 180 mins even when a blacklist also fires."""

    def r001(cursor, ctx):
        return True, "R001: Hold"

    def r007(cursor, ctx):
        return True, "R007: Blacklisted"

    cursor = MagicMock()
    cursor.fetchone.return_value = ("HOLD", 180)

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R001", r001),
            ("R007", r007),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 2
    assert "R001" in result["flagged_reason"]
    assert "R007" in result["flagged_reason"]


def test_blacklist_still_rejects_without_r001():
    """Without R001, tier-0 blacklist rejection still wins over review rules."""

    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r007(cursor, ctx):
        return True, "R007: Blacklisted"

    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ("REJECTED", 60),  # R007 deciding tier
        ("REVIEW", 60),    # R002 delay metadata (ignored for REJECTED)
    ]

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R007", r007),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "REJECTED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is True
    assert len(result["triggered_rules"]) == 2


def test_multiple_review_rules_use_max_delay():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r003(cursor, ctx):
        return True, "R003: IP Velocity"

    cursor = _cursor_with_rule_meta("REVIEW", 60)

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [
            ("R002", r002),
            ("R003", r003),
        ],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "PENDING_REVIEW"
    assert result["delay_minutes"] == 60
    assert result["is_fraud"] is False
    assert len(result["triggered_rules"]) == 2


def test_flagged_reason_contains_all_rules():
    def r002(cursor, ctx):
        return True, "R002: Email Velocity"

    def r005(cursor, ctx):
        return True, "R005: Spend Velocity"

    cursor = _cursor_with_rule_meta("REVIEW", 60)

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


def test_hold_reads_delay_minutes_from_rule_master():
    def mock_rule(cursor, ctx):
        return True, "R001: Hold"

    cursor = _cursor_with_rule_meta("HOLD", 180)

    with patch("fraud_engine.engine.RULE_CHECKS", [("R001", mock_rule)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180


def test_max_delay_across_triggered_rules():
    """When multiple HOLD/REVIEW rules fire, order delay is the max of their delays."""

    def r001(cursor, ctx):
        return True, "R001: Hold"

    def r002(cursor, ctx):
        return True, "R002: Review"

    cursor = MagicMock()
    # Cache: R001 fetched once in status loop; R002 fetched once in delay loop.
    cursor.fetchone.side_effect = [
        ("HOLD", 180),   # R001
        ("REVIEW", 60),  # R002
    ]

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [("R001", r001), ("R002", r002)],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180


def test_pass_rule_delay_does_not_inflate_hold_timeout():
    """PASS rules keep stored delay_minutes but must not affect review timeout."""

    def r002(cursor, ctx):
        return True, "R002: Pass"

    def r001(cursor, ctx):
        return True, "R001: Hold"

    cursor = MagicMock()
    # R001 hard-overrides status to ON_HOLD @ 180; PASS sibling delay must not apply.
    # R001 hold window is fixed at 180 minutes regardless of the DB row value.
    cursor.fetchone.side_effect = [
        ("HOLD", 60),   # R001 status/delay metadata (forced to 180)
        ("PASS", 999),  # R002 delay metadata
    ]

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [("R002", r002), ("R001", r001)],
    ):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180


def test_pass_only_has_zero_delay():
    def r002(cursor, ctx):
        return True, "R002: Pass"

    cursor = _cursor_with_rule_meta("PASS", 120)

    with patch("fraud_engine.engine.RULE_CHECKS", [("R002", r002)]):
        result = evaluate_order(cursor, {})

    assert result["order_status"] == "APPROVED"
    assert result["delay_minutes"] == 0
    assert result["is_fraud"] is False


def test_multi_item_product_rule_only_on_matching_line():
    """R001 runs per line; non-iPhone lines do not contribute an R001 hit."""
    from fraud_engine.engine import evaluate_order_with_items

    def r001(cursor, ctx):
        name = (ctx.get("product_name") or "").lower()
        if "iphone 16" in name:
            return True, "R001: iPhone 16 order — held"
        return False, None

    def r007(cursor, ctx):
        return False, None

    cursor = _cursor_with_rule_meta("HOLD", 180)

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [("R001", r001), ("R007", r007)],
    ), patch(
        "fraud_engine.engine.PRODUCT_SCOPED_RULE_IDS",
        frozenset({"R001"}),
    ):
        result = evaluate_order_with_items(
            cursor,
            {"program_id": "P2", "user_id": "U1", "email": "a@b.c",
             "phone_number": "1", "ip_address": "1.1.1.1", "device_id": "D1",
             "address": "x", "order_timestamp": None},
            [
                {
                    "product_id": "P-IPHONE",
                    "product_name": "iPhone 16 Pro",
                    "category": "Electronics",
                    "quantity": 1,
                    "line_amount": 1000,
                },
                {
                    "product_id": "P-SAMSUNG",
                    "product_name": "Samsung Galaxy S24",
                    "category": "Electronics",
                    "quantity": 1,
                    "line_amount": 800,
                },
            ],
        )

    assert result["order_status"] == "ON_HOLD"
    assert result["delay_minutes"] == 180
    assert len(result["triggered_rules"]) == 1
    assert "iPhone 16 Pro" in result["flagged_reason"]
    assert "Samsung" not in (result["flagged_reason"] or "")
    assert len(result["item_results"]) == 2
    assert result["item_results"][0]["order_status"] == "ON_HOLD"
    assert result["item_results"][1]["order_status"] == "APPROVED"


def test_multi_item_order_level_rule_runs_once():
    """Velocity/blacklist-style rules fire once for the basket, not per line."""
    from fraud_engine.engine import evaluate_order_with_items

    calls = {"r003": 0}

    def r003(cursor, ctx):
        calls["r003"] += 1
        return True, "R003: IP Velocity"

    def r001(cursor, ctx):
        return False, None

    cursor = _cursor_with_rule_meta("REVIEW", 60)

    with patch(
        "fraud_engine.engine.RULE_CHECKS",
        [("R001", r001), ("R003", r003)],
    ), patch(
        "fraud_engine.engine.PRODUCT_SCOPED_RULE_IDS",
        frozenset({"R001"}),
    ):
        result = evaluate_order_with_items(
            cursor,
            {"program_id": "P1", "user_id": "U1", "email": "a@b.c",
             "phone_number": "1", "ip_address": "9.9.9.9", "device_id": "D1",
             "address": "x", "order_timestamp": None},
            [
                {"product_id": "A", "product_name": "A", "quantity": 1, "line_amount": 10},
                {"product_id": "B", "product_name": "B", "quantity": 1, "line_amount": 20},
            ],
        )

    assert calls["r003"] == 1
    assert result["order_status"] == "PENDING_REVIEW"
    assert len(result["triggered_rules"]) == 1
