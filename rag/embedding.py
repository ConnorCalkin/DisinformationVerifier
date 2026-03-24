"""
Purpose: Convert text into vectors.
"""

import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file


def get_embedding(text: str) -> list[float]:
    """
    Sends the text to OpenAI, which returns the embedding.
    - enables similarity search in vector DB
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    embedding = response.data[0].embedding

    logger.info("Embedding created successfully")

    return embedding
