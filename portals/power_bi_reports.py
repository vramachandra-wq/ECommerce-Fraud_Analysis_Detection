import streamlit as st
from config import POWER_BI_EMBED_URL

def show_powerbi_dashboard():
    st.title("Analytics Dashboards")
    
    # 1. Fetch your secure embed link from config
    embed_url = POWER_BI_EMBED_URL
    
    # Safety check: ensure the URL actually loaded
    if not embed_url:
        st.error("⚠️ Error: POWER_BI_EMBED_URL is missing from the .env file.")
        return
    
    # 2. Write the raw HTML and CSS
    # We use CSS to create a styled container for the iframe
    custom_html = f"""
    <style>
        /* Container styling for shadows and rounded corners */
        .pbi-container {{
            width: 100%;
            height: 75vh; /* Responsive height: 75% of the user's screen */
            border-radius: 12px; /* Rounded corners */
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.12); /* Soft drop shadow */
            overflow: hidden; /* Ensures the iframe doesn't break out of the rounded corners */
            background-color: #f4f6f8; /* Soft background color while loading */
            margin-top: 1rem;
            border: 1px solid #e0e0e0;
        }}
        
        /* Iframe styling to fill the container completely */
        .pbi-iframe {{
            width: 100%;
            height: 100%;
            border: none; /* Removes the ugly default browser iframe border */
        }}
    </style>
    
    <div class="pbi-container">
        <iframe 
            class="pbi-iframe"
            title="E-commerce Fraud Analysis"
            src="{embed_url}" 
            allowFullScreen="true">
        </iframe>
    </div>
    """
    
    # 3. Render the HTML in Streamlit
    st.markdown(custom_html, unsafe_allow_html=True)