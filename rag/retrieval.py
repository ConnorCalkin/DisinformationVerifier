"""
Purpose: Find relevant chunks for a question.
"""

import logging

logger = logging.getLogger(__name__)


def retrieve_chunks(collection, query: str, n_results: int = 3, min_dist: float = 0) -> list[tuple[str, dict, float]]:
    """
    Queries chroma with the document to find relevant chunks.
    returns the chunk text, metadata, and distance for each relevant chunk.
    returns at max n_results chunks that have a distance above min_dist.
    only returns chunks that are relevant to the query (distance above min_dist).
    """

    # 2. Query Chroma
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # Filter results based on distance threshold
    filtered_results = [
        (doc, meta, dist)
        for doc, meta, dist in zip(documents, metadatas, distances)
        if dist >= min_dist
    ]

    logger.info(f"Retrieved {len(filtered_results)} chunks")

    return filtered_results
