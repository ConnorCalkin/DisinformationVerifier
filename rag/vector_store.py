"""
Purpose: Store chunks in Chroma.
"""


import logging

logger = logging.getLogger(__name__)


def add_chunks(collection, chunks: list[str], metadata: dict):
    """
    Saves chunk text, embedding, and metadata.
    - allows for fast semantic search later
    """

    ids = [f"{metadata['article_id']}_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            **metadata,
            "chunk_index": i
        }
        for i in range(len(chunks))
    ]

    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(
        f"Stored {len(chunks)} chunks for article {metadata['article_id']}")
