import logging
from os import environ
from datetime import datetime
import psycopg2
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection
from dotenv import load_dotenv


def setup_logging():
    """ Configures logging for the application. Logs will be sent to the console. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


load_dotenv()


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
                m.supported,
                m.contradicted,
                m.misleading,
                m.unsure,
                s.source_type_name
            FROM 
                input i
            LEFT JOIN 
                claim c ON i.input_id = c.input_id
            LEFT JOIN 
                metrics m ON i.metrics_id = m.metrics_id
            LEFT JOIN
                source_type s ON i.source_type_id = s.source_type_id  -- FIXED: changed c. to i.
            WHERE 
                i.input_id = %s
            """

    return run_query(query, (input_id,))


def metrics_table_insert_execution(cur, supported: float, contradicted: float, misleading: float, unsure: float) -> str:
    """ Helper function to generate the SQL query for inserting metrics. """
    cur.execute("""
                INSERT INTO metrics (supported, contradicted, misleading, unsure)
                VALUES (%s, %s, %s, %s) RETURNING metrics_id
                """, (supported, contradicted, misleading, unsure))
    metrics_id = cur.fetchone()['metrics_id']
    return metrics_id


def source_type_table_insert_execution(cur, source_type_name: str) -> str:
    """ Helper function to generate the SQL query for inserting source type. """
    cur.execute("""
                INSERT INTO source_type (source_type_name)
                VALUES (%s) 
                ON CONFLICT (source_type_name) DO UPDATE SET source_type_name = EXCLUDED.source_type_name
                RETURNING source_type_id
                """, (source_type_name,))
    source_type_id = cur.fetchone()['source_type_id']
    return source_type_id


def input_table_insert_execution(cur, input_text: str, input_summary: str, source_type_id: int, metrics_id: int) -> str:
    """ Helper function to generate the SQL query for inserting input. """
    created_at = datetime.now()
    cur.execute("""
        INSERT INTO input (input_text, input_summary, source_type_id, metrics_id, created_at)
        VALUES (%s, %s, %s, %s, %s) RETURNING input_id
        """, (input_text, input_summary, source_type_id, metrics_id, created_at))
    input_id = cur.fetchone()['input_id']
    return input_id


def claim_table_insert_execution(cur, input_id: int, claim: str, rating: str, evidence: str) -> None:
    """ Helper function to generate the SQL query for inserting claims. """
    cur.execute("""
        INSERT INTO claim (input_id, claim_text, rating, evidence)
        VALUES (%s, %s, %s, %s)
        """, (input_id, claim, rating, evidence))


def archive_user_input(input_text: str,
                       input_summary: str,
                       source_type_name: str,
                       supported: float,
                       contradicted: float,
                       misleading: float,
                       unsure: float,
                       claims: list[dict]) -> None:
    """ 
    Archives a new user input along with its claims and metrics into the database. 
    Uses a transaction to ensure data integrity across multiple tables.
    """
    if not claims:
        logging.warning(
            "No claims to archive for this input. Skipping archive.")
        return
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert metrics to retrieve metrics_id
            metrics_id = metrics_table_insert_execution(
                cur, supported, contradicted, misleading, unsure)
            # Insert source type to retrieve source_type_id
            source_type_id = source_type_table_insert_execution(
                cur, source_type_name)
            # Insert input and retrieve input_id
            input_id = input_table_insert_execution(cur, input_text, input_summary,
                                                    source_type_id, metrics_id)
            # Insert claims
            for claim in claims:
                claim_table_insert_execution(cur, input_id, claim['claim'],
                                             claim['rating'], claim['evidence'])
            conn.commit()
            logging.info(
                f"Successfully archived user input with input_id: {input_id}")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error archiving user input: {e}")
        print(f"Error archiving user input: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_source_ratings():

    query = """
            SELECT 
                s.source_type_name,
                COUNT(i.input_id) AS total_inputs,
                SUM(m.contradicted) AS total_contradicted,
                SUM(m.misleading) AS total_misleading,
                ROUND(
                    CAST(
                        (SUM(m.contradicted) + SUM(m.misleading)) / NULLIF(COUNT(i.input_id), 0) * 100 
                    AS NUMERIC), 
                2) AS unreliability_pct
            FROM source_type s
            JOIN input i ON s.source_type_id = i.source_type_id
            JOIN metrics m ON i.metrics_id = m.metrics_id  -- This is the corrected line
            GROUP BY s.source_type_id, s.source_type_name
            ORDER BY unreliability_pct DESC
            LIMIT 10;
        """

    results = run_query(query)

    return results
