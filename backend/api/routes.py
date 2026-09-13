import logging

from fastapi import APIRouter, HTTPException, Request

from api.models import (
    AuditListResponse,
    CollectionStats,
    CollectionsResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    ReadinessResponse,
    SentenceCitation,
    SourceDocument,
)
from api.rate_limit import RateLimiter
from audit.logger import get_recent_audit, init_audit_db, log_query
from config import get_settings
from rag.ingestion import ingest_document
from rag.pipeline import (
    GENERATION_MODEL,
    GRADING_MODEL,
    LLM_PROVIDER,
    groq_configured,
    run_query,
)
from rag.retriever import collection_stats, get_client

logger = logging.getLogger(__name__)
router = APIRouter()
_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(get_settings().rate_limit_per_minute)
    return _limiter


def reset_limiter() -> None:
    global _limiter
    _limiter = None


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest, raw: Request):
    client_host = raw.client.host if raw.client else "unknown"
    if not get_limiter().allow(client_host):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")

    try:
        state, latency_ms = run_query(
            query=request.query,
            collection=request.collection,
            max_sources=request.max_sources,
        )

        sources = [
            SourceDocument(
                title=d["metadata"].get("title", "Unknown"),
                content_excerpt=(
                    d["content"][:300] + "..." if len(d["content"]) > 300 else d["content"]
                ),
                relevance_score=d["relevance_score"],
                document_id=d["metadata"].get("document_id", ""),
                chunk_index=d["metadata"].get("chunk_index"),
                total_chunks=d["metadata"].get("total_chunks"),
                document_type=d["metadata"].get("document_type"),
                source_url=d["metadata"].get("source_url"),
            )
            for d in state.get("relevant_docs") or []
        ]

        answer = state.get("answer") or (
            "I cannot find relevant information in the available guidelines."
        )

        query_id = log_query(
            query=request.query,
            collection=request.collection,
            sources_retrieved=len(sources),
            grounding_score=float(state.get("grounding_score") or 0.0),
            latency_ms=latency_ms,
        )

        citations = [
            SentenceCitation(
                sentence=c.get("sentence", ""),
                source_titles=list(c.get("source_titles") or []),
                grounded=bool(c.get("grounded")),
            )
            for c in state.get("citations") or []
        ]

        logger.info(
            "query_complete",
            extra={
                "event": "query_complete",
                "request_id": query_id,
                "latency_ms": latency_ms,
            },
        )

        return QueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            grounding_score=float(state.get("grounding_score") or 0.0),
            confidence=state.get("confidence") or "low",
            warning=state.get("warning"),
            refusal_reason=state.get("refusal_reason"),
            citations=citations,
            citation_coverage=float(state.get("citation_coverage") or 0.0),
            query_id=query_id,
            latency_ms=latency_ms,
            subqueries=list(state.get("subqueries") or []),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("query_failed", extra={"event": "query_failed"})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(request: IngestRequest):
    try:
        result = ingest_document(
            title=request.title,
            content=request.content,
            document_type=request.document_type,
            source_url=request.source_url or "",
            collection_name=request.collection,
        )
        return IngestResponse(
            document_id=result["document_id"],
            chunks_created=result["chunks_created"],
            collection=request.collection,
            status="success",
        )
    except Exception as e:
        logger.exception("ingest_failed", extra={"event": "ingest_failed"})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health", response_model=HealthResponse)
async def health_endpoint():
    settings = get_settings()
    stats = collection_stats()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        collections=[CollectionStats(**s) for s in stats],
        llm_provider=LLM_PROVIDER,
        llm_configured=groq_configured(),
        mock_llm=settings.mock_llm,
        grading_model=GRADING_MODEL,
        generation_model=GENERATION_MODEL,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_endpoint():
    """Readiness: audit DB reachable and vector store listable."""
    settings = get_settings()
    checks: dict[str, str] = {}
    ready = True

    try:
        init_audit_db()
        get_recent_audit(1)
        checks["audit_db"] = "ok"
    except Exception as exc:  # noqa: BLE001 — surface check failure
        checks["audit_db"] = f"error: {exc}"
        ready = False

    try:
        get_client().list_collections()
        checks["vector_store"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["vector_store"] = f"error: {exc}"
        ready = False

    checks["llm"] = "mock" if settings.mock_llm else ("configured" if groq_configured() else "missing_key")
    # Missing LLM key is degraded but still "ready" for extractive mode.
    status = "ready" if ready else "not_ready"
    if not ready:
        raise HTTPException(status_code=503, detail={"status": status, "checks": checks})
    return ReadinessResponse(status=status, checks=checks, version=settings.app_version)


@router.get("/collections", response_model=CollectionsResponse)
async def collections_endpoint():
    return CollectionsResponse(
        collections=[CollectionStats(**s) for s in collection_stats()]
    )


@router.get("/audit", response_model=AuditListResponse)
async def audit_endpoint():
    entries = get_recent_audit(100)
    # Normalize id -> query_id for the typed model.
    normalized = []
    for entry in entries:
        normalized.append(
            {
                "query_id": entry.get("id") or entry.get("query_id"),
                "timestamp": entry["timestamp"],
                "query_hash": entry["query_hash"],
                "collection": entry["collection"],
                "sources_retrieved": entry["sources_retrieved"],
                "grounding_score": entry["grounding_score"],
                "latency_ms": entry["latency_ms"],
            }
        )
    return AuditListResponse(entries=normalized)
