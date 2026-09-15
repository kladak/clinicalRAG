import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
import numpy as np
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

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


class _OnnxEncoder:
    """all-MiniLM-L6-v2 via Chroma's bundled ONNX runtime.

    Exposes the ``.encode(texts) -> ndarray`` surface the retrieval and
    ingestion paths already call, so callers are unchanged. The model is
    fetched once into ``~/.cache/chroma`` and is baked into the image at
    build time, so process start needs no network.
    """

    def __init__(self) -> None:
        self._fn = ONNXMiniLM_L6_V2()

    def encode(self, texts):
        return np.asarray(self._fn(list(texts)), dtype=np.float32)


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = _OnnxEncoder()
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
