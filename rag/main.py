'''
    Main function for the RAG lambda.
'''
from linecache import cache
import logging

import psycopg2


from connection import get_db_connection
from retrieval import retrieve_relevant_chunks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_valid_event(event: dict) -> bool:
    """
    Returns True if the event is valid, False otherwise.
    """
    if not isinstance(event, dict):
        return False

    if "queries" not in event:
        return False

    if not isinstance(event["queries"], list):
        return False

    for query in event["queries"]:
        if not isinstance(query, str):
            return False

    return True


def main(event: dict = None, context: dict = None) -> dict:
    '''
        Main function for the RAG lambda
        - connects to Chroma
        - retrieves relevant chunks for each query in the event
        - returns the retrieved chunks and their metadata
    '''
    if is_valid_event(event) is False:
        logger.warning("Invalid event format: %s", event)
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
    if "n_results" in event:
        params["n_results"] = event["n_results"]
    if "min_dist" in event:
        params["min_dist"] = event["min_dist"]

    # retrieve chunks for each query in the event
    try:
        with get_db_connection() as connection:
            chunks = [
                retrieve_relevant_chunks(connection, query, **params)
                for query in event.get("queries", [])
            ]
    except psycopg2.Error as e:
        logger.error("Error retrieving chunks: %s", e)
        return {
            "statusCode": 500,
            "body": f"Error retrieving chunks: {e}"
        }

    logger.info(
        "Retrieved chunks for %d queries", len(event.get("queries", [])))
    return {
        "statusCode": 200,
        "body": chunks
    }
