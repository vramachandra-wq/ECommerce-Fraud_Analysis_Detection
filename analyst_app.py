import streamlit as st
from ui import apply_theme, render_app_shell
from ui.i18n import t, language_toggle
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
    change_analyst_password,
    get_granted_pages,
    is_admin,
)


def _login_form():
    """Login page with optional change-password flow (before session starts)."""
    mode = st.session_state.get("auth_mode", "login")

    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        if mode == "change_password":
            st.markdown("### " + t("change_password"))
            st.caption(t("password_change_login_hint"))

            with st.form("analyst_change_password_login"):
                username = st.text_input(t("username"), key="cp_login_username")
                current_password = st.text_input(
                    t("current_password"), type="password", key="cp_login_current"
                )
                new_password = st.text_input(
                    t("new_password"), type="password", key="cp_login_new"
                )
                confirm_password = st.text_input(
                    t("confirm_new_password"), type="password", key="cp_login_confirm"
                )
                submitted = st.form_submit_button(
                    t("update_password"), use_container_width=True, type="primary"
                )

            if submitted:
                with get_cursor(commit=True) as (conn, cur):
                    ok, message_key = change_analyst_password(
                        cur,
                        conn,
                        username=username,
                        current_password=current_password,
                        new_password=new_password,
                        confirm_password=confirm_password,
                    )
                if ok:
                    st.success(t("password_change_then_login"))
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error(t(message_key))

            if st.button(t("back_to_login"), use_container_width=True, key="back_to_login_btn"):
                st.session_state.auth_mode = "login"
                st.rerun()
            return

        st.markdown("### " + t("employee_login"))
        with st.form("analyst_login"):
            username = st.text_input(t("username"))
            password = st.text_input(t("password"), type="password")
            submitted = st.form_submit_button(t("log_in"), use_container_width=True)

        if submitted:
            with get_cursor(commit=True) as (conn, cur):
                user = authenticate_analyst(cur, username, password, conn=conn)

            if user:
                st.session_state.analyst = user
                if is_admin(user):
                    st.session_state.admin = user
                st.session_state.pop("auth_mode", None)
                st.rerun()
            else:
                st.error(t("invalid_login_analyst"))

        if st.button(t("change_password"), use_container_width=True, key="goto_change_password"):
            st.session_state.auth_mode = "change_password"
            st.rerun()


def main():
    st.set_page_config(
        page_title="Metro Cart - Internal Portal",
        layout="wide"
    )
    apply_theme()
    language_toggle()
    render_app_shell(t("internal_app_title"), t("internal_app_subtitle"))

    # Render main login if the base analyst session is missing
    if "analyst" not in st.session_state:
        _login_form()
        return

    user_data = st.session_state.analyst

    # Centralized Sidebar & Logout
    st.sidebar.title(t("internal_brand"))
    st.sidebar.write(t("welcome_user", name=user_data.get("employee_name", "Employee")))

    if st.sidebar.button(t("log_out"), use_container_width=True):
        st.session_state.clear()  # Clears all auth keys safely
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

    nav_labels = {
        PAGE_FRAUD_DASHBOARD: t("nav_fraud_dashboard"),
        PAGE_ADMIN_PANEL: t("nav_admin_panel"),
        PAGE_POWER_BI: t("nav_power_bi"),
        PAGE_AI_CHATBOT: t("nav_ai_chatbot"),
    }

    if not available:
        st.warning(t("no_page_access"))
        return

    if len(available) > 1:
        choice_label = st.sidebar.radio(t("nav_title"), [nav_labels[p] for p in available])
        choice = next(p for p in available if nav_labels[p] == choice_label)
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
