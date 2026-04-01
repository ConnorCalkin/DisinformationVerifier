"""
This script represents the lambda function which will be called in chatbot.py

The lambda function will take an input of developer_role, prompt and structured output."""

import logging
from os import environ
import boto3
import json
from openai import OpenAI
from pydantic import BaseModel

_CACHED_SECRET = None
_OPENAI_CLIENT = None
sm_client = boto3.client('secretsmanager', region_name='eu-west-2')


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


class NamedEntity(BaseModel):
    name: str


class NamedEntityResponse(BaseModel):
    search_terms: list[NamedEntity]


""" {"search_terms": ["NASA", "Artemis program", "2024 Solar Eclipse"]}}"""
"""{"type": "json_object"}"""


structured_outputs = {
    "rated_claims": RatedClaimResponse,
    "unrated_claims": UnratedClaimResponse,
    "entities": NamedEntityResponse
}


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
        raise RuntimeError(f"Failed to initialize OpenAI client {e}.")


def query_llm(prompt: str, client: OpenAI, developer_role: dict,
              success_log: str, response_format: object) -> object:
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

        logging.info(success_log)

        return response.output_parsed

    except Exception as e:
        logging.error(f"Error querying LLM: {e}")
        raise RuntimeError(f"Failed to query LLM. Check logs for details.{e}")


def parse_response(
    llm_response: (
        UnratedClaimResponse
        | RatedClaimResponse
        | NamedEntityResponse
    )
) -> dict:
    """Parse the llm response into a Lambda-
    compatible dict with statusCode and body."""

    if isinstance(llm_response, UnratedClaimResponse):
        body = json.dumps({
            "summary": llm_response.summary,
            "claims": llm_response.claims
        })
        return {"statusCode": 200, "body": body}

    if isinstance(llm_response, RatedClaimResponse):
        body = json.dumps([
            {
                "claim": rated_claim.claim,
                "rating": rated_claim.rating,
                "explanation": rated_claim.explanation,
                "sources": rated_claim.sources
            }
            for rated_claim in llm_response.rated_claims
        ])
        return {"statusCode": 200, "body": body}

    if isinstance(llm_response, NamedEntityResponse):
        body = json.dumps([
            named_entity.name
            for named_entity in llm_response.search_terms
        ])
        return {"statusCode": 200, "body": body}

    error_body = json.dumps({
        "error": "Unknown 'structured_output' received."
    })
    return {"statusCode": 400, "body": error_body}


def validate_event(event: dict) -> None:
    """Raises an error if expected keys aren't in body or are incorrect types."""

    if any(key not in event for key in ["dv_role",
                                        "prompt",
                                        "success_message", ""
                                        "structured_output"]):
        raise KeyError("Event missing required keys dv_role, prompt,"
                       " success_message, structured_output")

    if not isinstance(event["dv_role"], dict) or \
            not isinstance(event["prompt"], str) or \
            not isinstance(event["success_message"], str):
        raise TypeError("Event values aren't correct object types.")


def lambda_handler(event, context):
    """Takes developer role, prompt and structured output as inputs.

    Queries openAI LLM and returns response.

    Event is in the form {"dv_role": dict, 
    "prompt": str, 
    "structured_output": rated_claims | unrated_claims | entities,
    "success_message": str}
    """

    event = json.loads(event["body"])
    logging.info("Event parsed successfully")

    try:
        validate_event(event)

        developer_role = event["dv_role"]
        prompt = event["prompt"]
        success_message = event["success_message"]

        structured_output_option = event["structured_output"]

        structured_output = structured_outputs.get(structured_output_option)

        client = get_openai_client()

        response = query_llm(prompt, client, developer_role,
                             success_message, structured_output)

    except Exception as e:
        error_body = json.dumps({"error": f"{e}"})
        return {"statusCode": 400, "body": error_body}

    return parse_response(response)
