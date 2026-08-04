from fraud_engine.review_actions import review_actions_for_rule_ids


def test_review_actions_r001_full():
    actions = review_actions_for_rule_ids(["R001"])
    assert actions["approve"] is True
    assert actions["reject"] is True
    assert actions["mark_fraud"] is True
    assert actions["full_review"] is True


def test_review_actions_all_flagged_orders_full():
    actions = review_actions_for_rule_ids(["R002", "R003"])
    assert actions["approve"] is True
    assert actions["reject"] is True
    assert actions["mark_fraud"] is True
    assert actions["full_review"] is True


def test_review_actions_empty_rules_still_full():
    actions = review_actions_for_rule_ids([])
    assert actions["approve"] is True
    assert actions["reject"] is True
    assert actions["mark_fraud"] is True
    assert actions["full_review"] is True
