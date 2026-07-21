import streamlit as st
from ui import apply_theme, render_app_shell
from ui.i18n import t, language_toggle
from portals.customer_portal import render


def main():
    st.set_page_config(
        page_title="Metro Cart - Customer Portal",
        layout="wide",
        page_icon="🛒",
    )
    apply_theme()
    language_toggle()
    render_app_shell(t("customer_app_title"), t("customer_app_subtitle"))
    render()


if __name__ == "__main__":
    main()
