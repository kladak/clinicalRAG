"""Shared fixtures. Keep heavy ML deps out of unit tests when possible."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MOCK_LLM", "1")
os.environ.setdefault("CLINICALRAG_MOCK_LLM", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("LOG_JSON", "0")


@pytest.fixture()
def tmp_paths(monkeypatch, tmp_path):
    chroma = tmp_path / "chroma"
    audit = tmp_path / "audit.db"
    chroma.mkdir()
    monkeypatch.setenv("CHROMA_PATH", str(chroma))
    monkeypatch.setenv("AUDIT_DB_PATH", str(audit))
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("CLINICALRAG_MOCK_LLM", "1")
    monkeypatch.setenv("GROQ_API_KEY", "")

    import config

    config.reset_settings_cache()

    try:
        import rag.retriever as retriever

        retriever.reset_client()
    except Exception:
        pass

    try:
        import rag.pipeline as pipeline

        pipeline.reset_pipeline()
    except Exception:
        pass

    import audit.logger as audit_logger  # noqa: F401 (path comes from settings)

    return {"chroma": chroma, "audit": audit}


@pytest.fixture()
def sample_hf_chunk():
    return {
        "content": (
            "SGLT2 Inhibitors (new addition to GDMT, Class I 2022). "
            "Dapagliflozin (Farxiga) 10mg daily or empagliflozin (Jardiance) 10mg daily "
            "reduce risk of CV death and worsening HF regardless of diabetes status."
        ),
        "metadata": {
            "title": "AHA/ACC 2022 Heart Failure Management Guidelines",
            "document_id": "doc-hf",
            "chunk_index": 0,
            "content_hash": "abc123",
        },
        "relevance_score": 0.82,
    }
