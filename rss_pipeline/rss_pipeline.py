"""Orchestrates RSS pipeline, scraping articles, chunking, embedding and adding to RDS"""

import logging

import rss_web_scraping.extract_content as extract_content
from rag import chunking, embedding, vector_store, connection


def setup_logging():
    """
    Configures logging for the Lambda function. Logs will be sent to CloudWatch.
    """

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


setup_logging()
logger = logging.getLogger(__name__)


def main(event: dict = None, context: dict = None) -> None:
    """
    Runs the full RSS pipeline: scrape, chunk, embed, and store.
    """

    articles = extract_content.run()
    articles_added = 0
    with connection.get_db_connection() as conn:
        for article in articles:
            embeddings = []
            try:
                chunks = chunking.chunk_text(article["content"])
            except Exception as e:
                logger.error(
                    f"Error chunking article: {e}")
                continue

            try:
                for chunk in chunks:
                    embeddings.append(embedding.get_embedding(chunk))
            except Exception as e:
                logger.error(
                    f"Error generating embedding for article: {e}")
                continue

            try:
                vector_store.add_chunks_to_rds(
                    conn, chunks, embeddings, article)
                articles_added += 1
            except Exception as e:
                conn.rollback()
                logger.error(
                    f"Error adding chunks to RDS for article: {e}")
                continue

    return {
        "statusCode": 200,
        "body": f"Successfully added {articles_added} out of {len(articles)} articles to RDS."
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
