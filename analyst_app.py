import streamlit as st
from ui import apply_theme, render_app_shell
from ui.i18n import t, language_toggle
from portals.analyst_dashboard import render as render_dashboard
from portals.admin_panel import render as render_admin_panel
from portals.ai_chatbot import render as render_ai_chatbot
from portals.power_bi_reports import show_powerbi_dashboard as render_power_bi

from database.connection import get_cursor
from auth.analyst_auth import (
    PAGE_ADMIN_PANEL,
    PAGE_AI_CHATBOT,
    PAGE_FRAUD_DASHBOARD,
    PAGE_POWER_BI,
    authenticate_analyst,
    get_granted_pages,
    is_admin,
    ALL_PAGES,
)


def _login_form():
    st.markdown('<div class="login-panel">', unsafe_allow_html=True)
    st.title(t("internal_brand"))
    st.subheader(t("employee_login"))

    with st.form("analyst_login"):
        username = st.text_input(t("username"))
        password = st.text_input(t("password"), type="password")
        submitted = st.form_submit_button(t("log_in"), use_container_width=True)

    if submitted:
        with get_cursor() as (conn, cur):
            user = authenticate_analyst(cur, username, password)

        if user:
            st.session_state.analyst = user
            if is_admin(user):
                st.session_state.admin = user
            with get_cursor() as (conn, cur):
                st.session_state.granted_pages = get_granted_pages(cur, user)
            st.rerun()
        else:
            st.error(t("invalid_login_analyst"))
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Metro Cart - Internal Portal",
        layout="wide",
        page_icon="🛡️",
    )
    apply_theme()
    language_toggle()
    render_app_shell(t("internal_app_title"), t("internal_app_subtitle"))

    if "analyst" not in st.session_state:
        _login_form()
        return

    user_data = st.session_state.analyst

    st.sidebar.title(t("internal_brand"))
    st.sidebar.write(t("welcome_user", name=user_data.get("employee_name", "Employee")))

    if st.sidebar.button(t("log_out"), use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()

    granted = st.session_state.get("granted_pages")
    if granted is None:
        with get_cursor() as (conn, cur):
            granted = get_granted_pages(cur, user_data)
        st.session_state.granted_pages = granted

    page_renderers = {
        PAGE_FRAUD_DASHBOARD: render_dashboard,
        PAGE_ADMIN_PANEL: render_admin_panel,
        PAGE_POWER_BI: render_power_bi,
        PAGE_AI_CHATBOT: render_ai_chatbot,
    }

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

    if choice not in granted:
        st.error(t("access_denied"))
        return

    page_renderers[choice]()


if __name__ == "__main__":
    main()
