"""
This script will run a streamlit 'front end' for the RAG chatbot.

When a user inputs an article, url or claim. This script will extract claims from the input
(scraping a page first if it's a url). 

These claims are then sent to multiple lambda functions via lambda urls.
"""

import streamlit as st
import requests
import plotly.graph_objects as go


# TODO: import function that retrieves claims from a text body.

# TODO: import function that retrieves article body from a url.

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
        st.markdown(f"**Evidence:** {claim['evidence']}")


def set_up_initial_inputs() -> tuple[str, str, str, str]:
    "Set up input fields for user to enter an article, url or claim."

    main_input, secondary_input = st.columns([5, 3.5])

    with main_input:
        user_input = st.text_area(
            label='Input an article, URL, or claim to verify:',
            placeholder='"https://www.bbc.co.uk/news/science-environment-56837908"\n\n"The Earth is flat."',
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

        source = set_up_follow_up_inputs(source_type)

    return user_input, input_format, source_type, source


def set_up_follow_up_inputs(source_type):
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
    """Creates a grey background for each metric bar"""

    fig = go.Figure(go.Bar(
        x=[1] * 4,
        y=y_positions,
        orientation='h',
        marker=dict(
            color='rgb(242,242,242)',  # Transparent fill
            line=dict(color='white', width=1)  # The thin black border
        ),
        width=0.5,
        hoverinfo='none'  # Keep the background quiet
    ))

    return fig


def add_metric_bars(fig: go.Figure, values: list[float], y_positions: list[str]) -> None:
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
            line=dict(width=0)
        ),
        width=0.5
    ))

    return fig


def update_figure_layout(fig: go.Figure) -> None:
    """Updates the layout of the figure to ensure bars are overlaid and axes are hidden."""

    fig.update_layout(
        barmode='overlay',  # Crucial: prevents bars from stacking or dodging
        xaxis=dict(range=[0, 1], visible=False),
        yaxis=dict(visible=False),
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        bargap=0.1
    )

    return fig


def show_metric_bars(values: list[float]):
    """Displays horizontal bars with colors corresponding to the value (0-1)."""

    y_positions = ["A", "B", "C", "D"]

    fig = add_grey_background(y_positions)

    fig = add_metric_bars(fig, values, y_positions)

    fig = update_figure_layout(fig)

    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})


def display_claims(claims: list[dict]) -> None:
    """Display claims and their ratings in the Streamlit app."""

    box_designs = {  # Different colour boxes for different ratings.
        'Supported': lambda x: st.success(x),
        'Misleading': lambda x: st.warning(x),
        'Contradicted': lambda x: st.error(x),
        'Unsure': lambda x: st.info(x)
    }

    for claim in claims:
        box_design = box_designs.get(claim['rating'])
        with st.container(border=True):
            display_claim_and_rating(claim, box_design)


def get_user_input_claims(user_input: str, format: str) -> list[dict]:
    """
    Take user input and return claims and their ratings.
    pipeline will be different depending on the input format

    """

    if user_input.strip() != "":

        placeholder.empty()

        # TODO: Return list of claims using lambdas, will depend on 'format'.

        claims = [  # Placeholder claims for testing purposes
            {
                'claim': 'The Earth is flat.',
                'rating': 'Contradicted',
                'evidence': """Scientific consensus and overwhelming evidence (link)
                from various fields of study confirm that the Earth is an oblate spheroid."""
            },
            {
                'claim': 'The Earth is the center of the universe.',
                'rating': 'Contradicted',
                'evidence': """The heliocentric model, 
                supported by extensive astronomical observations,
                demonstrates that the Earth orbits the Sun, 
                which is just one of billions of stars in the Milky Way galaxy."""
            },
            {
                'claim': 'The Earth is approximately 4.5 billion years old.',
                'rating': 'Supported',
                'evidence': """Radiometric dating of rocks and meteorites, 
                as well as the study of Earth's geological layers, 
                consistently indicate that the Earth is around 4.5 billion years old."""
            }
        ]
        claims = [] # Placeholder to test the 'no claims extracted' warning message.

        return claims


def click_button(user_input: str, format: str) -> list[dict]:
    """Handle button click event and return claims with ratings."""

    button_clicked = st.button('Verify!')

    if button_clicked and user_input.strip() == "":
        st.warning("Please enter an article, URL, or claim to verify.")
        return None

    elif button_clicked:
        return get_user_input_claims(user_input, format)

    else:
        return None


def display_input_metrics(claims_and_rating: list[dict]) -> None:
    """Display bar metrics about the user input. These include:
    -Trustworthiness
    -Correctness
    -Overall
    -Confidence"""

    trust, correctness, overall, confidence = create_metrics(claims_and_rating)

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
        show_metric_bars([trust,
                          correctness,
                          overall,
                          confidence])


def create_metrics(claims_and_rating: list[dict]) -> tuple[float, float, float, float]:
    """Create metrics about the user input based on the claims and their ratings."""

    # TODO: Create function to calculate metrics based on claims and their ratings.

    return 0.1, 0.5, 0.75, 0.9  # Placeholder values for testing purposes


def render_input_screen(screen_placeholder) -> None:
    """Render the initial input screen for the user to enter an article, URL or claim."""

    with screen_placeholder.container(border=True):

        user_input, format, source_type, source = set_up_initial_inputs()

        claims_and_ratings = click_button(user_input, format)

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
        display_input_metrics(claims_and_ratings)

    with st.container(border=True, height=300):
        display_claims(claims_and_ratings)

    if st.button('Verify another claim?'):
        st.rerun()


if __name__ == "__main__":

    placeholder = st.empty()

    claims_and_ratings = render_input_screen(placeholder)

    if claims_and_ratings is not None:
        render_results_screen(claims_and_ratings, placeholder)
