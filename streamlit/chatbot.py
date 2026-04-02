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
import requests
from loading_animation import jumping_loader
from about_us import render_about_us
# from streamlit_functions import (
#                                  setup_logging)

import db_logic as db
import history_dashboard as history
import source_rankings as sr
import streamlit as st


load_dotenv()


# WIKI_URL = os.getenv("WIKI_URL")
# RAG_URL = os.getenv("RAG_URL")
# SCRAPE_URL = os.getenv("SCRAPE_URL")
# LLM_URL = os.getenv("LLM_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

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


def post_to_lambda(lambda_url: str, payload: dict) -> dict | list:
    """Sends a POST request to a lambda URL
    and returns the response as a dict."""

    logging.info(
        f"Sending POST request to lambda with payload: {payload}")

    if "claims" in payload:
        payload["queries"] = payload["claims"]  # Renaming for RAG lambda

    logging.info(f"Final payload sent to lambda: {payload}")

    response = requests.post(
        lambda_url,
        json=payload
    )

    if response.status_code != 200:
        logging.error(
            f"Lambda request failed with status code {response.status_code}: {response.text}")
        raise RuntimeError(f"{response.text}")

    logging.info(f"Received response from lambda: ")

    return response.json()["rated_claims"], response.json()["summary"]

# setup_logging()


st.set_page_config(page_title="Syft", page_icon='logo_icon.png', layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "Input"

if "selected_input_id" not in st.session_state:
    st.session_state.selected_input_id = None


def apply_syft_pro_theme():
    st.markdown('<style>' + open('style.css').read() +
                '</style>', unsafe_allow_html=True)



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


def get_claims_and_ratings_from_input(user_input: str, input_format: str, source_type: str) -> tuple[str, list[dict]] | None:
    """
    Main process function for RAG interface.

    Take user input and return claims and their ratings.
    pipeline will be different depending on the input format

    """

    if user_input.strip() != "":

        payload = {"input": user_input,
                   "input_type": input_format, "source_type": source_type}

        rated_claims, summary = post_to_lambda(BACKEND_URL, payload)

        # summary, unrated_claims = get_unrated_claims_from_input(
        #     user_input, input_format)

        # wiki_context, rag_context = get_context_from_lambdas(unrated_claims)

        # rated_claims = rate_claims_via_llm(
        #     unrated_claims, wiki_context, rag_context, LLM_URL)

        # # rated_claims = convert_llm_response_to_dict(rated_claims_raw)

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

    with st.container(border=False):
        st.subheader("Input Summary")
        st.info(summary)

        render_trust_metrics(*metrics)

    with st.container(border=False, height=300):
        render_claims(claims_and_ratings)


def render_claim_clusters(claims_and_evidence: list[dict]) -> None:
    """Render the claim clusters to display claims grouped by similarity."""

    st.subheader("Common Misinformation Themes")

    if not claims_and_evidence:
        return

    cols = st.columns(len(claims_and_evidence))
    for cluster, col in zip(claims_and_evidence, cols):
        with col:
            with st.expander(cluster['cluster_name']):
                st.write(f"Description: {cluster['cluster_description']}")


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
    tab_verify, tab_history, tab_source_rankings, tab_about = st.tabs(
        ["VERIFIER", "HISTORY", "SOURCE RANKINGS", "ABOUT US"])

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

            # --- INPUT FORM ---
            user_input, input_format, source_type = render_and_parse_input_boxes()
            verification_result = verify_button(
                user_input, input_format, source_type)

            if verification_result:
                st.session_state.results = verification_result
                st.session_state.page = "Results"  # Switch state to trigger small logo
                st.rerun()

            # CLUSTERS

            clusters = db.get_clusters()[:4]
            if clusters:
                render_claim_clusters(clusters)
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

    with tab_source_rankings:
        st.session_state.page = "Source Rankings"
        sr.main()

    with tab_about:
        st.session_state.page = "About"
        render_about_us()


if __name__ == "__main__":
    main()
