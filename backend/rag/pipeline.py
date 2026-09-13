import hashlib
import logging
import re
import time
import uuid
from typing import List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from config import get_settings
from rag.citations import annotate_citations, citation_coverage
from rag.decompose import DecomposedQuery, decompose_query
from rag.evaluator import compute_grounding_score
from rag.guards import (
    REFUSAL_ANSWER,
    check_answer_faithfulness,
    check_off_topic,
)
from rag.retriever import retrieve

logger = logging.getLogger(__name__)

_grader = None
_generator = None

# Re-exported for routes/health that still import these names.
LLM_PROVIDER = "groq"


# Module-level labels refreshed from settings for backward-compatible imports.
GRADING_MODEL = "llama-3.1-8b-instant"
GENERATION_MODEL = "llama-3.3-70b-versatile"


def _refresh_model_labels() -> None:
    global GRADING_MODEL, GENERATION_MODEL
    settings = get_settings()
    GRADING_MODEL = settings.grading_model
    GENERATION_MODEL = settings.generation_model


_refresh_model_labels()


def groq_configured() -> bool:
    return get_settings().groq_configured


def get_grader():
    global _grader
    if _grader is None:
        from langchain_groq import ChatGroq

        settings = get_settings()
        _grader = ChatGroq(
            model=settings.grading_model,
            api_key=settings.groq_api_key,
            max_tokens=256,
        )
    return _grader


def get_generator():
    global _generator
    if _generator is None:
        from langchain_groq import ChatGroq

        settings = get_settings()
        _generator = ChatGroq(
            model=settings.generation_model,
            api_key=settings.groq_api_key,
            max_tokens=1024,
        )
    return _generator


def _query_tokens(text: str) -> set[str]:
    stopwords = {
        "about",
        "after",
        "also",
        "and",
        "are",
        "for",
        "from",
        "how",
        "into",
        "list",
        "onto",
        "the",
        "this",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) >= 3 and token not in stopwords
    }


def _rerank_score(query: str, doc: dict) -> float:
    query_tokens = _query_tokens(query)
    text = f"{doc['metadata'].get('title', '')} {doc['content']}".lower()
    text_tokens = set(re.findall(r"[a-zA-Z0-9]+", text))

    token_overlap = len(query_tokens & text_tokens)
    exact_bonus = sum(1 for token in query_tokens if token in text)
    title_bonus = sum(
        1 for token in query_tokens if token in doc["metadata"].get("title", "").lower()
    )

    return (
        doc.get("relevance_score", 0.0)
        + (0.08 * token_overlap)
        + (0.04 * exact_bonus)
        + (0.06 * title_bonus)
    )


def _doc_key(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    if meta.get("content_hash"):
        return str(meta["content_hash"])
    if meta.get("document_id") is not None and meta.get("chunk_index") is not None:
        return f"{meta['document_id']}:{meta['chunk_index']}"
    return hashlib.sha256(doc.get("content", "").encode()).hexdigest()


class RAGState(TypedDict):
    query: str
    collection: str
    max_sources: int
    subqueries: List[str]
    clinical_terms: List[str]
    retrieved_docs: List[dict]
    relevant_docs: List[dict]
    answer: str
    grounding_score: float
    confidence: str
    warning: Optional[str]
    refusal_reason: Optional[str]
    citations: List[dict]
    citation_coverage: float
    query_id: str
    start_time: float


def guard_query_node(state: RAGState) -> RAGState:
    decision = check_off_topic(state["query"])
    if not decision.allow:
        logger.info(
            "query_refused",
            extra={"event": "query_refused", "request_id": state.get("query_id")},
        )
        return {
            **state,
            "relevant_docs": [],
            "retrieved_docs": [],
            "answer": REFUSAL_ANSWER,
            "warning": decision.reason,
            "refusal_reason": decision.code,
            "grounding_score": 0.0,
            "confidence": "low",
            "citations": [],
            "citation_coverage": 0.0,
        }
    return state


def decompose_node(state: RAGState) -> RAGState:
    if state.get("refusal_reason"):
        return state
    decomposed: DecomposedQuery = decompose_query(state["query"])
    return {
        **state,
        "subqueries": decomposed.subqueries,
        "clinical_terms": decomposed.clinical_terms,
    }


def retrieve_node(state: RAGState) -> RAGState:
    if state.get("refusal_reason"):
        return state

    settings = get_settings()
    # Tightened after compound queries flooded the source list with weak neighbors.
    # Keep a small overfetch for multi-query merge, then hard-cap to max_sources*2.
    overfetch = settings.retrieval_overfetch
    merge_limit = min(max(state["max_sources"] * 2, state["max_sources"] + overfetch), 8)

    decomposed = decompose_query(state["query"])
    queries = decomposed.retrieval_queries[:3] or [state["query"]]

    merged: dict[str, dict] = {}
    for q in queries:
        results = retrieve(q, state["collection"], k=state["max_sources"] + overfetch)
        if not results["documents"] or not results["documents"][0]:
            continue
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            item = {
                "content": doc,
                "metadata": meta,
                "relevance_score": round(1 - dist, 3),
            }
            key = _doc_key(item)
            prior = merged.get(key)
            if prior is None or item["relevance_score"] > prior["relevance_score"]:
                merged[key] = item

    docs = list(merged.values())
    docs.sort(key=lambda item: _rerank_score(state["query"], item), reverse=True)
    docs = docs[:merge_limit]
    return {**state, "retrieved_docs": docs}


def fallback_relevance(state: RAGState) -> RAGState:
    settings = get_settings()
    relevant_docs = [
        doc
        for doc in state["retrieved_docs"]
        if doc.get("relevance_score", 0) >= settings.relevance_floor
    ][: state["max_sources"]]
    if relevant_docs:
        return {
            **state,
            "relevant_docs": relevant_docs,
            "warning": state.get("warning"),
        }
    return {
        **state,
        "relevant_docs": [],
        "warning": (
            "No relevant guidelines found for this query. "
            "Please verify with primary clinical sources."
        ),
        "refusal_reason": state.get("refusal_reason") or "no_relevant_docs",
    }


def grade_relevance_node(state: RAGState) -> RAGState:
    if state.get("refusal_reason") and not state.get("retrieved_docs"):
        return state

    if not state["retrieved_docs"]:
        return {
            **state,
            "relevant_docs": [],
            "warning": "No documents in collection.",
            "refusal_reason": "empty_collection",
        }

    settings = get_settings()
    if settings.mock_llm or not groq_configured():
        return fallback_relevance(state)

    docs_text = "\n\n".join(
        [
            f"Document: {d['metadata'].get('title', '')}\n{d['content']}"
            for d in state["retrieved_docs"][:3]
        ]
    )

    prompt = f"""You are grading whether retrieved documents are relevant to a clinical query.

Query: {state["query"]}

Retrieved documents:
{docs_text}

Are these documents relevant to answering the query? Reply with only YES or NO."""

    try:
        response = get_grader().invoke([HumanMessage(content=prompt)])
        relevant = "YES" in response.content.upper()
    except Exception:
        return fallback_relevance(state)

    if relevant:
        return {
            **state,
            "relevant_docs": state["retrieved_docs"][: state["max_sources"]],
        }

    return {
        **state,
        "relevant_docs": [],
        "warning": (
            "No relevant guidelines found for this query. "
            "Please verify with primary clinical sources."
        ),
        "refusal_reason": "graded_irrelevant",
    }


def extractive_answer(state: RAGState) -> str:
    query_terms = {
        word
        for word in re.findall(r"[a-zA-Z0-9]+", state["query"].lower())
        if len(word) > 3
    }
    # Prefer clinical terms from decomposition when present.
    for term in state.get("clinical_terms") or []:
        query_terms.add(term.lower())

    selected = []

    for doc in state["relevant_docs"]:
        sentences = re.split(r"(?<=[.!?])\s+", doc["content"].strip())
        ranked = sorted(
            sentences,
            key=lambda sentence: sum(1 for term in query_terms if term in sentence.lower()),
            reverse=True,
        )
        for sentence in ranked:
            if len(sentence.strip()) > 40 and sentence.strip() not in selected:
                selected.append(sentence.strip())
            if len(selected) >= 5:
                break
        if len(selected) >= 5:
            break

    if not selected and state["relevant_docs"]:
        selected = [state["relevant_docs"][0]["content"].split("\n")[0].strip()]

    title = state["relevant_docs"][0]["metadata"].get("title", "the retrieved guideline")
    bullets = "\n".join([f"- {sentence}" for sentence in selected[:5]])
    return f"Based on {title}:\n{bullets}"


def generate_node(state: RAGState) -> RAGState:
    if state.get("refusal_reason") and not state.get("relevant_docs"):
        if not state.get("answer"):
            return {**state, "answer": REFUSAL_ANSWER}
        return state

    if not state["relevant_docs"]:
        return {**state, "answer": ""}

    context = "\n\n---\n\n".join(
        [
            f"[{d['metadata'].get('title', 'Unknown')}]\n{d['content']}"
            for d in state["relevant_docs"]
        ]
    )

    system = """You are a clinical decision support assistant. Your role is to answer physician queries based strictly on the provided clinical guidelines.

CRITICAL RULES:
1. Answer ONLY using information from the provided context
2. If the answer is not in the context, say exactly: "I cannot find this in the available guidelines."
3. Never speculate or use outside knowledge
4. Always cite which guideline your answer comes from
5. Be precise with drug names, dosages, and clinical criteria
6. Do not invent dosages that are not explicitly present in the context"""

    human = f"""Clinical guidelines context:
{context}

Physician query: {state["query"]}

Answer based only on the guidelines above:"""

    settings = get_settings()
    if settings.mock_llm or not groq_configured():
        warning = state.get("warning")
        if settings.mock_llm and not warning:
            warning = "Running in MOCK_LLM mode; returning an extractive answer from retrieved guidelines."
        elif not warning:
            warning = (
                "Groq API key is not configured; returning an extractive answer "
                "from retrieved guidelines."
            )
        return {**state, "answer": extractive_answer(state), "warning": warning}

    try:
        response = get_generator().invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=human),
            ]
        )
        return {**state, "answer": response.content}
    except Exception:
        warning = state.get("warning")
        if not warning:
            warning = (
                "Generation service was unavailable; returning an extractive answer "
                "from retrieved guidelines."
            )
        return {**state, "answer": extractive_answer(state), "warning": warning}


def evaluate_grounding_node(state: RAGState) -> RAGState:
    settings = get_settings()

    if state.get("refusal_reason") and not state.get("relevant_docs"):
        return {
            **state,
            "grounding_score": 0.0,
            "confidence": "low",
            "citations": [],
            "citation_coverage": 0.0,
            "answer": state.get("answer") or REFUSAL_ANSWER,
        }

    if not state["answer"] or not state["relevant_docs"]:
        return {
            **state,
            "grounding_score": 0.0,
            "confidence": "low",
            "citations": [],
            "citation_coverage": 0.0,
        }

    source_texts = [d["content"] for d in state["relevant_docs"]]
    faithfulness = check_answer_faithfulness(state["answer"], source_texts)
    answer = state["answer"]
    warning = state.get("warning")
    refusal_reason = state.get("refusal_reason")

    if not faithfulness.allow:
        answer = REFUSAL_ANSWER
        warning = faithfulness.reason
        refusal_reason = faithfulness.code
        return {
            **state,
            "answer": answer,
            "grounding_score": 0.0,
            "confidence": "low",
            "warning": warning,
            "refusal_reason": refusal_reason,
            "citations": [],
            "citation_coverage": 0.0,
            "relevant_docs": [],
        }

    score = compute_grounding_score(answer, source_texts)
    citations = annotate_citations(answer, state["relevant_docs"])
    coverage = citation_coverage(citations)

    if score >= settings.high_grounding_threshold:
        confidence = "high"
    elif score >= settings.medium_grounding_threshold:
        confidence = "medium"
    else:
        confidence = "low"

    if score < settings.low_grounding_warn_threshold and not warning:
        warning = (
            "This response may not be fully grounded in available guidelines. "
            "Please verify with primary sources."
        )

    return {
        **state,
        "answer": answer,
        "grounding_score": score,
        "confidence": confidence,
        "warning": warning,
        "refusal_reason": refusal_reason,
        "citations": [
            {
                "sentence": c.sentence,
                "source_titles": c.source_titles,
                "grounded": c.grounded,
            }
            for c in citations
        ],
        "citation_coverage": coverage,
    }


def should_generate(state: RAGState) -> str:
    if state.get("refusal_reason") and not state.get("relevant_docs"):
        return "evaluate_grounding"
    if state["relevant_docs"]:
        return "generate"
    return "evaluate_grounding"


def should_retrieve(state: RAGState) -> str:
    if state.get("refusal_reason"):
        return "evaluate_grounding"
    return "decompose"


def build_pipeline():
    graph = StateGraph(RAGState)
    graph.add_node("guard_query", guard_query_node)
    graph.add_node("decompose", decompose_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade_relevance", grade_relevance_node)
    graph.add_node("generate", generate_node)
    graph.add_node("evaluate_grounding", evaluate_grounding_node)

    graph.set_entry_point("guard_query")
    graph.add_conditional_edges(
        "guard_query",
        should_retrieve,
        {
            "decompose": "decompose",
            "evaluate_grounding": "evaluate_grounding",
        },
    )
    graph.add_edge("decompose", "retrieve")
    graph.add_edge("retrieve", "grade_relevance")
    graph.add_conditional_edges(
        "grade_relevance",
        should_generate,
        {
            "generate": "generate",
            "evaluate_grounding": "evaluate_grounding",
        },
    )
    graph.add_edge("generate", "evaluate_grounding")
    graph.add_edge("evaluate_grounding", END)

    return graph.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def reset_pipeline() -> None:
    """Test helper — drop compiled graph after settings changes."""
    global _pipeline, _grader, _generator
    _pipeline = None
    _grader = None
    _generator = None


def run_query(query: str, collection: str, max_sources: int) -> tuple[RAGState, int]:
    start = time.time()
    initial_state: RAGState = {
        "query": query,
        "collection": collection,
        "max_sources": max_sources,
        "subqueries": [],
        "clinical_terms": [],
        "retrieved_docs": [],
        "relevant_docs": [],
        "answer": "",
        "grounding_score": 0.0,
        "confidence": "low",
        "warning": None,
        "refusal_reason": None,
        "citations": [],
        "citation_coverage": 0.0,
        "query_id": str(uuid.uuid4()),
        "start_time": start,
    }
    result = get_pipeline().invoke(initial_state)
    latency_ms = int((time.time() - start) * 1000)
    return result, latency_ms
