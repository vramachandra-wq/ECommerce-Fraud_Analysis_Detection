"""Analyst / Admin login for the Fraud Analyst Dashboard and Admin Panel."""

ANALYST_FIELDS = ["analyst_id", "employee_name", "username", "role"]


def authenticate_analyst(cursor, username: str, password: str):
    cursor.execute(
        """
        SELECT analyst_id, employee_name, username, role
        FROM master.analyst_users
        WHERE username = %s AND password = %s
        """,
        (username, password),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(ANALYST_FIELDS, row))


def is_admin(analyst: dict) -> bool:
    return analyst is not None and analyst.get("role") == "Admin"


# Page keys must exactly match the pages implemented today. Keep this list
# in sync with the pages actually rendered by analyst_app.py.
PAGE_FRAUD_DASHBOARD = "FRAUD_DASHBOARD"
PAGE_ADMIN_PANEL = "ADMIN_PANEL"
PAGE_AI_CHATBOT = "ai_chatbot"

ALL_PAGES = [PAGE_FRAUD_DASHBOARD, PAGE_ADMIN_PANEL,PAGE_AI_CHATBOT]

PAGE_LABELS = {
    PAGE_FRAUD_DASHBOARD: "Fraud Analyst Dashboard",
    PAGE_ADMIN_PANEL: "Admin Control Panel",
    PAGE_AI_CHATBOT : "Analytic Ai Chatbot"
}


def get_granted_pages(cursor, analyst: dict) -> set:
    """Pages this analyst may access. Admins always have full access."""
    if is_admin(analyst):
        return set(ALL_PAGES)
    cursor.execute(
        "SELECT page_key FROM master.analyst_permissions WHERE analyst_id = %s AND granted = TRUE",
        (analyst["analyst_id"],),
    )
    return {row[0] for row in cursor.fetchall()}


def has_page_access(cursor, analyst: dict, page_key: str) -> bool:
    return page_key in get_granted_pages(cursor, analyst)
