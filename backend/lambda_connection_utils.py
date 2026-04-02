"""
This script contains all functions related to interacting with the lambda functions.
"""

import os
import logging
import requests


from classes import Claim

INPUT_FORMAT_URL = 'URL'
INPUT_FORMAT_CLAIM = 'Claim'
INPUT_FORMAT_ARTICLE = 'Article Text'
DEFAULT_SOURCE_OPTION = 'Choose an option...'

WIKI_URL = os.getenv("WIKI_URL")
RAG_URL = os.getenv("RAG_URL")
SCRAPE_URL = os.getenv("SCRAPE_URL")

CLAIM_EXTRACTION_DEVELOPER_ROLE_CONTENT = """# Role
    Professional Fact-Checker (Executive Summary Mode)

    # Task
    1. Write a 1-3 sentence executive summary of the input text, capturing the overall gist and main points.
    2. Extract only the MAIN objective, verifiable claims. Ignore minor details,
    repetitive updates, subjective information or trivial data points.

    # Constraints
    1. Essential Claims Only: Extract only the most significant units of information.
    2. Objective & Atomic: No opinions or subjective statements. Each statement must stand alone.
    3. Contextual Independence: Replace pronouns with nouns (e.g., "The President" instead of "He").
    4. No Overlap: Ensure claims are mutually exclusive.
    5. If a claim is subjective, emotional, or an opinion (e.g., "I love...", "I don't like..."), DO NOT include it.

    """

CLAIM_EXTRACTION_DEVELOPER_ROLE = {
    "role": "developer",
    "content": CLAIM_EXTRACTION_DEVELOPER_ROLE_CONTENT
}

CLAIM_RATING_DEVELOPER_ROLE_CONTENT = """# Role
Professional Fact-Verification Engine (Simplified Mode)

# Task
Evaluate "Claims" against the provided "Factual Context" (Wikipedia or RAG chunks). 

# Rating Definitions
1. SUPPORTED: Context explicitly confirms the claim.
2. CONTRADICTED: Context explicitly refutes the claim.
3. MISLEADING: Claim is partially accurate but uses imprecise language, lacks nuance, or is not 100% supported by the text provided.
4. UNSURE: Context lacks sufficient information.

# Constraints
1. Objectivity: Use ONLY provided context. No external knowledge.
2. Tone: Be concise. One to two sentences max for the explanation.
3. Formatting: Return ONLY the results. No intro/outro text. DO INCLUDE " ' " characters in the response
to allow for clear parsing of the explanation and sources.
4. Return The source URL(s) for each claim if available.
"""

CLAIM_RATING_DEVELOPER_ROLE = {
    "role": "developer",
    "content": CLAIM_RATING_DEVELOPER_ROLE_CONTENT
}


def get_summary_and_claims_from_text(text_input: str, llm_url: str) -> tuple[str, list[Claim]]:
    """This function uses an LLM to extract a list of claims made
    in a body of text.

    'text_input' is either directly from a user input or a body of text
    from the web-scraping lambda.
    """

    payload = {
        "dv_role": CLAIM_EXTRACTION_DEVELOPER_ROLE,
        "prompt": text_input,
        "structured_output": "unrated_claims",
        "success_message": "Successfully extracted claims from text input."
    }

    logging.info(f"Sending payload to LLM for claim extraction. {payload}")
    response = post_to_lambda(llm_url, payload)
    summary = response["summary"]
    claims = [Claim(claim_text=claim) for claim in response["claims"]]

    logging.info(f"LLM returned summary: {summary}")
    logging.info(
        f"LLM returned claims: {[claim.claim_text for claim in claims]}")

    return summary, claims


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

    return response.json()


def get_context_from_lambdas(unrated_claims: list[Claim]) -> tuple[list[dict], list[dict]]:
    """Send claims to RAG and Wikipedia lambdas and return the context retrieved from both."""

    logging.info("Connecting to Wikipedia")
    wiki_context = send_claims_to_wiki_lambda(unrated_claims, WIKI_URL)
    logging.info(
        "Successfully retrieved context from Wikipedia: "
        f"{wiki_context}..."
    )

    logging.info("Connecting to RAG")
    rag_context = send_claims_to_rag_lambda(unrated_claims, RAG_URL)
    logging.info("Successfully retrieved context from RAG: example snippet: " +
                 str(rag_context[0][0]) + "...")

    return wiki_context, rag_context


def get_unrated_claims_from_input(user_input: str, input_format: str, llm_url: str) -> tuple[str, list[Claim]]:
    """Extract claims from the user input based on the input format."""

    if input_format == INPUT_FORMAT_CLAIM:
        summary = f"Verification of the following claim: {user_input.title()}"
        unrated_claims = [Claim(claim_text=user_input)]
        return summary, unrated_claims

    if input_format == INPUT_FORMAT_URL:
        article_body = send_url_to_web_scraping_lambda(
            user_input, SCRAPE_URL)
        return get_summary_and_claims_from_text(article_body, llm_url)

    if input_format == INPUT_FORMAT_ARTICLE:

        return get_summary_and_claims_from_text(user_input, llm_url)

    # Default return for unsupported formats, should not reach here due to input validation
    return "No summary generated", []


def send_url_to_web_scraping_lambda(user_url: str, lambda_url: str) -> str:
    """Sends a URL to the web-scraping lambda
    and returns the extracted text body."""

    payload = {"url": user_url}
    response = post_to_lambda(lambda_url, payload)

    return response["text"]


def send_claims_to_rag_lambda(
    claims: list[Claim], lambda_url: str
) -> list[dict]:
    """Sends claims to the RAG lambda and
    returns relevant facts with metadata."""

    payload = {"claims": _extract_claim_strings(claims)}
    return post_to_lambda(lambda_url, payload)


def send_claims_to_wiki_lambda(
    claims: list[Claim], lambda_url: str
) -> list[dict]:
    """Sends claims to the Wikipedia lambda and
    returns Wikipedia evidence for each claim."""

    payload = {"claims": _extract_claim_strings(claims)}
    response = post_to_lambda(lambda_url, payload)

    return response["wiki_context"]


def _extract_claim_strings(
    claims: list[Claim]
) -> list[str]:
    """Converts a list of Claim objects to strings."""
    return [claim.claim_text for claim in claims]


def validate_inputs_for_prompt(claims: list[Claim], wiki_context: list[dict], rag_context: list[list]) -> None:
    """Validates the inputs for the LLM prompt. Raises ValueError if any of the inputs are invalid."""

    if not isinstance(claims, list) or not all(isinstance(c, Claim) for c in claims):
        raise ValueError("Claims must be a list of Claim objects.")

    if wiki_context is not None and (not isinstance(wiki_context, list) or not all(isinstance(w, dict) for w in wiki_context)):
        raise ValueError(
            "ERROR: Wikipedia context must be a list of dictionaries.")

    if rag_context is not None and (not isinstance(rag_context, list) or not all(isinstance(r, list) for r in rag_context)):
        raise ValueError("ERROR: RAG context must be a list of lists.")

    if claims == []:
        raise ValueError("Claims list is empty.")
    if wiki_context == []:
        raise ValueError("Wikipedia context list is empty.")
    if rag_context == []:
        raise ValueError("RAG context list is empty.")


def create_llm_prompt(
    claims: list[Claim],
    wiki_context: list[dict],
    rag_context: list[list[dict]]
) -> str:
    """Creates a prompt for the LLM based on
    claims, Wikipedia context and RAG context.

    RAG dict keys: title, content,
    source_url, created_at"""

    validate_inputs_for_prompt(claims, wiki_context, rag_context)

    if wiki_context is None:
        wiki_context = ["No Wikipedia context was retrieved for these claims."]
    if rag_context is None:
        rag_context = [["No RAG facts were retrieved for these claims."]]

    claims_strings = "\n".join(
        [f"[{claim.claim_text}]" for claim in claims]
    )

    wiki_strings = "\n".join(
        [
            f"[{r['relevant_sections']}] (Source: {r['url']})"
            for r in wiki_context
        ]
    )

    rag_strings = ""
    for rag_entries in rag_context:
        rag_strings += "\n".join(

            [
                f"[{r['content']}] (Source: {r['source_url']}, Date: {r['published_at']})"
                for r in rag_entries
            ]
        )

    prompt = f"""Evaluate the following {len(claims)} individual claims separately based on
                the provided Wikipedia evidence and RAG facts. 
                For each claim, assign a rating of 
                SUPPORTED, CONTRADICTED, MISLEADING, or UNSURE
                based strictly on the provided evidence. 
                Provide a brief explanation for each rating and, as a final entry, 
                include all the sources of the evidence used, date and title if available.

                Claims:
                {claims_strings}
                
                Wikipedia Evidence:
                {wiki_strings}
                
                RAG Facts:
                {rag_strings}

                ### Instructions:
1. Assign one rating: SUPPORTED, CONTRADICTED, MISLEADING, or UNSURE.
2. A claim is MISLEADING if it is directionally correct but lacks the specific detail, nuance, or precision found in the sources.
3. Provide a brief 1-2 sentence explanation.
4. Identify if the information came from "Wikipedia", a URL, or multiple.
5. DO NOT include any sources if the claim is rated UNSURE.
"""

    return prompt


def rate_claims_via_llm(claims: list[Claim], wiki_context: list[dict], rag_context: list[dict], llm_url: str) -> list[dict]:
    """
    This functions sends the claims to openai along with context from
    Wikipedia and RAG. 
    Openai will return categorical ratings for each claim along with a brief explanation for the rating.
    This will include the source that a claim was proved/disproved via.

    Openai will also summarize the overall user input in a short description.
    """

    prompt = create_llm_prompt(claims, wiki_context, rag_context)

    payload = {
        "dv_role": CLAIM_EXTRACTION_DEVELOPER_ROLE,
        "prompt": prompt,
        "structured_output": "rated_claims",
        "success_message": "Successfully rated claims based on Wikipedia and RAG context."
    }

    response = post_to_lambda(llm_url, payload)

    return response
