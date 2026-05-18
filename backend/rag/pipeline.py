import os
import re
import time
import uuid
from typing import List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from rag.evaluator import compute_grounding_score
from rag.retriever import retrieve

_grader = None
_generator = None
LLM_PROVIDER = "groq"
GRADING_MODEL = "llama-3.1-8b-instant"
GENERATION_MODEL = "llama-3.3-70b-versatile"


def groq_configured() -> bool:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return bool(key and key != "your_key_here")


def get_grader():
    global _grader
    if _grader is None:
        _grader = ChatGroq(
            model=GRADING_MODEL,
            api_key=os.getenv("GROQ_API_KEY"),
            max_tokens=256,
        )
    return _grader


def get_generator():
    global _generator
    if _generator is None:
        _generator = ChatGroq(
            model=GENERATION_MODEL,
            api_key=os.getenv("GROQ_API_KEY"),
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
    title_bonus = sum(1 for token in query_tokens if token in doc["metadata"].get("title", "").lower())

    return (
        doc.get("relevance_score", 0.0)
        + (0.08 * token_overlap)
        + (0.04 * exact_bonus)
        + (0.06 * title_bonus)
    )


class RAGState(TypedDict):
    query: str
    collection: str
    max_sources: int
    retrieved_docs: List[dict]
    relevant_docs: List[dict]
    answer: str
    grounding_score: float
    confidence: str
    warning: Optional[str]
    query_id: str
    start_time: float


def retrieve_node(state: RAGState) -> RAGState:
    results = retrieve(state["query"], state["collection"], k=state["max_sources"] + 2)
    docs = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            docs.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "relevance_score": round(1 - dist, 3),
                }
            )
    docs.sort(key=lambda item: _rerank_score(state["query"], item), reverse=True)
    return {**state, "retrieved_docs": docs}


def fallback_relevance(state: RAGState) -> RAGState:
    relevant_docs = [
        doc for doc in state["retrieved_docs"] if doc.get("relevance_score", 0) >= 0.2
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
        "warning": "No relevant guidelines found for this query. Please verify with primary clinical sources.",
    }


def grade_relevance_node(state: RAGState) -> RAGState:
    if not state["retrieved_docs"]:
        return {**state, "relevant_docs": [], "warning": "No documents in collection."}

    if not groq_configured():
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
        return {**state, "relevant_docs": state["retrieved_docs"][: state["max_sources"]]}

    return {
        **state,
        "relevant_docs": [],
        "warning": "No relevant guidelines found for this query. Please verify with primary clinical sources.",
    }


def extractive_answer(state: RAGState) -> str:
    query_terms = {
        word
        for word in re.findall(r"[a-zA-Z0-9]+", state["query"].lower())
        if len(word) > 3
    }
    selected = []

    for doc in state["relevant_docs"]:
        sentences = re.split(r"(?<=[.!?])\s+", doc["content"].strip())
        ranked = sorted(
            sentences,
            key=lambda sentence: sum(
                1 for term in query_terms if term in sentence.lower()
            ),
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
5. Be precise with drug names, dosages, and clinical criteria"""

    human = f"""Clinical guidelines context:
{context}

Physician query: {state["query"]}

Answer based only on the guidelines above:"""

    if not groq_configured():
        warning = state.get("warning")
        if not warning:
            warning = "Groq API key is not configured; returning an extractive answer from retrieved guidelines."
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
            warning = "Generation service was unavailable; returning an extractive answer from retrieved guidelines."
        return {**state, "answer": extractive_answer(state), "warning": warning}


def evaluate_grounding_node(state: RAGState) -> RAGState:
    if not state["answer"] or not state["relevant_docs"]:
        return {**state, "grounding_score": 0.0, "confidence": "low"}

    source_texts = [d["content"] for d in state["relevant_docs"]]
    score = compute_grounding_score(state["answer"], source_texts)

    if score >= 0.7:
        confidence = "high"
    elif score >= 0.4:
        confidence = "medium"
    else:
        confidence = "low"

    warning = state.get("warning")
    if score < 0.5 and not warning:
        warning = "This response may not be fully grounded in available guidelines. Please verify with primary sources."

    return {
        **state,
        "grounding_score": score,
        "confidence": confidence,
        "warning": warning,
    }


def should_generate(state: RAGState) -> str:
    if state["relevant_docs"]:
        return "generate"
    return "evaluate_grounding"


def build_pipeline():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade_relevance", grade_relevance_node)
    graph.add_node("generate", generate_node)
    graph.add_node("evaluate_grounding", evaluate_grounding_node)

    graph.set_entry_point("retrieve")
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


def run_query(query: str, collection: str, max_sources: int) -> tuple[RAGState, int]:
    start = time.time()
    initial_state: RAGState = {
        "query": query,
        "collection": collection,
        "max_sources": max_sources,
        "retrieved_docs": [],
        "relevant_docs": [],
        "answer": "",
        "grounding_score": 0.0,
        "confidence": "low",
        "warning": None,
        "query_id": str(uuid.uuid4()),
        "start_time": start,
    }
    result = get_pipeline().invoke(initial_state)
    latency_ms = int((time.time() - start) * 1000)
    return result, latency_ms
