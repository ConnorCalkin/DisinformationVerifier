import logging

logger = logging.getLogger(__name__)


def add_chunks_to_rds(conn,
                      chunks: list[str],
                      embeddings: list[list[float]],
                      metadata: dict) -> None:
    """
    Saves chunk text and metadata to RDS.
    - allows for fast retrieval later
    """

    with conn.cursor() as cur:
        for i, chunk in enumerate(chunks):
            embedding_data = embeddings[i]
            cur.execute(
                """
                INSERT INTO documents (
                    title,
                    source_url,
                    content,
                    published_at,
                    embedding
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    metadata['title'],
                    metadata['source_url'],
                    chunk,
                    metadata['published_at'],
                    embedding_data
                )
            )
        conn.commit()
    logger.info(
        "Stored %d chunks for article %s in RDS", len(chunks), metadata['article_id'])
