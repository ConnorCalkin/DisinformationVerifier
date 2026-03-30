import streamlit as st
import db_logic as db
import chatbot as chat
import plotly.graph_objects as go
import chatbot as chat

# -- SIDEBAR: CHAT HISTORY NAVIGATION --


def render_sidebar():
    with st.sidebar:
        st.title("Navigation")
        if st.button("➕ New Input", use_container_width=True):
            st.session_state.page = "Input"
            st.session_state.selected_input_id = None
            st.rerun()

        if st.button("📜 Input History", use_container_width=True):
            st.session_state.page = "Input History List"
            st.session_state.selected_input_id = None
            st.rerun()

        if st.button("ℹ️ About Us", use_container_width=True):
            st.session_state.page = "About Us"
            st.session_state.selected_input_id = None
            st.rerun()

        st.divider()

        st.caption("Quick Access (Last 5 Inputs)")
        try:
            history_items = db.fetch_input_history_list()
            # Show only the 5 most recent entries
            for item in history_items[:5]:
                label = f"🕒 {item['created_at'].strftime('%H:%M')}: {item['input_text'][:20]}..."
                if st.button(label, key=f"quick_{item['input_id']}", use_container_width=True):
                    st.session_state.page = "Input Detail"
                    st.session_state.selected_input_id = item["input_id"]
                    st.rerun()
        except Exception as e:
            st.error(f"Error fetching input history: {e}")


def render_history_list_screen(screen_placeholder) -> None:
    """
    Displays a list of past inputs with summaries and timestamps.
    """
    with screen_placeholder.container():
        st.header("Previous Input History")
        history_list = db.fetch_input_history_list()

        if not history_list:
            st.info("No input history found. Start by verifying a claim!")
            return

        for item in history_list:
            render_history_list_button(item)
            st.divider()


def render_history_list_button(item: dict) -> None:
    """ Helper function for abstraction of button rendering in the history list screen. """
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(
                f"**{item['created_at'].strftime('%Y-%m-%d %H:%M')}**")
            st.write(f"*{item['input_text'][:100]}...*")
            st.write(f"**Summary:** {item['input_summary'][:100]}...")
        with col2:
            if st.button("View Full Details", key=f"detail_{item['input_id']}"):
                st.session_state.page = "Input Detail"
                st.session_state.selected_input_id = item["input_id"]
                st.rerun()


def render_history_detail_screen(input_id: int, screen_placeholder) -> None:
    # 1. Fetch the full joined data from RDS
    rows = db.fetch_input_details(input_id)

    if not rows:
        st.error("Could not find data for this record.")
        return

    # 2. Format the data to match your existing UI logic
    # We turn the database rows into the dictionary list your functions expect
    formatted_claims = []
    for r in rows:
        formatted_claims.append({
            'claim': r['claim_text'],
            'rating': r['rating'],
            'evidence': r['evidence'],
            'sources': r['sources']
        })
    screen_placeholder.empty()  # Clear the placeholder before rendering details
    with screen_placeholder.container():
        if st.button("⬅️ Back to History"):
            st.session_state.page = "Input History List"
            st.rerun()

        st.title("Past Verifications")
        st.info(f"**Summary:** {rows[0]['input_summary']}")

        chat.render_trust_metrics(*chat.calculate_metrics(formatted_claims))
        chat.render_claims(formatted_claims)
