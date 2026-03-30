"""functions to render about us page"""

import streamlit as st


def render_about_us() -> None:
    """
    renders the about us page with information about the project,
    our sources, and how to interpret the ratings.
    """

    st.header("About Us")
    st.markdown("""
    Syft is an AI-powered fact-checking engine designed to provide transparency 
    and context to digital information. Our goal isn't to tell you what to think, 
    but to show you what the data says.
    """)

    render_overview_section()
    render_sources_section()
    render_ratings_key_section()


def render_overview_section() -> None:
    """
    renders the overview section of the about us page,
    explaining how the system works.
    """

    st.subheader("How It Works")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 1. Extraction")
            st.write(
                "We scrape URLs or parse raw text to identify verifiable claims using Natural Language Processing.")
        with col2:
            st.markdown("### 2. Retrieval (RAG)")
            st.write(
                "Claims are cross-referenced against a vector database of real-time RSS feeds and Wikipedia's knowledge base.")
        with col3:
            st.markdown("### 3. Verification")
            st.write(
                "An LLM compares the retrieved evidence against the claims to generate a rating and a detailed explanation.")


def render_sources_section() -> None:
    """
    renders the sources section of the about us page, 
    listing our trusted sources of truth
    """

    st.subheader("Our Sources of Truth")
    sources = [
        {"name": "Wikipedia", "url": "https://www.wikipedia.org",
            "desc": "The world's largest collaborative encyclopedia, useful for established facts and historical context."},
        {"name": "BBC News", "url": "https://www.bbc.com/news",
            "desc": "A globally recognized public service broadcaster known for rigorous editorial standards and neutrality."},
        {"name": "Reuters", "url": "https://www.reuters.com",
            "desc": "An international news agency focused on rapid, evidence-based reporting with minimal bias."},
        {"name": "Full Fact", "url": "https://fullfact.org",
            "desc": "A team of independent fact-checkers and technologists who find, expose and counter misinformation."}
    ]

    for source in sources:
        with st.expander(f"**{source['name']}**"):
            st.write(source['desc'])
            st.link_button(f"Visit {source['name']}", source['url'])


def render_ratings_key_section() -> None:
    """
    renders the ratings key section of the about us page,
    explaining the meaning of each rating.
    """

    st.subheader("Understanding the Ratings")

    cols = st.columns(2)

    with cols[0]:
        st.success("**SUPPORTED**")
        st.caption(
            "The claim is directly confirmed by information found in our trusted sources.")

        st.warning("**MISLEADING**")
        st.caption(
            "The claim contains a grain of truth but is presented out of context or ignores key facts.")

    with cols[1]:
        st.error("**CONTRADICTED**")
        st.caption(
            "The claim is explicitly refuted by reliable evidence from our sources.")

        st.info("**UNSURE**")
        st.caption(
            "Insufficient evidence was found to prove or disprove the claim with confidence.")

    st.divider()
    st.info("Note: AI can make mistakes. Always review the 'Evidence' provided alongside each rating.")


if __name__ == "__main__":

    render_about_us()
