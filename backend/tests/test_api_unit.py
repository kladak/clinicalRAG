"""API tests that avoid loading sentence-transformers / Chroma when possible."""

from __future__ import annotations

import sys
import types

import pytest

# Lightweight stubs so importing the FastAPI app does not require LangChain/Chroma.
if "langchain_core" not in sys.modules:
    lc = types.ModuleType("langchain_core")
    messages = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content: str = "", **kwargs):
            self.content = content

    messages.HumanMessage = _Msg
    messages.SystemMessage = _Msg
    messages.AIMessage = _Msg
    sys.modules["langchain_core"] = lc
    sys.modules["langchain_core.messages"] = messages

if "langgraph" not in sys.modules:
    lg = types.ModuleType("langgraph")
    graph = types.ModuleType("langgraph.graph")

    class StateGraph:
        def __init__(self, *a, **k):
            pass

        def add_node(self, *a, **k):
            return self

        def add_edge(self, *a, **k):
            return self

        def add_conditional_edges(self, *a, **k):
            return self

        def set_entry_point(self, *a, **k):
            return self

        def compile(self, *a, **k):
            return types.SimpleNamespace(invoke=lambda state: state)

    graph.StateGraph = StateGraph
    graph.END = "END"
    sys.modules["langgraph"] = lg
    sys.modules["langgraph.graph"] = graph

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    pytest.skip("fastapi not installed", allow_module_level=True)


# These contract tests need the app import graph; skip cleanly when heavy deps are absent.
for _mod in ("chromadb", "sentence_transformers"):
    try:
        __import__(_mod)
    except ImportError:
        pytest.skip(f"{_mod} not installed — API contract tests need full backend deps or richer stubs", allow_module_level=True)



@pytest.fixture()
def client(tmp_paths, monkeypatch):
    # Stub retrieval-heavy pipeline entrypoints for pure API contract tests.
    import rag.pipeline as pipeline

    def fake_run_query(query: str, collection: str, max_sources: int):
        if "France" in query:
            state = {
                "answer": "I cannot find this in the available guidelines.",
                "relevant_docs": [],
                "grounding_score": 0.0,
                "confidence": "low",
                "warning": "off topic",
                "refusal_reason": "off_topic",
                "citations": [],
                "citation_coverage": 0.0,
                "subqueries": [],
            }
            return state, 12
        state = {
            "answer": "Based on Heart Failure guidelines: use SGLT2 inhibitors.",
            "relevant_docs": [
                {
                    "content": "Dapagliflozin 10mg daily is recommended for HFrEF.",
                    "metadata": {
                        "title": "AHA/ACC 2022 Heart Failure Management Guidelines",
                        "document_id": "hf1",
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "document_type": "guideline",
                        "source_url": "https://example.org",
                    },
                    "relevance_score": 0.9,
                }
            ],
            "grounding_score": 0.8,
            "confidence": "high",
            "warning": None,
            "refusal_reason": None,
            "citations": [
                {
                    "sentence": "Based on Heart Failure guidelines: use SGLT2 inhibitors.",
                    "source_titles": ["AHA/ACC 2022 Heart Failure Management Guidelines"],
                    "grounded": True,
                }
            ],
            "citation_coverage": 1.0,
            "subqueries": [],
        }
        return state, 25

    monkeypatch.setattr(pipeline, "run_query", fake_run_query)
    monkeypatch.setattr(pipeline, "groq_configured", lambda: False)

    import rag.retriever as retriever

    monkeypatch.setattr(retriever, "collection_stats", lambda: [{"name": "clinical_guidelines", "document_count": 3}])
    monkeypatch.setattr(retriever, "get_client", lambda: type("C", (), {"list_collections": lambda self: []})())

    # Avoid seed/chroma on startup
    import data.seed_data as seed_data

    monkeypatch.setattr(seed_data, "seed_if_empty", lambda: None)

    import audit.logger as audit_logger

    audit_logger.init_audit_db()

    import main as main_module

    # Rebuild limiter against tmp settings
    import api.routes as routes

    routes.reset_limiter()

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body.get("mock_llm") is True


def test_query_contract(client):
    response = client.post(
        "/api/v1/query",
        json={"query": "What SGLT2 inhibitors are recommended for heart failure?", "max_sources": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "high"
    assert body["sources"]
    assert body["citations"]
    assert "query_id" in body
    assert response.headers.get("X-Request-Id")


def test_query_refusal(client):
    response = client.post(
        "/api/v1/query",
        json={"query": "What is the capital of France today please?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refusal_reason"] == "off_topic"
    assert body["grounding_score"] == 0.0


def test_ready(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
