import streamlit as st
from ui.brand import brand_wordmark_html
from ui import apply_theme, render_app_shell
from ui.i18n import t, language_toggle
from ui.customer_login import (
    apply_customer_login_theme,
    render_login_header,
    render_login_close,
    render_login_illustration,
)
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
    ALL_PAGES,
    authenticate_analyst,
    change_analyst_password,
    get_granted_pages,
    is_admin,
)


def _login_form():
    """Split-screen employee login matching the customer portal layout."""
    mode = st.session_state.get("auth_mode", "login")
    # Reuse customer split-login CSS hooks for identical chrome.
    st.markdown('<div class="customer-login-marker analyst-login-marker"></div>', unsafe_allow_html=True)

    _, row, _ = st.columns([0.04, 0.92, 0.04])
    with row:
        st.markdown('<div class="customer-login-row"></div>', unsafe_allow_html=True)
        left, right = st.columns([1.15, 0.85], gap="small")

        with left:
            if mode == "change_password":
                render_login_header(
                    logo=t("internal_app_title"),
                    welcome=t("analyst_login_welcome"),
                    title=t("change_password"),
                )
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
                render_login_close(demo_hint=t("analyst_login_hint"))

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
            else:
                render_login_header(
                    logo=t("internal_app_title"),
                    welcome=t("analyst_login_welcome"),
                    title=t("employee_login"),
                )
                with st.form("analyst_login"):
                    username = st.text_input(t("username"), placeholder="e.g. analyst1")
                    password = st.text_input(t("password"), type="password")
                    submitted = st.form_submit_button(
                        t("log_in"), type="primary", use_container_width=True
                    )
                render_login_close(demo_hint=t("analyst_login_hint"))

                if st.button(
                    t("change_password"),
                    use_container_width=True,
                    key="goto_change_password",
                ):
                    st.session_state.auth_mode = "change_password"
                    st.rerun()

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

        with right:
            render_login_illustration("images/analyst_login_hero.png")


def main():
    st.set_page_config(
        page_title="Metro Cart - Internal Portal",
        layout="wide",
        initial_sidebar_state="auto",
    )
    apply_theme()

    if "analyst" not in st.session_state:
        apply_customer_login_theme()
        language_toggle()
        _login_form()
        return

    col_shell, col_lang = st.columns([0.74, 0.26], gap="small")
    with col_shell:
        render_app_shell(t("internal_app_title"), t("internal_app_subtitle"))
    with col_lang:
        language_toggle(inline=True)

    user_data = st.session_state.analyst

    st.sidebar.markdown(
        f'<div class="sidebar-brand">{brand_wordmark_html(name=t("internal_brand"), size=24)}</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.write(t("welcome_user", name=user_data.get("employee_name", "Employee")))
    role = user_data.get("role") or ""
    if role:
        st.sidebar.markdown(
            f'<span class="sidebar-role-chip">{role}</span>',
            unsafe_allow_html=True,
        )

    if st.sidebar.button(t("log_out"), use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()

    with get_cursor() as (conn, cur):
        granted = get_granted_pages(cur, user_data)

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
