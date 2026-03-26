from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor
from embedding import get_embedding


def retrieve_relevant_chunks(connection: connection,
                             query: str,
                             top_k: int = 5,
                             max_dist: float = 1) -> list[dict]:
    """
    Retrieves the most relevant chunks for a given query.
    """

    # Get an embedding for the query
    embedding = get_embedding(query)

    # Query the database for the most relevant chunks
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT title, content, source_url, published_at, (embedding <=> %s::vector) AS distance
        FROM documents
        WHERE (embedding <=> %s::vector) <= %s
        ORDER BY distance ASC
        LIMIT %s;
        """,
        (embedding, embedding, max_dist, top_k)
    )

    results = cursor.fetchall()

    return results
