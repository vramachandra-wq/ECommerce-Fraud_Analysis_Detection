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
    
    custom_html = f"""
    <style>
        /* Outer wrapper: caps width at the report's native 1920px and
           maintains a 16:9 aspect ratio at any smaller width */
        .pbi-wrapper {{
            width: 100%;
            max-width: 1920px;
            aspect-ratio: 16 / 9;
            margin: 1rem auto 0 auto;
            border-radius: 12px; /* Rounded corners */
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.12); /* Soft drop shadow */
            overflow: hidden; /* Ensures the iframe doesn't break out of the rounded corners */
            background-color: var(--secondary-background-color); /* Loading bg follows active theme */
            border: 1px solid rgba(128, 140, 158, 0.35);
        }}
        
        /* Iframe fills the aspect-ratio-locked wrapper fluidly; Power BI's
           embed handles the internal scaling from its native 1920x1080 layout */
        .pbi-iframe {{
            width: 100%;
            height: 100%;
            border: none; /* Removes the ugly default browser iframe border */
        }}
    </style>
    
    <div class="pbi-wrapper">
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