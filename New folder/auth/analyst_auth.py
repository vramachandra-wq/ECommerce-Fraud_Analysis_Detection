from typing import Optional, Dict, Set, Any

ANALYST_FIELDS = ["analyst_id", "employee_name", "username", "role"]

# --- PAGE CONFIGURATION ---

PAGE_FRAUD_DASHBOARD = "FRAUD_DASHBOARD"
PAGE_ADMIN_PANEL = "ADMIN_PANEL"
PAGE_POWER_BI = "POWER_BI_DASHBOARD"
PAGE_AI_CHATBOT = "AI_CHATBOT"

ALL_PAGES = [PAGE_FRAUD_DASHBOARD, PAGE_ADMIN_PANEL, PAGE_POWER_BI, PAGE_AI_CHATBOT]

PAGE_LABELS = {
    PAGE_FRAUD_DASHBOARD: "Fraud Analyst Dashboard",
    PAGE_ADMIN_PANEL: "Admin Control Panel",
    PAGE_POWER_BI: "Analytics Dashboards",
    PAGE_AI_CHATBOT: "AI Chatbot",
}


# --- AUTHENTICATION & AUTHORIZATION ---

def authenticate_analyst(cursor, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates analyst credentials and returns their profile profile if successful."""
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


def is_admin(analyst: Dict[str, Any]) -> bool:
    """Checks if the provided analyst profile has Admin privileges."""
    return analyst is not None and analyst.get("role") == "Admin"


def get_granted_pages(cursor, analyst: Dict[str, Any]) -> Set[str]:
    """
    Fetches the set of page keys this analyst may access. 
    Admins automatically receive full access.
    
    BEST PRACTICE: Call this ONCE during login and store the result in 
    st.session_state to prevent redundant database queries on every UI rerun.
    """
    if is_admin(analyst):
        return set(ALL_PAGES)
        
    cursor.execute(
        """
        SELECT page_key 
        FROM master.analyst_permissions 
        WHERE analyst_id = %s AND granted = TRUE
        """,
        (analyst["analyst_id"],),
    )
    return {row[0] for row in cursor.fetchall()}


def has_page_access(granted_pages: Set[str], page_key: str) -> bool:
    """
    Checks if a page key exists in the analyst's granted pages.
    
    Refactored to accept the set of granted_pages directly instead of 
    a cursor to prevent N+1 database querying issues in the frontend UI.
    """
    return page_key in granted_pages