'''
    Main function for the RAG lambda.
'''
from datetime import datetime
import logging
import json

import psycopg2

from connection import get_db_connection
from retrieval import retrieve_relevant_chunks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_valid_event_body(event_body: dict) -> bool:
    """
    Returns True if the event is valid, False otherwise.
    """

    if not isinstance(event_body, dict):
        return False

    if "queries" not in event_body:
        return False

    if not isinstance(event_body["queries"], list):
        return False

    for query in event_body["queries"]:
        if not isinstance(query, str):
            return False

    return True


def datetime_handler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def main(event: dict = None, context: dict = None) -> dict:
    '''
        Main function for the RAG lambda
        - connects to Chroma
        - retrieves relevant chunks for each query in the event
        - returns the retrieved chunks and their metadata
    '''
    event_body = event.get("body", {})
    if is_valid_event_body(event_body) is False:
        logger.warning("Invalid event format: %s", event_body)
        return {
            "statusCode": 400,
            "body": """
            Invalid event format.
            Expected a dict with a 'queries'
            key containing a list of strings.
            """
        }

    # add possible params to the retrieval function
    params = {}
    if "top_k" in event_body:
        params["top_k"] = event_body["top_k"]
    if "max_dist" in event_body:
        params["max_dist"] = event_body["max_dist"]

    # retrieve chunks for each query in the event
    try:
        with get_db_connection() as connection:
            chunks = [
                retrieve_relevant_chunks(connection, query, **params)
                for query in event_body.get("queries", [])
            ]
    except psycopg2.Error as e:
        logger.error("Error retrieving chunks: %s", e)
        return {
            "statusCode": 500,
            "body": f"Error retrieving chunks: {e}"
        }

    logger.info(
        "Retrieved chunks for %d queries", len(event_body.get("queries", [])))

    return {
        "statusCode": 200,
        # Use the custom datetime handler to serialize datetime objects in the chunks
        # Otherswise, the lambda will fail to serialize the response
        "body": json.dumps(chunks, default=datetime_handler)
    }
