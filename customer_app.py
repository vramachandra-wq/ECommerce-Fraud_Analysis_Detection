import streamlit as st
from ui import apply_theme, render_app_shell
from portals.customer_portal import render 

def main():
    st.set_page_config(
        page_title="Metro Cart - Customer Portal", 
        layout="wide"
    )
    apply_theme()
    render_app_shell("🛒 Metro Cart", "Customer Purchase Portal")

    # Call the render function from customer_portal.py
    render()

if __name__ == "__main__":
    main()