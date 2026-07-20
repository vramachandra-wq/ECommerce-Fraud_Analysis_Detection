import streamlit as st
from ui import apply_theme, render_app_shell
from portals.analyst_dashboard import render as render_dashboard
from portals.admin_panel import render as render_admin_panel
from portals.ai_chatbot import render as render_ai_chatbot

# 1. Import your new Power BI module here
from portals.power_bi_reports import show_powerbi_dashboard as render_power_bi

from database.connection import get_cursor
from auth.analyst_auth import (
    PAGE_ADMIN_PANEL,
    PAGE_AI_CHATBOT,
    PAGE_FRAUD_DASHBOARD,
    PAGE_POWER_BI,        # <-- Make sure to add this to your auth module
    PAGE_LABELS,
    ALL_PAGES,
    authenticate_analyst,
    get_granted_pages,
    is_admin,
)

def _login_form():
    st.title("🏢 Metro Cart Internal")
    st.subheader("Employee Login")
    
    # Note: Streamlit's st.form doesn't natively support a 'width' argument, 
    # but left it as you had it in case you are using a custom wrapper.
    with st.form("analyst_login"):
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
    apply_theme()
    render_app_shell("Metro Cart PRO", "Fraud Analyst Workspace")

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
    with get_cursor() as (conn, cur):
        granted = get_granted_pages(cur, user_data)

    # 2. Add the Power BI page to your router dictionary
    page_renderers = {
        PAGE_FRAUD_DASHBOARD: render_dashboard,
        PAGE_ADMIN_PANEL: render_admin_panel,
        PAGE_POWER_BI: render_power_bi,     # <-- Maps the auth constant to your function
        PAGE_AI_CHATBOT: render_ai_chatbot,
    }
    
    # 3. Add the Power BI page to the available tuple to check against granted permissions
    available = [p for p in ALL_PAGES if p in granted]

    if not available:
        st.warning("You don't have access to any pages yet. Contact an Admin to request access.")
        return

    if len(available) > 1:
        choice_label = st.sidebar.radio("Navigation", [PAGE_LABELS[p] for p in available])
        choice = next(p for p in available if PAGE_LABELS[p] == choice_label)
    else:
        choice = available[0]

    # Re-verify at render time
    if choice not in granted:
        st.error("Access Denied.")
        return
        
    # Render the selected page
    page_renderers[choice]()

if __name__ == "__main__":
    main()