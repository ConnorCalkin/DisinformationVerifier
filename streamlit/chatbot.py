"""
This script will run a streamlit 'front end' for the RAG chatbot.

When a user inputs an article, url or claim. This script will extract claims from the input
(scraping a page first if it's a url).

These claims are then sent to multiple lambda functions via lambda urls.
"""

import os
import plotly.graph_objects as go
from dotenv import load_dotenv
import logging
from loading_animation import jumping_loader
from about_us import render_about_us
from streamlit_functions import (convert_llm_response_to_dict, send_url_to_web_scraping_lambda,
                                 get_summary_and_claims_from_text,
                                 send_claims_to_rag_lambda,
                                 send_claims_to_wiki_lambda, rate_claims_via_llm,
                                 setup_logging,
                                 Claim)
import db_logic as db
import history_dashboard as history
import streamlit as st

from cluster import get_claims_clustered_with_evidence

load_dotenv()


WIKI_URL = os.getenv("WIKI_URL")
RAG_URL = os.getenv("RAG_URL")
SCRAPE_URL = os.getenv("SCRAPE_URL")
LLM_URL = os.getenv("LLM_URL")

INPUT_FORMAT_URL = 'URL'
INPUT_FORMAT_CLAIM = 'Claim'
INPUT_FORMAT_ARTICLE = 'Article Text'
DEFAULT_SOURCE_OPTION = 'Choose an option...'

CATEGORY_COLORS = {
    'SUPPORTED': "#c1eaca",
    'MISLEADING': "#f0edb9",
    'CONTRADICTED': "#f0c1c1",
    'UNSURE': "#b8e2f4"
}

setup_logging()

st.set_page_config(layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "Input"

if "selected_input_id" not in st.session_state:
    st.session_state.selected_input_id = None


def apply_syft_pro_theme():
    st.markdown("""
        <style>
        /* Lightened Background (Bone White) */
        .stApp {
            background-color: #F6F3F8 !important;
        }

        /* 2. STYLE THE TABS TO BE SLEEK */
        /* Center the tab bar */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 60px;
            background-color: transparent !important;
        }
                
        /* 1. The Tab text itself (Inactive state) */
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: transparent !important;
            border: none !important;
            font-family: sans-serif;
            font-weight: 600 !important;
            color: #888 !important; /* Set inactive tabs to grey for contrast */
            font-size: 1rem !important;
            letter-spacing: 0.05em;
            transition: color 0.3s ease;
        }

        /* 2. The Active Tab (Text color & Underline) */
        /* This targets the tab when it is clicked/active */
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: #531F78 !important; /* Your Purple */
            border-bottom: 3px solid #531F78 !important; /* Matching Purple Underline */
        }

        /* 3. The Sliding Highlight (Streamlit's internal bar) */
        /* Change the sliding bar to match your purple so it doesn't flash blue */
        div[data-baseweb="tab-highlight"] {
            background-color: #531F78 !important;
        }

        /* The Analyze/Verify Button */
        div.stButton > button {
            background-color: #531F78 !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.6rem 2rem !important;
            transition: 0.3s;
        }
        
        div.stButton > button:hover {
            background-color: #331A44 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        /* Clean up the Sidebar (Hide it since we have top nav) */
        [data-testid="stSidebar"] {
            display: none;
        }
                
        /* 1. The main background of the alert box */
        div[data-testid="stAlert"] {
            background-color: #F1E6F9 !important; /* Soft Purple Background */
            border: 1px solid #531F78 !important;  /* Purple Border */
            border-radius: 8px !important;
        }

        /* 2. Target the text inside the box (The most important part) */
        div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] p {
            color: #531F78 !important; /* Dark Purple Text */
            font-weight: 500 !important;
        }

        /* 3. Target the Icon (The 'i' or '!' symbol) */
        div[data-testid="stAlert"] svg {
            fill: #531F78 !important;
            color: #531F78 !important;
        }

        /* 4. Fix for the 'X' close button if it exists */
        div[data-testid="stAlert"] button {
            color: #531F78 !important;
        }
                
        /* 1. TEXT AREA & SELECTBOX BASE STYLE */
        .stTextArea textarea, 
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important; /* Soft Purple Background */
            border: 1px solid #d1d1d1 !important;  /* Subtle grey border */
            border-radius: 10px !important;
            color: #000000 !important;             /* FORCE TYPED TEXT TO BLACK */
            -webkit-text-fill-color: #000000 !important;
        }

        /* 2. PLACEHOLDER STYLE (The 'Grey' text before typing) */
        .stTextArea textarea::placeholder {
            color: #888888 !important;             /* Professional Grey */
            -webkit-text-fill-color: #888888 !important;
            opacity: 1; 
        }

        /* 1. COMPLETELY KILL THE RED/ORANGE FOCUS RING */
        /* We target every possible layer of the Streamlit Input/Selectbox */
        [data-baseweb="base-input"]:focus-within, 
        [data-baseweb="input"]:focus-within,
        .stTextArea div:focus-within,
        .stSelectbox div:focus-within {
            border-color: #531F78 !important; /* SYFT Purple Border */
            box-shadow: 0 0 0 2px rgba(83, 31, 120, 0.2) !important; /* Soft Purple Glow */
            background-color: #ffffff !important;
        }
        /* 4. DROPDOWN (SELECTBOX) FOCUS FIX */
        /* This kills the red ring on the dropdowns specifically */
        div[data-baseweb="select"]:focus-within {
            border-color: #531F78 !important;
            box-shadow: 0 0 0 2px rgba(83, 31, 120, 0.2) !important;
            outline: none !important;
        }

        /* Ensure dropdown text is black once selected */
        div[data-baseweb="select"] span {
            color: #000000 !important;
        }

        /* 5. SYFT PURPLE FOR LABELS */
        .stTextArea label p, 
        .stSelectbox label p {
            color: #531F78 !important;
            font-weight: 600 !important;
            text-transform: none; /* Keeps labels from being all caps if preferred */
        }
                
        /* 2. ALIGN THE BOXES (EXTEND INPUT LENGTH) */
        /* Adjust the '165px' value below to get the perfect alignment with your Tip Box */
        .stTextArea textarea {
            min-height: 140px !important; 
            max-height: 140px !important;
            background-color: #ffffff !important;
            border-radius: 10px !important;
        }
                
        /* Reduce the gap at the very top of the page for the small logo */
        [data-testid="stHeader"] {
            height: 30px !important;
        }

        /* Tighten the spacing around the small image */
        [data-testid="stImage"] {
            padding-top: 0px !important;
            margin-bottom: -10px !important;
        }
                
        /* FORCE ALERT/INFO BARS TO WHITE */
        /* Target the main container and the inner colored div */
        div[data-testid="stAlert"], 
        div[data-testid="stNotificationContentInfo"],
        div[data-testid="stNotificationContentSuccess"] {
            background-color: #ffffff !important; 
            border: 1px solid #d1d1d1 !important;
            color: #531F78 !important;
            border-radius: 10px !important;
        }

        /* Ensure the text inside is dark purple on the white background */
        div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
            color: #531F78 !important;
            font-weight: 500 !important;
        }

        /* Make the icon purple */
        div[data-testid="stAlert"] svg {
            fill: #531F78 !important;
        }
        /* 1. RESET ALL ALERTS TO DEFAULT */
        /* This removes the global purple/white overrides so SUCCESS, ERROR, and WARNING revert */
        div[data-testid="stAlert"] {
            background-color: transparent !important;
            border: none !important;
        }

        /* 2. TARGET THE 'NOTE' BOX SPECIFICALLY */
        /* This looks for an info box that contains the text 'Note:' */
        div[data-testid="stNotificationContentInfo"]:has(p:contains("Note:")),
        div[data-testid="stAlert"]:has(p:contains("Note:")) {
            background-color: #F1E6F9 !important; /* Your Soft Purple */
            border: 1px solid #531F78 !important;  /* Your Dark Purple Border */
            border-radius: 8px !important;
        }

        /* 3. STYLE THE TEXT INSIDE THE PURPLE NOTE ONLY */
        div[data-testid="stAlert"]:has(p:contains("Note:")) [data-testid="stMarkdownContainer"] p {
            color: #531F78 !important;
            font-weight: 500 !important;
        }

        /* 4. STYLE THE ICON INSIDE THE PURPLE NOTE ONLY */
        div[data-testid="stAlert"]:has(p:contains("Note:")) svg {
            fill: #531F78 !important;
            color: #531F78 !important;
        }
        </style>
    """, unsafe_allow_html=True)


def display_claim_and_rating(claim: dict, box_design) -> None:
    """Display a claim and its rating"""

    claim_str, ratings = st.columns([1, 3])  # Adjust column widths as needed

    with claim_str:

        box_design(f"**Claim:** {claim['claim']}")

    with ratings:
        st.markdown(f"**Rating:** {claim['rating']}")
        st.markdown(
            f"**Evidence:** {claim['evidence']} Sources: {', '.join(claim['sources'])}")


def render_and_parse_input_boxes() -> tuple[str, str, str]:
    """
    Set up input fields for user to enter an article, url or claim.

    Will also render input fields for input format and source type

    """

    main_input, secondary_input = st.columns([5, 3.5])

    with main_input:
        user_input = st.text_area(
            label='Input an article, URL, or claim to verify:',
            placeholder="""'https://www.bbc.co.uk/news/science-environment-56837908"
            "The Earth is flat.'""",
            height=150,
            key='user_input'
        )

    with secondary_input:

        format_input, source_input = st.columns(2)

        with format_input:
            input_format = st.selectbox(
                label='Input format:',
                options=[
                    INPUT_FORMAT_URL,
                    INPUT_FORMAT_CLAIM,
                    INPUT_FORMAT_ARTICLE

                ],
                key='input_format'
            )
        with source_input:
            source_type = st.selectbox(
                label='Source type:',
                options=[DEFAULT_SOURCE_OPTION,
                         'TikTok',
                         'Instagram',
                         'Facebook',
                         'BBC',
                         'Reddit',
                         'The Guardian',
                         'GB News',
                         'The Daily Mail',
                         'The Sun',
                         'AI',
                         'Twitter/X',
                         'Other'],
                key='source_type',
                index=0
            )
        if source_type == 'Choose an option...':

            st.info("💡 Hint: Select a source type to enable verification.")

    return user_input, input_format, source_type


def add_grey_background(y_positions: list[str]) -> go.Figure:
    """Creates a grey background for each metric bar
    representing the full range."""

    fig = go.Figure(go.Bar(
        x=[1] * 4,
        y=y_positions,
        orientation='h',
        marker=dict(
            color='rgba(255,255,255, 1)',  # Transparent fill
            line={"color": 'white', "width": 1}  # invisible border
        ),
        width=0.5,
        hoverinfo='none'  # Keep the background quiet
    ))

    return fig


def add_metric_bars(fig: go.Figure, values: list[float], y_positions: list[str]) -> go.Figure:
    """Adds colored bars corresponding to the value (0-1) on top of the grey background."""

    bar_colors = [CATEGORY_COLORS.get(y, "#D3D3D3") for y in y_positions]

    fig.add_trace(go.Bar(
        x=values,
        y=y_positions,
        orientation='h',
        marker=dict(
            color=bar_colors,
            line={"width": 0}
        ),
        width=0.5
    ))

    return fig


def update_figure_layout(fig: go.Figure) -> go.Figure:
    """Updates the layout of the figure to ensure bars are overlaid and axes are hidden."""

    fig.update_layout(
        barmode='overlay',  # Crucial: prevents bars from stacking or dodging
        xaxis={"range": [0, 1], "visible": False},
        yaxis={"visible": False},
        height=100,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        bargap=0.1
    )

    return fig


def render_metric_bars(values: list[float]):
    """Displays horizontal bars with colors corresponding to the value (0-1)."""

    y_positions = ["SUPPORTED", "MISLEADING", "CONTRADICTED", "UNSURE"]

    y_positions = y_positions[::-1]
    values = values[::-1]

    fig = add_grey_background(y_positions)

    fig = add_metric_bars(fig, values, y_positions)

    fig = update_figure_layout(fig)

    st.plotly_chart(fig, use_container_width=True,
                    config={'staticPlot': True})


def render_claims(claims: list[dict]) -> None:
    """Display claims and their ratings in the Streamlit app."""

    box_designs = {  # Different colour boxes for different ratings.
        'SUPPORTED': lambda x: st.success(x),
        'MISLEADING': lambda x: st.warning(x),
        'CONTRADICTED': lambda x: st.error(x),
        'UNSURE': lambda x: st.info(x)
    }

    for claim in claims:

        box_design = box_designs.get(claim['rating'])
        with st.container(border=True):
            display_claim_and_rating(claim, box_design)


def get_unrated_claims_from_input(user_input: str, input_format: str) -> tuple[str, list[Claim]]:
    """Extract claims from the user input based on the input format."""

    if input_format == INPUT_FORMAT_CLAIM:
        summary = f"Verification of the following claim: {user_input.title()}"
        unrated_claims = [Claim(claim_text=user_input)]
        return summary, unrated_claims

    if input_format == INPUT_FORMAT_URL:
        article_body = send_url_to_web_scraping_lambda(
            user_input, SCRAPE_URL)
        return get_summary_and_claims_from_text(article_body, LLM_URL)

    if input_format == INPUT_FORMAT_ARTICLE:

        return get_summary_and_claims_from_text(user_input, LLM_URL)

    # Default return for unsupported formats, should not reach here due to input validation
    return "No summary generated", []


def get_context_from_lambdas(unrated_claims: list[Claim]) -> tuple[list[dict], list[dict]]:
    """Send claims to RAG and Wikipedia lambdas and return the context retrieved from both."""

    logging.info("Connecting to Wikipedia")
    wiki_context = send_claims_to_wiki_lambda(unrated_claims, WIKI_URL)
    logging.info(
        "Successfully retrieved context from Wikipedia: "
        f"example snippet: {str(wiki_context[0])}..."
    )

    logging.info("Connecting to RAG")
    rag_context = send_claims_to_rag_lambda(unrated_claims, RAG_URL)
    logging.info("Successfully retrieved context from RAG: example snippet: " +
                 str(rag_context[0][0]) + "...")

    return wiki_context, rag_context


def get_claims_and_ratings_from_input(user_input: str, input_format: str, source_type: str) -> tuple[str, list[dict]] | None:
    """
    Main process function for RAG interface.

    Take user input and return claims and their ratings.
    pipeline will be different depending on the input format

    """

    if user_input.strip() != "":

        summary, unrated_claims = get_unrated_claims_from_input(
            user_input, input_format)

        wiki_context, rag_context = get_context_from_lambdas(unrated_claims)

        rated_claims = rate_claims_via_llm(
            unrated_claims, wiki_context, rag_context, LLM_URL)

        # rated_claims = convert_llm_response_to_dict(rated_claims_raw)

        sup, mis, con, uns = calculate_metrics(rated_claims)

        db.archive_user_input(
            input_text=user_input,
            input_summary=summary[:250],
            source_type_name=source_type,
            supported=sup,
            contradicted=con,
            misleading=mis,
            unsure=uns,
            claims=rated_claims
        )
        return summary, rated_claims, (sup, mis, con, uns)

    return None


def verify_button(user_input: str, input_format: str, source_type: str) -> tuple[str, list[dict]] | None:
    button_clicked = st.button('Syft!')

    if button_clicked and user_input.strip() == "":
        st.warning("Please enter an article, URL, or claim to verify.")
        return None

    if button_clicked and source_type == DEFAULT_SOURCE_OPTION:
        st.warning("Please select a source type to continue.")
        return None

    if button_clicked:
        if user_input.strip() == "":
            st.warning("Please enter an article, URL, or claim to verify.")
            return None

        if source_type == 'Choose an option...':
            st.warning("Please select a source type to continue.")
            return None

        placeholder = st.empty()
        with placeholder.container():
            jumping_loader()
            log_text = st.empty()
            log_text.write("Syfting through our sources...")

        result = get_claims_and_ratings_from_input(
            user_input,
            input_format,
            source_type
        )

        placeholder.empty()

        if result:
            summary, claims_and_ratings, metrics = result
            return summary, claims_and_ratings, metrics

    return None


def render_trust_metrics(
    supported: float,
    misleading: float,
    contradicted: float,
    unsure: float
) -> None:
    """Display bar metrics about the user input. These include:
    -Supported
    -Misleading
    -Contradicted
    -Unsure"""
    fields_col, values_col = st.columns([1, 3])

    with fields_col:
        st.markdown(
            """
            <div style="line-height: 25px; font-weight: bold; text-align: left;">
                Supported:<br>
                Misleading:<br>
                Contradicted:<br>
                Unsure:
            </div>
            """,
            unsafe_allow_html=True
        )

    with values_col:
        render_metric_bars([supported,
                            misleading,
                            contradicted,
                            unsure])


def calculate_metrics(claims_and_rating: list[dict]) -> tuple[float, float, float, float]:
    """Create metrics representing the proportion of each rating (0.0 to 1.0)."""

    rating_totals = {
        'SUPPORTED': 0,
        'MISLEADING': 0,
        'CONTRADICTED': 0,
        'UNSURE': 0
    }

    total_claims = len(claims_and_rating)

    if total_claims == 0:
        return (0.0, 0.0, 0.0, 0.0)

    for response in claims_and_rating:
        rating = response.get('rating', 'UNSURE')
        if rating in rating_totals:
            rating_totals[rating] += 1

    # Convert to proportions (0 to 1)
    return (
        rating_totals['SUPPORTED'] / total_claims,
        rating_totals['MISLEADING'] / total_claims,
        rating_totals['CONTRADICTED'] / total_claims,
        rating_totals['UNSURE'] / total_claims
    )


def render_input_screen(screen_placeholder) -> tuple[str, list[dict]] | None:
    """Render the initial input screen for the user to enter an article, URL or claim."""

    with screen_placeholder.container(border=True):

        user_input, input_format, source_type = render_and_parse_input_boxes()

        try:
            result = verify_button(
                user_input, input_format, source_type)
            return result
        except RuntimeError as e:
            st.error(f"An error occurred during verification: {e}")
            return None
        except ValueError as e:
            st.error(f"An error occurred while processing the claims: {e}")
            return None


def render_results_screen(
    summary: str,
    claims_and_ratings: list[dict],
    metrics: tuple[float, float, float, float],
    screen_placeholder
) -> None:
    """Render the results screen to display claims and their ratings."""

    screen_placeholder.empty()

    if not claims_and_ratings:
        st.warning(
            "No claims were extracted from the input. Please try again with a different article, URL or claim.")
        return

    with st.container(border=True):
        st.subheader("Input Summary")
        st.info(summary)

        render_trust_metrics(*metrics)

    with st.container(border=True, height=300):
        render_claims(claims_and_ratings)


def render_claim_clusters(claims_and_evidence: list[dict]) -> None:
    """Render the claim clusters to display claims grouped by similarity."""

    st.subheader("Common Misinformation Themes")

    if not claims_and_evidence:
        return

    claims_and_evidence = sorted(
        claims_and_evidence, key=lambda x: len(x['claims']), reverse=True)[:3]

    cols = st.columns(len(claims_and_evidence))
    for cluster, col in zip(claims_and_evidence, cols):
        with col:
            with st.expander(cluster['cluster_name']):
                st.write(f"Description: {cluster['description']}")


def main():
    apply_syft_pro_theme()
    col_logo, _ = st.columns([1, 10])
    with col_logo:
        st.image("logo.png", width=70)

    # --- 2. DETAIL VIEW OVERRIDE ---
    if st.session_state.page == "Input Detail":
        if st.session_state.selected_input_id:
            history.render_history_detail_screen(
                st.session_state.selected_input_id, st.container())
        return

    # --- 3. MAIN NAVIGATION TABS ---
    tab_verify, tab_history, tab_about = st.tabs(
        ["VERIFIER", "HISTORY", "ABOUT US"])

    with tab_verify:
        if "results" not in st.session_state:
            st.session_state.page = "Input"  # Mark as landing page

            # --- THE LARGE CENTER LOGO (Input Screen Only) ---
            _, center_logo, _ = st.columns([1, 1.2, 1])
            with center_logo:
                st.image("logo.png", use_container_width=True)

            st.markdown(
                """
                <div style="display: flex; justify-content: center; width: 100%; margin-top: -65px;">
                    <div style="width: 420px; display: flex; justify-content: flex-end;">
                        <p style="color: #666; font-size: 1.4rem; margin-right: -30px;">
                            Beyond The Headlines
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<div style='margin-bottom: 60px; margin-top: -25px;'></div>",
                        unsafe_allow_html=True)

            # --- CLAIMS ---

            # Placeholder for claim clusters, replace with actual clustering logic
            # Call the cluster function to get claim clusters
            clusters = get_claims_clustered_with_evidence()
            render_claim_clusters(clusters)

            # --- INPUT FORM ---
            user_input, input_format, source_type = render_and_parse_input_boxes()
            verification_result = verify_button(
                user_input, input_format, source_type)

            if verification_result:
                st.session_state.results = verification_result
                st.session_state.page = "Results"  # Switch state to trigger small logo
                st.rerun()
        else:
            # --- RESULTS SCREEN ---
            summary, claims, metrics = st.session_state.results
            render_results_screen(summary, claims, metrics, st.container())

            if st.button("Verify another claim", key="verify_another"):
                if "results" in st.session_state:
                    del st.session_state.results
                st.session_state.page = "Input"
                st.rerun()

    with tab_history:
        st.session_state.page = "History"
        history.render_history_list_screen(st.container())

    with tab_about:
        st.session_state.page = "About"
        render_about_us()


if __name__ == "__main__":
    main()
