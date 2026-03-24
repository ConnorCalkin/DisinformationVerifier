import logging
from os import environ
from dotenv import load_dotenv

import chromadb
from chromadb.utils import embedding_functions

if not environ.get("OPENAI_API_KEY"):
    load_dotenv()

logger = logging.getLogger(__name__)


def get_chroma_client_local() -> chromadb.Client:
    '''
    Returns a local Chroma client, which can be used to connect to a local 
    Chroma instance.
    '''
    try:
        return chromadb.Client()

    except chromadb.ChromaError as e:
        logger.error(f"Error creating local Chroma client: {e}")
        raise e


def get_chroma_client_http(chroma_host: str, chroma_port: str) -> chromadb.HttpClient:
    '''
    Returns an HTTP client for Chroma, 
    which can be used to connect to a remote Chroma instance.
    '''
    try:
        return chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port
        )
    except chromadb.ChromaError as e:
        logger.error(f"Error creating Chroma HTTP client: {e}")
        raise e


def get_article_collection(client: chromadb.Client) -> chromadb.Collection:
    '''
    Returns a Chroma collection for storing article chunks.
    If the collection doesn't exist, it will be created.
    '''
    try:
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        collection = client.get_or_create_collection(
            name="my_collection",
            embedding_function=openai_ef
        )
        return collection
    except Exception as e:
        logger.error(f"Error creating Chroma collection: {e}")
        raise e
