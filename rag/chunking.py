"""
Purpose: Convert article text into chunks.
"""
import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 100, overlap: int = 10) -> list[str]:
    """
    Takes the full text of an article, loops through it, creating overlapping chunks.
    - improved retrieval accuracy and avoids long inputs (expensive)
    """

    text = text.strip()
    if not text:
        logger.error("Input text cannot be empty or whitespace only.")
        raise ValueError("Input text cannot be empty or whitespace only.")

    text_words = text.split(" ")

    if len(text_words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    end = start + chunk_size
    while start < len(text_words) and end <= len(text_words):

        chunk = " ".join(text_words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap
        end = start + chunk_size

    logger.info(f"Created {len(chunks)} chunks")

    return chunks


if __name__ == "__main__":
    sample_text = "This is a sample article text that will be chunked into smaller pieces for testing purposes. " * 50
    chunks = chunk_text(sample_text)
    print(f"Number of chunks created: {len(chunks)}")
    for chunk in chunks[:3]:  # print first 3 chunks
        print(f"Chunk: {chunk}\n")
