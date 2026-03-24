import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os


def get_chroma_client_local():
    '''
    Returns a local Chroma client, which can be used to connect to a local 
    Chroma instance.
    '''
    return chromadb.Client()


def get_chroma_client_http(chroma_host: str, chroma_port: str):
    '''
    Returns an HTTP client for Chroma, 
    which can be used to connect to a remote Chroma instance.
    '''
    return chromadb.HttpClient(
        host=chroma_host,
        port=chroma_port
    )


def get_article_collection(client):
    '''
    Returns a Chroma collection for storing article chunks.
    If the collection doesn't exist, it will be created.
    '''
    return client.get_or_create_collection(
        name='articles',
        embedding_function=OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
    )
