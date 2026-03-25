import os
import logging
import psycopg2
from psycopg2.extensions import connection
from psycopg2.errors import ConnectionFailure

logger = logging.getLogger(__name__)


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
    except ConnectionFailure as e:
        logger.error("Error connecting to RDS: %s", e)
        raise e
