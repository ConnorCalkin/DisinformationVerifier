"""Orchestrates RSS pipeline, scraping articles, chunking, embedding and adding to RDS"""

import rss_web_scraping.extract_content as extract_content
from rag import chunking, embedding, vector_store, connection


def main():
    """
    Runs the full RSS pipeline: scrape, chunk, embed, and store.
    """

    articles = extract_content.run()

    with connection.get_db_connection() as conn:
        for article in articles:
            embeddings = []
            chunks = chunking.chunk_text(article["content"])

            for chunk in chunks:
                embeddings.append(embedding.get_embedding(chunk))
                print(chunk)

            vector_store.add_chunks_to_rds(conn, chunks, embeddings, article)


if __name__ == "__main__":
    main()
