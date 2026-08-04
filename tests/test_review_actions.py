"""Unit tests for full review actions on all flagged orders."""

from fraud_engine.review_actions import (
    review_actions_for_rule_ids,
    order_allows_reject_or_fraud,
)
from ai.order_review_summary import _heuristic_summary, _heuristic_recommendation


def test_review_actions_r001_enables_full_review():
    actions = review_actions_for_rule_ids(["R001"])
    assert actions["approve"] is True
    assert actions["reject"] is True
    assert actions["mark_fraud"] is True
    assert actions["full_review"] is True


def test_review_actions_other_rules_also_full():
    actions = review_actions_for_rule_ids(["R002", "R008"])
    assert actions["approve"] is True
    assert actions["reject"] is True
    assert actions["mark_fraud"] is True
    assert actions["full_review"] is True


def test_review_actions_mixed_is_full():
    actions = review_actions_for_rule_ids(["R002", "R001"])
    assert actions["full_review"] is True
    assert actions["reject"] is True


def test_order_allows_reject_for_any_hits():
    class FakeCur:
        def execute(self, *_a, **_k):
            return None

        def fetchall(self):
            return [("R002",)]

    assert order_allows_reject_or_fraud(FakeCur(), "ORD1") is True

    class FakeCurR001:
        def execute(self, *_a, **_k):
            return None

        def fetchall(self):
            return [("R001",)]

    assert order_allows_reject_or_fraud(FakeCurR001(), "ORD2") is True


def test_heuristic_summary_mentions_full_actions():
    ctx = {
        "order": {
            "order_id": "ORD-X",
            "product_name": "USB-C Dock",
            "amount": 7999,
            "order_status": "PENDING_REVIEW",
            "flagged_reason": "Email Velocity",
        },
        "triggered_rules": [
            {"rule_id": "R002", "rule_name": "Email Velocity"},
        ],
        "customer_history": {
            "total_orders": 4,
            "approved": 3,
            "rejected": 0,
            "fraud": 0,
            "avg_amount": 5000,
        },
        "shared_signals": {},
        "review_actions": {
            "approve": True,
            "reject": True,
            "mark_fraud": True,
            "full_review": True,
        },
    }
    text = _heuristic_summary(ctx)
    assert "ORD-X" in text
    assert "R002" in text
    assert "Approve, Reject, and Mark as Fraud" in text
    assert "advisory only" in text.lower()


def test_heuristic_recommendation_returns_action():
    rec = _heuristic_recommendation(
        {
            "triggered_rules": [{"rule_id": "R002"}],
            "customer_history": {
                "total_orders": 4,
                "approved": 3,
                "rejected": 0,
                "fraud": 0,
            },
            "shared_signals": {},
            "blacklists_active": {},
        }
    )
    assert rec["action"] in {"APPROVE", "REJECT", "MARK_FRAUD", "INVESTIGATE_FURTHER"}
    assert rec["rationale"]
