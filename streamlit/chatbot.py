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
from streamlit_functions import (convert_llm_response_to_dict, send_url_to_web_scraping_lambda,
                                 get_claims_from_text,
                                 send_claims_to_rag_lambda,
                                 send_claims_to_wiki_lambda, rate_claims_via_llm,
                                 setup_logging,
                                 Claim)


import streamlit as st


load_dotenv()


WIKI_URL = os.getenv("WIKI_URL")
RAG_URL = os.getenv("RAG_URL")
SCRAPE_URL = os.getenv("SCRAPE_URL")

setup_logging()

st.set_page_config(layout="wide")

# Set the title of the app
st.title('Disinformation Verifier Chatbot')


def display_claim_and_rating(claim: dict, box_design) -> None:
    """Display a claim and its rating"""

    claim_str, ratings = st.columns([1, 3])  # Adjust column widths as needed

    with claim_str:

        box_design(f"**Claim:** {claim['claim']}")

    with ratings:
        st.markdown(f"**Rating:** {claim['rating']}")
        st.markdown(f"**Evidence:** {claim['explanation']}")


def render_and_parse_input_boxes() -> tuple[str, str, str, str]:
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
                options=['URL', 'Claim', 'Article Text'],
                key='input_format'
            )
        with source_input:
            source_type = st.selectbox(
                label='Source type:',
                options=['News Article',
                         'Social Media', 'Other'],
                key='source_type'
            )

        source = render_and_parse_optional_input_box(source_type)

    return user_input, input_format, source_type, source


def render_and_parse_optional_input_box(source_type) -> str:
    """Set up follow up input fields based on the source type selected by the user."""

    if source_type == 'News Article':
        source = st.text_input(
            label='Article Source (Optional):',
            placeholder='e.g. BBC, CNN, etc.',
            key='news_source'
        )

    if source_type == 'Social Media':
        source = st.text_input(
            label='Platform (Optional):',
            placeholder='e.g. TikTok, Facebook, etc.',
            key='social_platform'
        )

    if source_type == 'Other':
        source = st.text_input(
            label='Source Description (Optional):',
            placeholder='e.g. YouTube video, podcast, etc.',
            key='other_source'
        )

    return source


def add_grey_background(y_positions: list[str]) -> go.Figure:
    """Creates a grey background for each metric bar
    representing the full range."""

    fig = go.Figure(go.Bar(
        x=[1] * 4,
        y=y_positions,
        orientation='h',
        marker=dict(
            color='rgb(242,242,242)',  # Transparent fill
            line={"color": 'white', "width": 1}  # invisible border
        ),
        width=0.5,
        hoverinfo='none'  # Keep the background quiet
    ))

    return fig


def add_metric_bars(fig: go.Figure, values: list[float], y_positions: list[str]) -> go.Figure:
    """Adds colored bars corresponding to the value (0-1) on top of the grey background."""

    colorscale = [[0, "#FF4B4B"], [0.5, "#FFA421"], [1, "#28A745"]]

    fig.add_trace(go.Bar(
        x=values,
        y=y_positions,
        orientation='h',
        marker=dict(
            color=values,
            colorscale=colorscale,
            cmin=0,
            cmax=1,
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

    y_positions = ["A", "B", "C", "D"]

    fig = add_grey_background(y_positions)

    fig = add_metric_bars(fig, values, y_positions)

    fig = update_figure_layout(fig)

    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})


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


def get_unrated_claims_from_input(user_input: str, input_format: str) -> list[Claim]:
    """Extract claims from the user input based on the input format."""

    if input_format == 'Claim':
            unrated_claims = [Claim(claim_text=user_input)]

    if input_format == 'URL':
        article_body = send_url_to_web_scraping_lambda(
            user_input, SCRAPE_URL)
        unrated_claims = get_claims_from_text(article_body)

    if input_format == 'Article Text':

        unrated_claims = get_claims_from_text(user_input)

    return unrated_claims


def get_context_from_lambdas(unrated_claims: list[Claim]) -> tuple[list[dict], list[dict]]:
    """Send claims to RAG and Wikipedia lambdas and return the context retrieved from both."""

    logging.info("Connecting to RAG")
    
    try:
        rag_context = send_claims_to_rag_lambda(unrated_claims, RAG_URL)
        logging.info("Successfully retrieved context from RAG: example snippet: " + str(rag_context[0][0]) + "...")

    except RuntimeError as e:
        st.error(f"An error occurred in RAG servers: {e}")
        return None

    logging.info("Connecting to Wikipedia")
    try:
        wiki_context = send_claims_to_wiki_lambda(unrated_claims, WIKI_URL)
        logging.info("Successfully retrieved context from Wikipedia: example snippet: " + str(wiki_context[0]) + "...")
    except RuntimeError as e:
        st.error(f"An error occurred in Wikipedia servers: {e}")
        return None
    
    return wiki_context, rag_context
    

def get_claims_and_ratings_from_input(user_input: str, input_format: str) -> list[dict] | None:
    """
    Main process function for RAG interface.

    Take user input and return claims and their ratings.
    pipeline will be different depending on the input format

    """

    if user_input.strip() != "":

        unrated_claims = get_unrated_claims_from_input(user_input, input_format)

        wiki_context, rag_context = get_context_from_lambdas(unrated_claims)

        rated_claims = rate_claims_via_llm(
            unrated_claims, wiki_context, rag_context)

        rated_claims = convert_llm_response_to_dict(rated_claims)

        return rated_claims


def verify_button(user_input: str, input_format: str) -> list[dict] | None:
    """Handle button click event and return claims with ratings."""

    button_clicked = st.button('Verify!')

    if button_clicked and user_input.strip() == "":
        st.warning("Please enter an article, URL, or claim to verify.")
        return None

    if button_clicked:
        claims_and_ratings = get_claims_and_ratings_from_input(
            user_input, input_format)
        
        return claims_and_ratings

    return None


def render_trust_metrics(claims_and_rating: list[dict]) -> None:
    """Display bar metrics about the user input. These include:
    -Trustworthiness
    -Correctness
    -Overall
    -Confidence"""

    trust, correctness, overall, confidence = calculate_metrics(
        claims_and_rating)

    fields_col, values_col = st.columns([1, 3])

    with fields_col:
        st.markdown(
            """
            <div style="line-height: 25px; font-weight: bold; text-align: left;">
                Trustworthiness:<br>
                Correctness:<br>
                Overall:<br>
                Confidence:
            </div>
            """,
            unsafe_allow_html=True
        )

    with values_col:
        render_metric_bars([trust,
                            correctness,
                            overall,
                            confidence])


def calculate_metrics(claims_and_rating: list[dict]) -> tuple[float, float, float, float]:
    """Create metrics about the user input based on the claims and their ratings."""

    # TODO: Create function to calculate metrics based on claims and their ratings.

    return 0.1, 0.5, 0.75, 0.9  # Placeholder values for testing purposes


def render_input_screen(screen_placeholder) -> list[dict]:
    """Render the initial input screen for the user to enter an article, URL or claim."""

    with screen_placeholder.container(border=True):

        user_input, input_format, _, _ = render_and_parse_input_boxes()

        try:
            claims_and_ratings = verify_button(user_input, input_format)
        except RuntimeError as e:
            st.error(f"An error occurred during verification: {e}")
            return None

        # TODO: Add a function to store claims, ratings, source_type and source in a database for future analysis.

    return claims_and_ratings


def render_results_screen(claims_and_ratings: list[dict], screen_placeholder) -> None:
    """Render the results screen to display claims and their ratings."""

    screen_placeholder.empty()

    if claims_and_ratings == []:
        st.warning(
            "No claims were extracted from the input. Please try again with a different article, URL or claim.")
        return

    with st.container(border=True):
        render_trust_metrics(claims_and_ratings)

    with st.container(border=True, height=300):
        render_claims(claims_and_ratings)


if __name__ == "__main__":

    placeholder = st.empty()

    claims_and_ratings = render_input_screen(placeholder)

    if claims_and_ratings is not None:
        render_results_screen(claims_and_ratings, placeholder)

        if st.button('Verify another claim?'):
            st.rerun()
