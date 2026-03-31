"""
This script contain functions and classes that are used in the streamlit app
"""

import re
import logging
from os import environ
import requests
from openai import OpenAI
from dotenv import load_dotenv
import boto3
import json
from pydantic import BaseModel

load_dotenv()

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


class Claim:
    """
    This class represents a claim that has been extracted from the users input
    """

    def __init__(self, claim_text: str, category: str = None):
        self.claim_text = claim_text
        self.category = category


class RatedClaim(BaseModel):
    claim: str
    rating: str
    explanation: str
    sources: list[str]


class RatedClaimResponse(BaseModel):
    rated_claims: list[RatedClaim]


class UnratedClaimResponse(BaseModel):
    summary: str
    claims: list[str]


def setup_logging():
    """ Configures logging for the Lambda function. Logs will be sent to CloudWatch. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


_CACHED_SECRET = None
_OPENAI_CLIENT = None
sm_client = boto3.client('secretsmanager', region_name='eu-west-2')


def get_secrets() -> dict:
    """Fetches OpenAI API key from AWS Secrets Manager."""

    global _CACHED_SECRET
    if _CACHED_SECRET:
        return _CACHED_SECRET
    secret_name = environ.get("SECRET_ID")
    if not secret_name:
        logging.error("SECRET_ID environment variable not set.")
        raise EnvironmentError("SECRET_ID environment variable not set.")
    try:
        response = sm_client.get_secret_value(SecretId=secret_name)
        _CACHED_SECRET = json.loads(response['SecretString'])
        logging.info("Secrets successfully retrieved and cached.")
        return _CACHED_SECRET
    except Exception as e:
        logging.error(f"Error fetching secrets from AWS Secrets Manager: {e}")
        raise EnvironmentError(
            "Failed to retrieve secrets from AWS Secrets Manager.")


def get_openai_client() -> OpenAI:
    """ Abstracted function to intialise and cache the OpenAI client. """

    global _OPENAI_CLIENT
    if _OPENAI_CLIENT:
        return _OPENAI_CLIENT
    try:
        secrets = get_secrets()
        api_key = secrets.get('OPENAI_API_KEY')
        if not api_key:
            logging.error("OPENAI_API_KEY not found in secrets.")
            raise KeyError("OPENAI_API_KEY not found in secrets.")
        _OPENAI_CLIENT = OpenAI(api_key=api_key)
        logging.info("OpenAI client initialized and cached.")
        return _OPENAI_CLIENT
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {e}")
        raise RuntimeError("Failed to initialize OpenAI client.")


def get_summary_and_claims_from_text(text_input: str) -> list[Claim]:
    """This function uses an LLM to extract a list of claims made
    in a body of text.

    'text_input' is either directly from a user input or a body of text
    from the web-scraping lambda.
    """

    client = get_openai_client()

    raw_output = query_llm(text_input, client,
                           CLAIM_EXTRACTION_DEVELOPER_ROLE,
                           "Successfully extracted claims from text input.", UnratedClaimResponse)

    summary_part = raw_output.summary

    claims_list = [
        Claim(claim_text=claim) for claim in raw_output.claims
    ]

    return summary_part, claims_list


def query_llm(prompt: str, client: OpenAI, developer_role: dict,
              succces_log: str, response_format: object) -> UnratedClaimResponse | RatedClaimResponse:
    """
    Queries the LLM for high-level objective claims returned as a 
    newline-separated string for maximum token efficiency.
    """

    if prompt is None or prompt.strip() == "":
        raise ValueError("Prompt cannot be empty or None.")

    try:
        response = client.responses.parse(
            model="gpt-5-nano",
            input=[developer_role,
                   {
                       "role": "user",
                       "content": prompt
                   }
                   ],
            temperature=1,
            reasoning={"effort": "low"},
            text_format=response_format,
        )

        logging.info(succces_log)

        return response.output_parsed

    except Exception as e:
        logging.error(f"Error querying LLM: {e}")
        raise RuntimeError("Failed to query LLM. Check logs for details.")


def post_to_lambda(lambda_url: str, payload: dict) -> dict:
    """Sends a POST request to a lambda URL
    and returns the response as a dict."""

    logging.info(
        f"Sending POST request to lambda with payload: {payload}")

    if "claims" in payload:
        payload["queries"] = payload["claims"]  # Renaming for RAG lambda

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


def send_url_to_web_scraping_lambda(user_url: str, lambda_url: str) -> str:
    """Sends a URL to the web-scraping lambda
    and returns the extracted text body."""

    payload = {"url": user_url}
    response = post_to_lambda(lambda_url, payload)

    return response["text"]


def _extract_claim_strings(
    claims: list[Claim]
) -> list[str]:
    """Converts a list of Claim objects to strings."""
    return [claim.claim_text for claim in claims]


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


def rate_claims_via_llm(claims: list[Claim], wiki_context: list[dict], rag_context: list[dict]) -> RatedClaimResponse:
    """
    This functions sends the claims to openai along with context from
    Wikipedia and RAG. 
    Openai will return categorical ratings for each claim along with a brief explanation for the rating.
    This will include the source that a claim was proved/disproved via.

    Openai will also summarize the overall user input in a short description.
    """

    client = get_openai_client()

    prompt = create_llm_prompt(claims, wiki_context, rag_context)

    response = query_llm(prompt, client,
                         CLAIM_RATING_DEVELOPER_ROLE,
                         "Successfully rated claims based on Wikipedia and RAG context.", RatedClaimResponse)

    logging.info(f"""LLM returned response example: 
                {response.rated_claims[0].claim}
                {response.rated_claims[0].rating}
                {response.rated_claims[0].explanation}
                {response.rated_claims[0].sources}""")

    return response


def convert_llm_response_to_dict(llm_response: RatedClaimResponse) -> list[dict]:
    """Converts LLM rating output string to a
    list of structured claim dicts.

    Each dict has: claim, rating,
    explanation, sources.
    """

    claim_dicts = [
        {
            "claim": rated_claim.claim,
            "rating": rated_claim.rating.upper(),
            "evidence": rated_claim.explanation,
            "sources": rated_claim.sources
        }
        for rated_claim in llm_response.rated_claims if (rated_claim.claim and
                                                         rated_claim.rating and
                                                         rated_claim.explanation)
    ]

    logging.info(f"Claims and ratings obtained: {claim_dicts[:3]}")

    return claim_dicts


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

if __name__ == "__main__":
    # Example usage

    setup_logging()

    example_claims = [Claim(claim_text="The sky is a really light blue."),
                      Claim(claim_text="The grass is green.")]

    example_wiki_context = ["The sky appears blue due to the scattering"
                            "of sunlight by the atmosphere."]

    example_rag_context = [
        {"content": "The sky is often described as blue during the day.",
         "created_at": "2024-01-01",
         "source_url": "https://example.com/sky"}
    ]

    print(
        rate_claims_via_llm(
            example_claims, example_wiki_context, example_rag_context)
    )
