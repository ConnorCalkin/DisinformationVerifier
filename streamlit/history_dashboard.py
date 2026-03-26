import streamlit as st
import db_logic as db
import chatbot as chat
import plotly.graph_objects as go


if "page" not in st.session_state:
    st.session_state.page = "Input History"

if "selected_input_id" not in st.session_state:
    st.session_state.selected_input_id = None

# -- SIDEBAR: CHAT HISTORY NAVIGATION --
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

# Fetch and display input history
try:
    history_list = db.fetch_input_history_list()
    for item in history_list:
        date_str = item["created_at"].strftime("%Y-%m-%d %H:%M")
        # Truncate to 50 chars and combine with a newline
        label = f"{date_str}: {item['input_text'][:50]}...\nSummary: {item['input_summary'][:50]}..."

        # When an item is clicked:
        if st.button(label, key=f"sidebar_{item['input_id']}", use_container_width=True):
            st.session_state.page = "Input Details"
            st.session_state.selected_input_id = item["input_id"]
            st.rerun()
except Exception as e:
    st.error(f"Error loading input history: {e}")


# # --- MAIN CONTENT ROUTER ---
# placeholder = st.empty()

# if st.session_state.page == "Input":
#     # EXISTING LOGIC:
#     render_input_screen(placeholder)

# elif st.session_state.page == "Input History List":
#     # 2. New History List Logic
#     render_history_list_screen(placeholder)

# elif st.session_state.page == "Input Detail":
#     # 3. New History Detail Logic
#     render_history_detail_screen(
#         st.session_state.selected_input_id, placeholder)

def render_history_list_screen(screen_placeholder) -> None:
    """
    Displays a list of past inputs with summaries and timestamps.
    """
    with screen_placeholder.container():
        st.header("Previous Input History")
        try:
            history_list = db.fetch_input_history_list()
            if not history_list:
                st.info("No input history found. Start by verifying a claim!")
                return
            
            for item in history_list:
                date_str = item["created_at"].strftime("%Y-%m-%d %H:%M")
                button_label = (f"📅{date_str}| 📝 {item['input_text'][:50]}...\nSummary: {item['input_summary'][:50]}...")
                if st.button(button_label, key=f"sidebar_{item['input_id']}", use_container_width=True):
                    st.session_state.page = "Input Detail"
                    st.session_state.selected_input_id = item["input_id"]
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading input history: {e}")


def render_history_detail_screen(input_id: int, screen_placeholder) -> None:
    # 1. Fetch the full joined data from RDS
    rows = db.fetch_input_details(input_id)

    if not rows:
        st.error("Could not find data for this record.")
        return

    # 2. Format the data to match your existing UI logic
    # We turn the database rows into the dictionary list your functions expect
    formatted_claims = [
        {
            'claim': r['claim_text'],
            'rating': r['rating'],
            'evidence': r['evidence']
        } for r in rows
    ]

    with screen_placeholder.container():
        if st.button("⬅️ Back to History"):
            st.session_state.page = "Input History List"
            st.rerun()

        st.title("Analysis Results")
        st.info(f"Original Input: {rows[0]['input_text']}")

        # 3. REUSE YOUR EXISTING UI FUNCTIONS
        with st.container(border=True):
            chat.render_trust_metrics(formatted_claims)  # Reuses your Plotly bars

        with st.container(border=True, height=400):
            chat.render_claims(formatted_claims)  # Reuses your claim boxes
