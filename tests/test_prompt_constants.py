"""Unit tests for ai/prompt_constants.py."""

from ai import prompt_constants as pc


def test_history_and_preview_limits():
    assert pc.MAX_HISTORY == 8
    assert pc.MAX_STORED_MESSAGES == 100
    assert pc.MARKDOWN_PREVIEW_ROWS == 15


def test_token_budgets_are_positive():
    assert pc.SUMMARY_MAX_TOKENS > 0
    assert pc.INTENT_MAX_TOKENS > 0
    assert pc.ADVISORY_MAX_TOKENS > 0
    assert pc.SQL_MAX_TOKENS > 0
    assert pc.REPAIR_MAX_TOKENS > 0
    assert pc.RECOMMENDATION_MAX_TOKENS > 0


def test_reasoning_effort_values():
    allowed = {"low", "medium", "high"}
    assert pc.INTENT_REASONING_EFFORT in allowed
    assert pc.ADVISORY_REASONING_EFFORT in allowed
    assert pc.SQL_REASONING_EFFORT in allowed
    assert pc.REPAIR_REASONING_EFFORT in allowed
    assert pc.SUMMARY_REASONING_EFFORT in allowed
    assert pc.RECOMMENDATION_REASONING_EFFORT in allowed


def test_schema_context_covers_core_tables():
    schema = pc.SCHEMA_CONTEXT.lower()
    for table in (
        "master.orders",
        "master.customers",
        "master.products",
        "master.device_master",
        "master.order_rule_hits",
        "master.rule_master",
    ):
        assert table in schema
    assert "password" in schema


def test_intent_system_prompt_labels():
    prompt = pc.INTENT_SYSTEM_PROMPT
    assert "NEW_QUERY" in prompt
    assert "FOLLOWUP_QUERY" in prompt
    assert "GENERAL" in prompt


def test_sql_system_prompt_rules():
    prompt = pc.SQL_SYSTEM_PROMPT
    assert "SELECT" in prompt
    assert "WITH" in prompt
    assert "DDL" in prompt or "DML" in prompt or "Never SELECT *" in prompt


def test_summary_prompt_format():
    rendered = pc.SUMMARY_SYSTEM_PROMPT_BASE.format(
        user_query="What is the fraud rate?",
        data_preview="| city | fraud_rate |\n| --- | --- |\n| Chennai | 0.12 |",
    )
    assert "What is the fraud rate?" in rendered
    assert "Chennai" in rendered


def test_strategy_summary_prompt_format():
    rendered = pc.STRATEGY_SUMMARY_PROMPT_BASE.format(
        user_query="How can we grow revenue?",
        data_preview="state,revenue\nTN,1000",
    )
    assert "How can we grow revenue?" in rendered


def test_advisory_prompt_format():
    rendered = pc.ADVISORY_SYSTEM_PROMPT.format(
        conversation_context="USER: fraud by city",
        data_context="city | count",
        user_query="why might this be happening?",
    )
    assert "why might this be happening?" in rendered


def test_repair_prompt_template_format():
    rendered = pc.REPAIR_PROMPT_TEMPLATE.format(
        error="Only SELECT queries are permitted.",
        schema="master.orders",
        sql="DELETE FROM master.orders",
    )
    assert "Only SELECT queries are permitted." in rendered


def test_recommendation_prompt_format_and_json_shape():
    rendered = pc.AI_RECOMMENDATION_PROMPT.format(
        user_query="Top cities by fraud",
        sql_query="SELECT city FROM master.orders",
        summary="Chennai leads.",
        conversation_history="prior chat",
        data_preview="city | count",
    )
    assert '"followups"' in rendered
    assert '"business_advice"' in rendered


def test_model_config_imports_exist():
    assert hasattr(pc, "GROQ_API_KEY")
    assert hasattr(pc, "GROQ_INTENT_MODEL")
    assert hasattr(pc, "GROQ_SQL_MODEL")
    assert hasattr(pc, "GROQ_REPAIR_MODEL")
    assert hasattr(pc, "GROQ_SUMMARY_MODEL")
