import streamlit as st
from portals.analyst_dashboard import render as render_dashboard
from portals.admin_panel import render as render_admin_panel
from database.connection import get_cursor
from auth.analyst_auth import (
    PAGE_ADMIN_PANEL,
    PAGE_FRAUD_DASHBOARD,
    PAGE_LABELS,
    authenticate_analyst,
    get_granted_pages,
    is_admin,
)

def _login_form():
    st.title("🏢 Metro Cart Internal")
    st.subheader("Employee Login")
    
    with st.form("analyst_login", width=500):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=False)

    if submitted:
        with get_cursor() as (conn, cur):
            user = authenticate_analyst(cur, username, password)
            
        if user:
            # Set the exact session keys the downstream portal files are looking for
            st.session_state.analyst = user
            if is_admin(user):
                st.session_state.admin = user
            st.rerun()
        else:
            st.error("Invalid username or password.")

def main():
    st.set_page_config(
        page_title="Metro Cart - Internal Portal", 
        layout="wide"
    )
    
    # Render main login if the base analyst session is missing
    if "analyst" not in st.session_state:
        _login_form()
        return

    user_data = st.session_state.analyst
    
    # Centralized Sidebar & Logout
    st.sidebar.title("🏢 Metro Cart Internal")
    st.sidebar.write(f"Welcome, **{user_data.get('employee_name', 'Employee')}**")
    
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.clear() # Clears all auth keys safely
        st.rerun()
        
    st.sidebar.divider()

    # NAVIGATION LOGIC — driven by page-level RBAC.
    # Admins always have every page; other analysts see only pages an Admin
    # has explicitly granted them (Admin Panel -> Analyst Permissions).
    with get_cursor() as (conn, cur):
        granted = get_granted_pages(cur, user_data)

    page_renderers = {
        PAGE_FRAUD_DASHBOARD: render_dashboard,
        PAGE_ADMIN_PANEL: render_admin_panel,
    }
    available = [p for p in (PAGE_FRAUD_DASHBOARD, PAGE_ADMIN_PANEL) if p in granted]

    if not available:
        st.warning("You don't have access to any pages yet. Contact an Admin to request access.")
        return

    if len(available) > 1:
        choice_label = st.sidebar.radio("Navigation", [PAGE_LABELS[p] for p in available])
        choice = next(p for p in available if PAGE_LABELS[p] == choice_label)
    else:
        choice = available[0]

    # Re-verify at render time (not just in the choice list) so a stale
    # session_state value can never render a page that isn't granted.
    if choice not in granted:
        st.error("Access Denied.")
        return
    page_renderers[choice]()

if __name__ == "__main__":
    main()