import streamlit as st
from portals.customer_portal import render 

def main():
    st.set_page_config(
        page_title="Metro Cart - Customer Portal", 
        layout="wide"
    )
    
    # Call the render function from customer_portal.py
    render()

if __name__ == "__main__":
    main()