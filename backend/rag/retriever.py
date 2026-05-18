import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

_client = None
_encoder = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def get_or_create_collection(name: str):
    return get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, collection_name: str, k: int = 5) -> dict:
    collection = get_or_create_collection(collection_name)
    count = collection.count()
    if count == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

    actual_k = min(k, count)
    embedding = get_encoder().encode([query])[0].tolist()
    return collection.query(
        query_embeddings=[embedding],
        n_results=actual_k,
        include=["documents", "metadatas", "distances"],
    )


def collection_stats() -> list:
    client = get_client()
    stats = []
    for col in client.list_collections():
        stats.append({"name": col.name, "document_count": col.count()})
    return stats
