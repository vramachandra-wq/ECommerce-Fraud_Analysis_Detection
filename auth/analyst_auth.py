from typing import Optional, Dict, Set, Any, Tuple

from auth.passwords import hash_password, upgrade_password_if_needed, verify_password

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

ROLE_ADMIN = "Admin"
ROLE_SENIOR_ANALYST = "Senior Fraud Analyst"
ROLE_FRAUD_ANALYST = "Fraud Analyst"

CREATABLE_ROLES_ADMIN = [ROLE_FRAUD_ANALYST, ROLE_SENIOR_ANALYST, ROLE_ADMIN]
CREATABLE_ROLES_NON_ADMIN = [ROLE_FRAUD_ANALYST, ROLE_SENIOR_ANALYST]


# --- AUTHENTICATION & AUTHORIZATION ---

def authenticate_analyst(
    cursor,
    username: str,
    password: str,
    conn=None,
) -> Optional[Dict[str, Any]]:
    """Validates analyst credentials and returns their profile if successful."""
    cursor.execute(
        """
        SELECT analyst_id, employee_name, username, role, password
        FROM master.analyst_users
        WHERE username = %s
        """,
        (username,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    data = dict(zip(ANALYST_FIELDS + ["password"], row))
    stored_password = data.pop("password")

    if not verify_password(password, stored_password):
        return None

    if conn is not None:
        upgrade_password_if_needed(
            cursor,
            conn,
            table="master.analyst_users",
            id_column="analyst_id",
            id_value=data["analyst_id"],
            plain_password=password,
            stored_password=stored_password,
        )

    return data


MIN_PASSWORD_LENGTH = 8


def change_analyst_password(
    cursor,
    conn,
    *,
    analyst_id: str = "",
    username: str = "",
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> Tuple[bool, str]:
    """
    Change an analyst password after verifying the current password.

    Identify the account with analyst_id (logged-in) or username (login page).
    Returns (True, success_key) or (False, error_key) for UI messaging.
    """
    current_password = (current_password or "").strip()
    new_password = (new_password or "").strip()
    confirm_password = (confirm_password or "").strip()
    username = (username or "").strip()
    analyst_id = (analyst_id or "").strip()

    if not current_password or not new_password or not confirm_password:
        return False, "password_change_missing_fields"
    if not analyst_id and not username:
        return False, "password_change_missing_fields"
    if new_password != confirm_password:
        return False, "password_change_mismatch"
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, "password_change_too_short"
    if new_password == current_password:
        return False, "password_change_same_as_current"

    if analyst_id:
        cursor.execute(
            """
            SELECT analyst_id, password
            FROM master.analyst_users
            WHERE analyst_id = %s
            """,
            (analyst_id,),
        )
    else:
        cursor.execute(
            """
            SELECT analyst_id, password
            FROM master.analyst_users
            WHERE username = %s
            """,
            (username,),
        )

    row = cursor.fetchone()
    if not row:
        return False, "password_change_user_not_found"

    resolved_id, stored_password = row[0], row[1]
    if not verify_password(current_password, stored_password):
        return False, "password_change_wrong_current"

    cursor.execute(
        """
        UPDATE master.analyst_users
        SET password = %s
        WHERE analyst_id = %s
        """,
        (hash_password(new_password), resolved_id),
    )
    conn.commit()
    return True, "password_change_success"


def is_admin(analyst: Dict[str, Any]) -> bool:
    """Checks if the provided analyst profile has Admin privileges."""
    return analyst is not None and analyst.get("role") == ROLE_ADMIN


def can_create_admin_users(analyst: Dict[str, Any]) -> bool:
    """Only Admin role may create other Admin accounts."""
    return is_admin(analyst)


def creatable_roles_for(analyst: Dict[str, Any]) -> list:
    if can_create_admin_users(analyst):
        return CREATABLE_ROLES_ADMIN
    return CREATABLE_ROLES_NON_ADMIN


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
