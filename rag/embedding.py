"""
Purpose: Convert text into vectors.
"""

from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
import logging

from openai import OpenAI
import os

logger = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
    '''
    Returns an OpenAI client, which can be used to create embeddings.
    '''
    try:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {e}")
        raise e


def get_embedding(text: str) -> list[float]:
    """
    Sends the text to OpenAI, which returns the embedding.
    - enables similarity search in vector DB
    """

    client = get_openai_client()

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    embedding = response.data[0].embedding

    logger.info("Embedding created successfully")

    return embedding
