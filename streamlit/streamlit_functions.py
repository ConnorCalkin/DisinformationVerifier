"""
This script contain functions and classes that are used in the streamlit app
"""

import re
import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEVELOPER_ROLE_CONTENT = """# Role
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

DEVELOPER_ROLE = {
    "role": "developer",
    "content": DEVELOPER_ROLE_CONTENT
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

    claims_string = query_llm(text_input, client)

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
                   for claim in claims_list if claim.strip()!=""]

    logging.info("Successfully converted claims string to list")

    return [Claim(claim_text=claim) for claim in claims_list]


def query_llm(prompt: str, client: OpenAI) -> str:
    """
    Queries the LLM for high-level objective claims returned as a 
    newline-separated string for maximum token efficiency.
    """

    if prompt is None or prompt.strip() == "":
        raise ValueError("Prompt cannot be empty or None.")

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[DEVELOPER_ROLE,
                      {
                          "role": "user",
                          "content": prompt
                      }
                      ],
            temperature=1,
            reasoning_effort="low",
            max_completion_tokens=2000
        )
        logging.info("Successfully queried LLM for claims extraction.")
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


if __name__ == "__main__":
    # Example usage

    setup_logging()
    TEXT_INPUT = """
Donald Trump is resigning as president"""

    claims = get_claims_from_text(TEXT_INPUT)

    for claim in claims:
        print(claim.claim_text)
