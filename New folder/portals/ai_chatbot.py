from ai.chatbot import render_chatbot_tab as render
from ui import apply_theme

# When run directly, ensure theme is applied then render
if __name__ == "__main__":
    apply_theme()
    render()