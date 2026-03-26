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
    Extract only the MAIN objective, verifiable claims. Ignore minor details,
    repetitive updates, subjective information or trivial data points.

    # Constraints
    1. Essential Claims Only: Extract only the most significant units of information.
    2. Objective & Atomic: No opinions or subjective statements. Each statement must stand alone.
    3. Contextual Independence: Replace pronouns with nouns (e.g., "The President" instead of "He").
    4. No Overlap: Ensure claims are mutually exclusive.
    5. If a claim is subjective, emotional, or an opinion (e.g., "I love...", "I don't like..."), DO NOT include it.

    # Output Format
    Return ONLY the claims as a plain text list, with each claim on a NEW LINE starting with a pipe character (|). 
    Do not use JSON, markdown, or introductory text.

    # Example Output
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
Evaluate "Claims" against the provided "Factual Context" (Wiki or RAG chunks). 

# Rating Definitions
1. SUPPORTED: Context explicitly confirms the claim.
2. CONTRADICTED: Context explicitly refutes the claim.
3. MISLEADING: Claim is partially accurate but uses imprecise language, lacks nuance, or is not 100% supported by the text provided.
4. UNSURE: Context lacks sufficient information.

# Constraints
1. Objectivity: Use ONLY provided context. No external knowledge.
2. Tone: Be concise. One to two sentences max for the explanation.
3. Formatting: Return ONLY the results. No intro/outro text.

# Output Format
Return each result on a NEW LINE starting with a pipe character in this exact format:
|'claim_made','rating','[Explanation sentence]'. Sources: [Specify "Wiki" and/or the specific URL(s) provided in the RAG facts]"""

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


def get_claims_from_text(text_input: str) -> list[Claim]:
    """This function uses an LLM to extract a list of claims made
    in a body of text.

    'text_input' is either directly from a user input or a body of text
    from the web-scraping lambda.
    """

    client = connect_to_openai()

    claims_string = query_llm(text_input, client,
                              CLAIM_EXTRACTION_DEVELOPER_ROLE,
                              "Successfully extracted claims from text input.")

    claims_list = convert_claims_string_to_list(claims_string)

    return claims_list


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

    logging.info(f"Sending POST request to lambda at {lambda_url} with payload: {payload}")

    payload["queries"] = payload["claims"]

    response = requests.post(
        lambda_url,
        json=payload
    )

    if response.status_code != 200:
        logging.error(f"Lambda request failed with status code {response.status_code}: {response.text}")
        raise RuntimeError(f"")

    logging.info(f"Received response from lambda: {response.json()}")

    return response.json()


# def validate_response_status(response: dict, status_key: str) -> None:
#     """Raises RuntimeError if the response
#     status code is not 200."""

#     if response.get(status_key) != 200:
#         error_msg = response.get(
#             "message",
#             "Lambda request failed."
#         )
#         raise RuntimeError(error_msg)


def send_url_to_web_scraping_lambda(user_url: str, lambda_url: str) -> str:
    """Sends a URL to the web-scraping lambda
    and returns the extracted text body."""
    payload = {"url": user_url}
    response = post_to_lambda(lambda_url, payload)
    # validate_response_status(
    #     response, "status_code"
    # )
    return response["message"]


def send_claims_to_rag_lambda(claims: list[Claim], lambda_url: str) -> list[dict]:
    """Sends claims to the RAG lambda and
    returns relevant facts with metadata."""

    claims = [claim.claim_text for claim in claims]  # convert Claim objects to strings

    payload = {"claims": claims}
    response = post_to_lambda(lambda_url, payload)
    
    # validate_response_status(
    #     response, "statusCode"
    # )

    return response


def send_claims_to_wiki_lambda(claims: list[Claim], lambda_url: str) -> list[dict]:
    """Sends claims to the Wikipedia lambda and
    returns Wikipedia evidence for each claim."""

    claims = [claim.claim_text for claim in claims]  # convert Claim objects to strings

    payload = {"claims": claims}
    
    response = post_to_lambda(lambda_url, payload)
    # validate_response_status(
    #     response, "statusCode"
    # )
    return response["body"]["wiki_context"]


def rate_claims_via_llm(claims: list[Claim], wiki_context: list[str], rag_context: list[dict]) -> str:
    """
    This functions sends the claims to openai along with context from
    wiki and RAG. 
    Openai will return categorical ratings for each claim along with a brief explanation for the rating.
    This will include the source that a claim was proved/disproved via.

    Openai will also summarize the overall user input in a short description.
    """

    client = connect_to_openai()

    prompt = create_llm_prompt(claims, wiki_context, rag_context)

    response = query_llm(prompt, client,
                         CLAIM_RATING_DEVELOPER_ROLE,
                         "Successfully rated claims based on wiki and RAG context.")

    validate_response_format(response)

    return response


def convert_llm_response_to_dict(llm_response: str) -> list[dict]:
    """Converts LLM rating output string to a
    list of structured claim dicts.

    Each dict has: claim, rating,
    explanation, sources.
    """
    pipe_line_pattern = re.compile(  # pattern to ascertain information
        r"\|'([^']+)','([^']+)','([^']+)',\s*Sources:\s*(.+)"
    )

    result = []
    for line in llm_response.splitlines():
        match = pipe_line_pattern.search(line)
        if not match:
            continue

        claim_dict = {
            "claim": match.group(1),
            "rating": match.group(2),
            "explanation": match.group(3),
            "sources": match.group(4).strip()
        }
        result.append(claim_dict)

    return result


def create_llm_prompt(
    claims: list[Claim],
    wiki_context: list[str],
    rag_context: list[dict]
) -> str:
    """Creates a prompt for the LLM based on
    claims, wiki context and RAG context.

    RAG dict keys: title, content,
    source_url, created_at"""

    validate_inputs_for_prompt(claims, wiki_context, rag_context)

    claims_strings = "\n".join(
        [f"[{claim.claim_text}]" for claim in claims]
    )

    wiki_strings = "\n".join(
        [f"[{e}]" for e in wiki_context]
    )

    rag_strings = "\n".join(
        [
            f"[{r['content']}] (Source: {r['source_url']}, Date: {r['created_at']})"
            for r in rag_context
        ]
    )

    prompt = f"""Evaluate the following claims based on
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
4. Identify if the information came from "Wiki", a URL, or multiple.
5. DO NOT include any sources if the claim is rated UNSURE.

### Output Format:
|'claim_made','rating','[Explanation]'. Sources: [Wiki and/or the specific Source URL(s) or 'None' if UNSURE]"""

    return prompt


def validate_inputs_for_prompt(claims: list[Claim], wiki_context: list[str], rag_context: list[dict]) -> None:
    """Validates the inputs for the LLM prompt. Raises ValueError if any of the inputs are invalid."""

    if not isinstance(claims, list) or not all(isinstance(c, Claim) for c in claims):
        raise ValueError("Claims must be a list of Claim objects.")

    if not isinstance(wiki_context, list) or not all(isinstance(w, str) for w in wiki_context):
        raise ValueError("Wiki context must be a list of strings.")

    if not isinstance(rag_context, list) or not all(isinstance(r, dict) for r in rag_context):
        raise ValueError("RAG context must be a list of dictionaries.")

    if claims == []:
        raise ValueError("Claims list is empty.")
    if wiki_context == []:
        raise ValueError("Wiki context list is empty.")
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
