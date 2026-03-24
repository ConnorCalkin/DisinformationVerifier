"""
Purpose: Convert article text into chunks.
"""

import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Takes the full text of an article, loops through it, creating overlapping chunks.
    - improved retrieval accuracy and avoids long inputs (expensive)
    """

    text = text.strip()
    if not text:
        raise ValueError("Input text cannot be empty or whitespace only.")

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    end = start + chunk_size
    while start < len(text) and end <= len(text):

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap
        end = start + chunk_size

    logger.info(f"Created {len(chunks)} chunks")

    return chunks
