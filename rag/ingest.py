"""
Purpose: Full pipeline for one article.
"""

import hashlib
from chunking import chunk_text
from vector_store import add_chunks

import logging

logger = logging.getLogger(__name__)


def generate_chunks(article_id: str, text: str) -> list[str]:
    """
    Takes the full text of an article, loops through it, creating overlapping chunks.
    """
    chunks = chunk_text(text)

    if not chunks:
        logger.warning(f"No chunks created for article {article_id}")
        raise ValueError(f"No chunks created for article {article_id}")

    return chunks


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
        logger.warning(f"Invalid article text for URL {url}")
        raise ValueError(f"Invalid article text for URL {url}")

    article_id = generate_article_id(url)
    chunks = generate_chunks(article_id, text)
    metadata = build_metadata(article_id, title, url)
    add_chunks(collection, chunks, metadata)

    logger.info(f"Ingested article {article_id}")
