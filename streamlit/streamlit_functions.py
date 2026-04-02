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



class Claim:
    """
    This class represents a claim that has been extracted from the users input
    """

    def __init__(self, claim_text: str, category: str = None):
        self.claim_text = claim_text
        self.category = category






_CACHED_SECRET = None
_OPENAI_CLIENT = None



# def get_secrets() -> dict:
#     """Fetches OpenAI API key from AWS Secrets Manager."""

#     global _CACHED_SECRET
#     if _CACHED_SECRET:
#         return _CACHED_SECRET
#     secret_name = environ.get("SECRET_ID")
#     if not secret_name:
#         logging.error("SECRET_ID environment variable not set.")
#         raise EnvironmentError("SECRET_ID environment variable not set.")
#     try:
#         response = sm_client.get_secret_value(SecretId=secret_name)
#         _CACHED_SECRET = json.loads(response['SecretString'])
#         logging.info("Secrets successfully retrieved and cached.")
#         return _CACHED_SECRET
#     except Exception as e:
#         logging.error(f"Error fetching secrets from AWS Secrets Manager: {e}")
#         raise EnvironmentError(
#             "Failed to retrieve secrets from AWS Secrets Manager.")


# def get_openai_client() -> OpenAI:
#     """ Abstracted function to intialise and cache the OpenAI client. """

#     global _OPENAI_CLIENT
#     if _OPENAI_CLIENT:
#         return _OPENAI_CLIENT
#     try:
#         secrets = get_secrets()
#         api_key = secrets.get('OPENAI_API_KEY')
#         if not api_key:
#             logging.error("OPENAI_API_KEY not found in secrets.")
#             raise KeyError("OPENAI_API_KEY not found in secrets.")
#         _OPENAI_CLIENT = OpenAI(api_key=api_key)
#         logging.info("OpenAI client initialized and cached.")
#         return _OPENAI_CLIENT
#     except Exception as e:
#         logging.error(f"Error initializing OpenAI client: {e}")
#         raise RuntimeError("Failed to initialize OpenAI client.")





# def query_llm(prompt: str, client: OpenAI, developer_role: dict,
#               succces_log: str, response_format: object) -> UnratedClaimResponse | RatedClaimResponse:
#     """
#     Queries the LLM for high-level objective claims returned as a 
#     newline-separated string for maximum token efficiency.
#     """

#     if prompt is None or prompt.strip() == "":
#         raise ValueError("Prompt cannot be empty or None.")

#     try:
#         response = client.responses.parse(
#             model="gpt-5-nano",
#             input=[developer_role,
#                    {
#                        "role": "user",
#                        "content": prompt
#                    }
#                    ],
#             temperature=1,
#             reasoning={"effort": "low"},
#             text_format=response_format,
#         )

#         logging.info(succces_log)

#         return response.output_parsed

#     except Exception as e:
#         logging.error(f"Error querying LLM: {e}")
#         raise RuntimeError("Failed to query LLM. Check logs for details.")













# def convert_llm_response_to_dict(llm_response: RatedClaimResponse) -> list[dict]:
#     """Converts LLM rating output string to a
#     list of structured claim dicts.

#     Each dict has: claim, rating,
#     explanation, sources.
#     """

#     claim_dicts = [
#         {
#             "claim": rated_claim.claim,
#             "rating": rated_claim.rating.upper(),
#             "evidence": rated_claim.explanation,
#             "sources": rated_claim.sources
#         }
#         for rated_claim in llm_response.rated_claims if (rated_claim.claim and
#                                                          rated_claim.rating and
#                                                          rated_claim.explanation)
#     ]

#     logging.info(f"Claims and ratings obtained: {claim_dicts[:3]}")

#     return claim_dicts




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
