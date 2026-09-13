"""Shared fixtures. Keep heavy ML deps out of unit tests when possible."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Ensure backend package imports resolve when pytest is run from repo root or backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MOCK_LLM", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


@pytest.fixture()
def tmp_paths(monkeypatch, tmp_path):
    chroma = tmp_path / "chroma"
    audit = tmp_path / "audit.db"
    chroma.mkdir()
    monkeypatch.setenv("CHROMA_PATH", str(chroma))
    monkeypatch.setenv("AUDIT_DB_PATH", str(audit))
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("GROQ_API_KEY", "")
    # Reset module-level singletons that cache paths
    import config

    config.reset_settings_cache()
    import rag.retriever as retriever

    retriever._client = None
    retriever.CHROMA_PATH = str(chroma)
    import audit.logger as audit_logger

    audit_logger.DB_PATH = str(audit)
    return {"chroma": chroma, "audit": audit}
