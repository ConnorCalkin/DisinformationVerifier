import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


def get_chroma_client_local():
    '''
    Returns a local Chroma client, which can be used to connect to a local 
    Chroma instance.
    '''
    try:
        return chromadb.Client()
    except Exception as e:
        logger.error(f"Error creating local Chroma client: {e}")
        raise e


def get_chroma_client_http(chroma_host: str, chroma_port: str):
    '''
    Returns an HTTP client for Chroma, 
    which can be used to connect to a remote Chroma instance.
    '''
    try:
        return chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port
        )
    except Exception as e:
        logger.error(f"Error creating Chroma HTTP client: {e}")
        raise e


def get_article_collection(client):
    '''
    Returns a Chroma collection for storing article chunks.
    If the collection doesn't exist, it will be created.
    '''
    try:
        return client.get_or_create_collection(
            name='articles',
            embedding_function=OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
    except Exception as e:
        logger.error(f"Error creating Chroma collection: {e}")
        raise e


def get_openai_client():
    '''
    Returns an OpenAI client, which can be used to create embeddings.
    '''
    try:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {e}")
        raise e
