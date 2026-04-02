import os
import logging
import json
from os import environ

import psycopg2
from psycopg2.extensions import connection
from psycopg2.errors import OperationalError
from openai import AsyncOpenAI
import boto3


logger = logging.getLogger(__name__)

_CACHED_SECRET = None
_OPENAI_CLIENT = None


def get_db_connection() -> connection:
    '''
    Connects to the RDS database and returns a connection object.
    '''
    try:
        conn = psycopg2.connect(
            host=os.environ.get("RDS_HOST"),
            port=os.environ.get("RDS_PORT"),
            database=os.environ.get("RDS_DB"),
            user=os.environ.get("RDS_USER"),
            password=os.environ.get("RDS_PASSWORD")
        )
        return conn
    except OperationalError as e:
        logger.error("Error connecting to RDS: %s", e)
        raise e


def get_boto3_client(service_name: str):
    """ Helper function to create a boto3 client for a given AWS service. """
    try:
        client = boto3.client(
            service_name, region_name=environ.get("AWS_REGION", "eu-west-2"))
        logging.info(f"{service_name} client initialized successfully.")
        return client
    except Exception as e:
        logging.error(f"Error initializing {service_name} client: {e}")
        raise RuntimeError(f"Failed to initialize {service_name} client.")


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
        sm_client = get_boto3_client("secretsmanager")
        response = sm_client.get_secret_value(SecretId=secret_name)
        _CACHED_SECRET = json.loads(response['SecretString'])
        logging.info("Secrets successfully retrieved and cached.")
        return _CACHED_SECRET
    except Exception as e:
        logging.error("Error fetching secrets from AWS Secrets Manager: %s", e)
        raise EnvironmentError(
            "Failed to retrieve secrets from AWS Secrets Manager.")


def get_openai_client() -> AsyncOpenAI:
    """ Abstracted function to intialise and cache the OpenAI client. """
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT:
        return _OPENAI_CLIENT
    try:
        secrets = get_secrets()
        api_key = secrets.get('OPENAI_API_KEY')
        # Log the first few characters for verification
        if not api_key:
            logging.error("OPENAI_API_KEY not found in secrets.")
            raise KeyError("OPENAI_API_KEY not found in secrets.")
        _OPENAI_CLIENT = AsyncOpenAI(api_key=api_key)

        logging.info("OpenAI client initialized and cached.")
        return _OPENAI_CLIENT
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {e}")
        raise RuntimeError("Failed to initialize OpenAI client.")
