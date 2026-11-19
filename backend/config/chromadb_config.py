"""ChromaDB connection and collection setup with sentence-transformer embeddings."""

import os
import chromadb
from chromadb.utils import embedding_functions

_client = None
_ef = None
COLLECTION_NAME = 'crisis_knowledge'


def get_chroma_client():
    global _client
    if _client is None:
        host = os.environ.get('CHROMA_HOST', 'localhost')
        port = int(os.environ.get('CHROMA_PORT', 8001))
        _client = chromadb.HttpClient(host=host, port=port)
    return _client


def get_embedding_function():
    """
    Use sentence-transformers all-MiniLM-L6-v2 – small, CPU-compatible model.
    Downloads on first use (~80MB).
    """
    global _ef
    if _ef is None:
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
    return _ef


def get_collection():
    """Get or create the crisis knowledge collection."""
    client = get_chroma_client()
    ef = get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={'hnsw:space': 'cosine'}
    )
