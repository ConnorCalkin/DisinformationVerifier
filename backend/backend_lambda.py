"""
This script respresents the lambda function which will be called in chatbot.py
"""

import logging

from lambda_connection_utils import (get_unrated_claims_from_input, get_context_from_lambdas ,rate_claims_via_llm)
import json
from os import environ

LLM_URL = environ["LLM_URL"]


def setup_logging():
    """ Configures logging for the Lambda function. Logs will be sent to CloudWatch. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def validate_event(event: dict) -> None:
    """Raises an error if event isn't in expected format"""

    if any(key not in event for key in ["input", "input_type", "source_type"]):
        raise KeyError("Event missing required keys input, input_type, source_type")
    
    if any(value is None for value in event.values()):
        raise ValueError("Event values cannot be None.")
    
    if not isinstance(event["input"], str) or \
        not isinstance(event["input_type"], str) or \
        not isinstance(event["source_type"], str):
        raise TypeError("Event values aren't correct object types.")
    

def lambda_handler(event, context):
    """Main lambda for the backend of the server.
    
    Event will contain: 
    - A url, claim or text chunk.
    - An input type specifying whether the input is a url, claim or text chunk.
    - The source that input has been made from (BBC, Twitter, etc.) and 
    will have the keys. {"input","input_type", "source_type"}

    Lambda will return a body that is a summary of the users input and a list of rated claims.

    """

    setup_logging()

    event = json.loads(event["body"])

    try:
        validate_event(event)
    except Exception as e:
        error_body = json.dumps({"error": f"{e}"})
        logging.error(f"Input validation failed: {e}")
        return {"statusCode": 400, "body": error_body}
    
    input = event["input"]
    input_type = event["input_type"]
    # source_type = event["source_type"]
    
    try:
        summary, unrated_claims = get_unrated_claims_from_input(input, input_type, LLM_URL)
        wiki_context, rag_context = get_context_from_lambdas(unrated_claims)
        rated_claims = rate_claims_via_llm(unrated_claims, wiki_context, rag_context, LLM_URL)
    except Exception as e:
        error_body = json.dumps({"error": f"Error processing input: {e}"})
        logging.error(f"Error during processing: {e}")
        return {"statusCode": 500, "body": error_body}

    response_body = json.dumps({
        "summary": summary,
        "rated_claims": rated_claims
    })

    return {"statusCode": 200, "body": response_body}


