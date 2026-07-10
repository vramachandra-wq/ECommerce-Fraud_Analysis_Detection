import streamlit as st


def log_chatbot_interaction(user_query, sql_query, result_df, summary):
    """
    Logs chatbot interactions.
    Replace with database logging later if needed.
    """
    if "chat_logs" not in st.session_state:
        st.session_state.chat_logs = []

    st.session_state.chat_logs.append({
        "user_query": user_query,
        "sql_query": sql_query,
        "summary": summary,
    })
    