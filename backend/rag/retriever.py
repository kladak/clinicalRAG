import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import get_settings

_client = None
_encoder = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=get_settings().chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def reset_client() -> None:
    global _client
    _client = None


def get_encoder():
    global _encoder
    if _encoder is None:
        model_name = get_settings().embedding_model
        try:
            # Prefer local cache (Docker bake / prior download) so demos do not
            # hard-require outbound Hugging Face at process start.
            _encoder = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            _encoder = SentenceTransformer(model_name)
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
