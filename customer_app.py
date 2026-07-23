import streamlit as st
from ui import apply_customer_theme, apply_customer_login_theme
from ui.i18n import language_toggle
from portals.customer_portal import render


def main():
    st.set_page_config(
        page_title="Metro Cart - Customer Portal",
        layout="wide",
    )
    apply_customer_theme()

    if "customer" not in st.session_state:
        apply_customer_login_theme()
        language_toggle()  # floating white control on login
        render()
        return

    # Authenticated views render the white language toggle in the header row.
    render()


if __name__ == "__main__":
    main()
