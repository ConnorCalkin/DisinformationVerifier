from psycopg2.extensions import connection
from psycopg2.extras import DictCursor
from embedding import get_embedding


def retrieve_relevant_chunks(connection: connection,
                             query: str,
                             top_k: int = 5) -> list[dict]:
    """
    Retrieves the most relevant chunks for a given query.
    """

    # Get an embedding for the query
    embedding = get_embedding(query)

    # Query the database for the most relevant chunks
    cursor = connection.cursor(cursor_factory=DictCursor)
    cursor.execute(
        """
        SELECT title, content, source_url, created_at, (embedding <=> %s::vector) AS distance
        FROM documents
        ORDER BY distance ASC
        LIMIT %s;
        """,
        (embedding, top_k)
    )

    results = cursor.fetchall()

    return results
