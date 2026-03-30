"""
This script contain functions and classes that are used in the streamlit app
"""

import re
import logging
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CLAIM_EXTRACTION_DEVELOPER_ROLE_CONTENT = """# Role
    Professional Fact-Checker (Executive Summary Mode

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

    # Output Format
    [SUMMARY]
    Return a concise executive summary of the overall input text in 1-3 sentences.
    [CLAIMS]
    Return ONLY the claims as a plain text list, with each claim on a NEW LINE starting with a pipe character (|). 
    Do not use JSON, markdown, or introductory text.

    # Example Output
    [SUMMARY]
    The article discusses Iran's nuclear program and the US response, as well as general information about fish and maritime traffic in the Strait of Hormuz.
    [CLAIMS]
    |President Trump issued a 48-hour deadline to Iran.
    |Fish all live in the sea.
    |Traffic through the Strait of Hormuz remains limited."""

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


# Output Format
Return each result on a NEW LINE starting with a pipe character in this exact format:
|'claim_made', 'rating', '[Explanation sentence]', 'Sources: [Specify "Wikipedia" and the URL(s) and the specific URL(s) provided in the RAG facts]' 
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


def setup_logging():
    """ Configures logging for the Lambda function. Logs will be sent to CloudWatch. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def connect_to_openai() -> OpenAI:
    """ Establishes a connection to the OpenAI API using the API key from environment variables. """

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        logging.info("Successfully connected to OpenAI API.")
        return client
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {e}")
        raise RuntimeError(
            "Failed to initialize OpenAI client. Check logs for details.")


def get_summary_and_claims_from_text(text_input: str) -> list[Claim]:
    """This function uses an LLM to extract a list of claims made
    in a body of text.

    'text_input' is either directly from a user input or a body of text
    from the web-scraping lambda.
    """

    client = connect_to_openai()

    raw_output = query_llm(text_input, client,
                              CLAIM_EXTRACTION_DEVELOPER_ROLE,
                              "Successfully extracted claims from text input.")
    if "[CLAIMS]" in raw_output:
        parts = raw_output.split("[CLAIMS]")
        summary_part = parts[0].replace("[SUMMARY]", "").strip()
        claims_part = parts[1].strip()
    else:
        summary_part = "Summary unavailable."
        claims_part = raw_output

    claims_list = convert_claims_string_to_list(claims_part)

    return summary_part, claims_list


def convert_claims_string_to_list(claims_string: str) -> list[Claim]:
    """This function takes the string output from the LLM 
    and converts it into a list of Claim objects.
    The LLM output is expected to be in the format:
    |Claim 1
    |Claim 2
    |Claim 3
    """

    validate_claims_string(claims_string)

    claims_list = re.split(r'\n|\|', claims_string)
    claims_list = [claim.strip()
                   for claim in claims_list if claim.strip() != ""]

    logging.info("Successfully converted claims string to list")

    return [Claim(claim_text=claim) for claim in claims_list]


def query_llm(prompt: str, client: OpenAI, developer_role: dict,
              succces_log: str) -> str:
    """
    Queries the LLM for high-level objective claims returned as a 
    newline-separated string for maximum token efficiency.
    """

    if prompt is None or prompt.strip() == "":
        raise ValueError("Prompt cannot be empty or None.")

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[developer_role,
                      {
                          "role": "user",
                          "content": prompt
                      }
                      ],
            temperature=1,
            reasoning_effort="low",
            max_completion_tokens=2000
        )
        logging.info(succces_log)
        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Error querying LLM: {e}")
        raise RuntimeError("Failed to query LLM. Check logs for details.")


def validate_claims_string(claims_string: str) -> None:
    """ Validates that the claims string returned by the LLM is in the expected format. """

    if len(claims_string.strip()) == 0:
        raise ValueError(
            """LLM returned an empty string. No claims were extracted.
            Either the input text contained no verifiable claims, 
            or it is likely token limit is too low for query of this size.""")

    if "|" not in claims_string and "\n" not in claims_string:
        raise ValueError(
            """LLM output does not contain expected pipe characters. Check LLM response format is 
            '|Claim 1\\n|Claim 2\\n|Claim 3'""")


def post_to_lambda(lambda_url: str, payload: dict) -> dict:
    """Sends a POST request to a lambda URL
    and returns the response as a dict."""

    logging.info(
        f"Sending POST request to lambda with payload: {payload}")

    if "claims" in payload:
        payload["queries"] = payload["claims"]

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


def send_claims_to_rag_lambda(claims: list[Claim], lambda_url: str) -> list[dict]:
    """Sends claims to the RAG lambda and
    returns relevant facts with metadata."""

    # convert Claim objects to strings
    claims = [claim.claim_text for claim in claims]

    payload = {"claims": claims}
    response = post_to_lambda(lambda_url, payload)

    return response


def send_claims_to_wiki_lambda(claims: list[Claim], lambda_url: str) -> list[dict]:
    """Sends claims to the Wikipedia lambda and
    returns Wikipedia evidence for each claim."""

    # convert Claim objects to strings
    claims = [claim.claim_text for claim in claims]

    payload = {"claims": claims}

    response = post_to_lambda(lambda_url, payload)

    return response["wiki_context"]


def rate_claims_via_llm(claims: list[Claim], wiki_context: list[dict], rag_context: list[dict]) -> str:
    """
    This functions sends the claims to openai along with context from
    Wikipedia and RAG. 
    Openai will return categorical ratings for each claim along with a brief explanation for the rating.
    This will include the source that a claim was proved/disproved via.

    Openai will also summarize the overall user input in a short description.
    """

    client = connect_to_openai()

    prompt = create_llm_prompt(claims, wiki_context, rag_context)

    response = query_llm(prompt, client,
                         CLAIM_RATING_DEVELOPER_ROLE,
                         "Successfully rated claims based on Wikipedia and RAG context.")

    logging.info(f"LLM returned response: {response[:50]} ...")

    return response


def convert_llm_response_to_dict(llm_response: str) -> list[dict]:
    """Converts LLM rating output string to a
    list of structured claim dicts.

    Each dict has: claim, rating,
    explanation, sources.
    """

    result = []

    llm_response = llm_response.strip()
    # claims = re.split(r'\n\|', llm_response)
    claims = [c for c in llm_response.split("|") if c.strip()]

    for claim in claims:
        info = re.split(r"',\s*'", claim)

        claim_dict = {
            "claim": info[0].replace("|", "").replace("'", ""),
            "rating": info[1].upper().strip(),
            "evidence": (info[2] + " " + info[3].replace("'", "")).strip()
        }

        result.append(claim_dict)

    logging.info(f"Claims and ratings obtained: {result[:3]}")

    return result


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
6. DO INCLUDE " ' " characters in the response to allow for clear parsing of the explanation and sources.

### Output Format:
|'claim_made','rating','[Evidence]', 'Sources: [Wikipedia and/or the specific Source URL(s) or 'None' if UNSURE]' """

    return prompt


def validate_inputs_for_prompt(claims: list[Claim], wiki_context: list[dict], rag_context: list[list]) -> None:
    """Validates the inputs for the LLM prompt. Raises ValueError if any of the inputs are invalid."""

    if not isinstance(claims, list) or not all(isinstance(c, Claim) for c in claims):
        raise ValueError("Claims must be a list of Claim objects.")

    if wiki_context is not None and (not isinstance(wiki_context, list) or not all(isinstance(w, dict) for w in wiki_context)):
        raise ValueError("ERROR: Wikipedia context must be a list of dictionaries.")

    if rag_context is not None and (not isinstance(rag_context, list) or not all(isinstance(r, list) for r in rag_context)):
        raise ValueError("ERROR: RAG context must be a list of lists.")

    if claims == []:
        raise ValueError("Claims list is empty.")
    if wiki_context == []:
        raise ValueError("Wikipedia context list is empty.")
    if rag_context == []:
        raise ValueError("RAG context list is empty.")


def validate_response_format(response: str) -> None:
    """Validates the LLM rating response format.
    Raises ValueError if pipe-prefixed entries
    or valid uppercase ratings are absent.
    """
    pipe_entry_pattern = re.compile(
        r"^\|", re.MULTILINE
    )
    valid_rating_pattern = re.compile(
        r"\b(SUPPORTED|CONTRADICTED|MISLEADING|UNSURE)\b"
    )

    has_pipe_entry = pipe_entry_pattern.search(response)
    has_valid_rating = valid_rating_pattern.search(response)

    if not has_pipe_entry:
        raise ValueError(
            "Response missing pipe-prefixed claim entries."
        )
    if not has_valid_rating:
        raise ValueError(
            "Response missing a valid uppercase rating."
        )
    

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
