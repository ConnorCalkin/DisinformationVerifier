import logging
from os import environ
from datetime import datetime
import psycopg2
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection

def setup_logging():
    """ Configures logging for the application. Logs will be sent to the console. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def get_db_connection() -> connection:
    """ Establishes and returns a connection to the rds database. """
    try:
        conn = connect(
            host=environ.get("RDS_HOST"),
            port=environ.get("RDS_PORT"),
            dbname=environ.get("RDS_DB"),
            user=environ.get("RDS_USER"),
            password=environ.get("RDS_PASSWORD"),
            cursor_factory=RealDictCursor
        )
        logging.info("Database connection established successfully.")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        raise ConnectionError("Failed to connect to the database.")

def run_query(query: str, params: tuple = None) -> list:
    """ Executes a given SQL query and returns the results. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:  # Check if the query returns any results
                result = cur.fetchall()
            else:
                result = []
    logging.info("Query executed successfully.")
    return result

def fetch_input_history_list() -> list:
    '''
    Fetches the list of all input history from the database.
    '''
    query = """
            SELECT 
                input_id,
                input_text,
                input_summary,
                created_at
            FROM 
                input
            ORDER BY 
                created_at DESC
            """
    return run_query(query)

def fetch_input_details(input_id: int) -> dict:
    '''
    Fetches the details of a specific input, including claims and metrics.
    '''
    query = """
            SELECT 
                i.input_id,
                i.input_text,
                i.input_summary,
                i.created_at,
                c.claim_id,
                c.claim_text,
                c.rating,
                c.evidence,
                m.confidence,
                m.accuracy,
                m.metrics_summary,
                s.source_type_name
            FROM 
                input i
            LEFT JOIN 
                claim c ON i.input_id = c.input_id
            LEFT JOIN 
                metrics m ON i.response_id = m.metrics_id
            LEFT JOIN
                source_type s ON c.source_type_id = s.source_type_id
            WHERE 
                i.input_id = %s
            """
    return run_query(query, (input_id,))


def metrics_input_query(confidence: float, accuracy: float, metrics_summary: str) -> str:
    """ Helper function to generate the SQL query for inserting metrics. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute( """
                INSERT INTO metrics (confidence, accuracy, metrics_summary)
                VALUES (%s, %s, %s) RETURNING metrics_id
                """, (confidence, accuracy, metrics_summary))
            metrics_id = cur.fetchone()['metrics_id']
    return metrics_id

def source_type_query(source_type_name: str) -> str:
    """ Helper function to generate the SQL query for inserting source type. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO source_type (source_type_name)
                VALUES (%s) 
                ON CONFLICT (source_type_name) DO UPDATE SET source_type_name = EXCLUDED.source_type_name
                RETURNING source_type_id
                """, (source_type_name,))
            source_type_id = cur.fetchone()['source_type_id']
    return source_type_id

def input_query(input_text: str, input_summary: str, source_type_id: int, metrics_id: int) -> str:
    """ Helper function to generate the SQL query for inserting input. """
    created_at = datetime.now()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO input (input_text, input_summary, source_type_id, metrics_id, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING input_id
                """, (input_text, input_summary, source_type_id, metrics_id, created_at))
            input_id = cur.fetchone()['input_id']
    return input_id

def claim_query(input_id: int, claim_text: str, rating: str, evidence: str) -> None:
    """ Helper function to generate the SQL query for inserting claims. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO claim (input_id, claim_text, rating, evidence)
                VALUES (%s, %s, %s, %s)
                """, (input_id, claim_text, rating, evidence))


def archive_user_input(input_text: str,
                       input_summary: str,
                       source_type_name: str,
                       confidence: float,
                       accuracy: float,
                       metrics_summary: str,
                       claims: list[dict]) -> None:
    """ 
    Archives a new user input along with its claims and metrics into the database. 
    Uses a transaction to ensure data integrity across multiple tables.
    """
    conn = get_db_connection()
    try:
        # Insert metrics to retrieve metrics_id
        metrics_id = metrics_input_query(confidence, accuracy, metrics_summary)
        # Insert source type to retrieve source_type_id
        source_type_id = source_type_query(source_type_name)
        # Insert input and retrieve input_id
        input_id = input_query(input_text, input_summary,
                               source_type_id, metrics_id)
        # Insert claims
        for claim in claims:
            claim_query(input_id, claim['claim_text'],
                        claim['rating'], claim['evidence'])
        conn.commit()
        logging.info(
            f"Successfully archived user input with input_id: {input_id}")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error archiving user input: {e}")
        raise RuntimeError(
            "Failed to archive user input. Check logs for details.")
    finally:
        conn.close()
