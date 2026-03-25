"""
Purpose: Full pipeline for one article.
"""

import hashlib
import logging

from chunking import chunk_text
from vector_store import add_chunks


logger = logging.getLogger(__name__)


def build_metadata(article_id: str, title: str, url: str) -> dict:
    """
    Builds metadata dict for an article, which will be stored with each chunk.
    """
    # TODO: Update this to be the metadata gained from the article
    return {
        "article_id": article_id,
        "title": title,
        "url": url
    }


def generate_article_id(url: str) -> str:
    """
    Generates a unique article ID based on the URL.
    This works by hashing the URL using SHA-256, 
    which produces a fixed-length string that is unique to the input URL.
    """
    url = url.strip().rstrip("/").lower()
    return hashlib.sha256(url.encode()).hexdigest()


def ingest_article(collection, title: str, url: str, text: str) -> None:
    """
    Chunks text, attach metadata, and store everything in Chroma.
    - prepares data for RAG
    """

    if text.strip() is None or text.strip() == "":
        logger.warning("Invalid article text for URL %s", url)
        raise ValueError(f"Invalid article text for URL {url}")

    article_id = generate_article_id(url)
    chunks = chunk_text(text)
    metadata = build_metadata(article_id, title, url)
    add_chunks(collection, chunks, metadata)

    logger.info("Ingested article %s", article_id)
