"""
This script will run a streamlit 'front end' for the RAG chatbot.

When a user inputs an article, url or claim. This script will extract claims from the input
(scraping a page first if it's a url). 

These claims are then sent to multiple lambda functions via lambda urls.
"""

import streamlit as st
import requests
from collections.abc import Callable

# TODO: import function that retrieves claims from a text body.

# TODO: import function that retrieves article body from a url.

st.set_page_config(layout="wide")

# Set the title of the app
st.title('Disinformation Verifier Chatbot')

# Initialize chat history in session state if it doesn't exist
# session_state persists data across Streamlit reruns
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []


def display_claim_and_rating(claim: dict, box_design) -> None:
    """Display a claim and its rating"""

    col_1, col_2 = st.columns([1, 3])  # Adjust column widths as needed

    with col_1:
        
        box_design(f"**Claim:** {claim['claim']}")

    with col_2:
        st.markdown(f"**Rating:** {claim['rating']}")
        st.markdown(f"**Evidence:** {claim['evidence']}")


def set_up_initial_inputs() -> tuple[str, str, str, str]:
    "Set up input fields for user to enter an article, url or claim."

    col1, col2 = st.columns([5, 3.5])

    with col1:
        user_input = st.text_area(
            label='Input an article, URL, or claim to verify:',
            placeholder='"https://www.bbc.co.uk/news/science-environment-56837908"\n\n"The Earth is flat."',
            height=150,
            key='user_input'
        )

    with col2:

        sub_col1, sub_col2 = st.columns(2)

        with sub_col1:
            input_format = st.selectbox(
            label='Input format:',
            options=['URL', 'Claim', 'Article Text'],
            key='input_format'
            )
        with sub_col2:
            source_type = st.selectbox(
                label='Source type:',
                options=['News Article',
                        'Social Media', 'Other'],
                key='source_type'
            )
        source = set_up_follow_up_inputs(source_type)

        

    return user_input, input_format, source_type, source


def set_up_follow_up_inputs(source_type):

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


def display_claims(claims: list[dict]) -> None:
    """Display claims and their ratings in the Streamlit app."""

    box_designs = {
        'Supported': lambda x: st.success(x),
        'Misleading': lambda x: st.warning(x),
        'Contradicted': lambda x: st.error(x),
        'Unsure': lambda x: st.info(x)
    }

    for claim in claims:
        with st.container(border=True):
            box_design = box_designs.get(claim['rating'])
            display_claim_and_rating(claim, box_design)

def get_user_input_claims(user_input:str) -> list[dict]:
    """Take user input and return claims and their ratings."""

    if user_input.strip() != "":

        placeholder.empty()

        # TODO: Return list of claims using lambdas

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

        return claims

def click_button() -> list[dict]:
    """Handle button click event and return claims."""

    button_clicked = st.button('Verify!')

    if button_clicked and st.session_state.user_input.strip() == "":
        st.warning("Please enter an article, URL, or claim to verify.")
        return None
            
    elif button_clicked:
        return get_user_input_claims(st.session_state.user_input)

    else:
        return None
    
placeholder = st.empty()

with placeholder.container(border=True):

    user_input, format, source_type, source = set_up_initial_inputs()

    claims = click_button()

if claims:
    
    placeholder.empty()
    display_claims(claims)

    if st.button('Verify another claim?'):
        st.rerun()



