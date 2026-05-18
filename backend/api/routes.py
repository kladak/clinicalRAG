from fastapi import APIRouter, HTTPException

from api.models import (
    CollectionStats,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceDocument,
)
from audit.logger import get_recent_audit, log_query
from rag.ingestion import ingest_document
from rag.pipeline import (
    GENERATION_MODEL,
    GRADING_MODEL,
    LLM_PROVIDER,
    groq_configured,
    run_query,
)
from rag.retriever import collection_stats

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
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
            for d in state["relevant_docs"]
        ]

        answer = state["answer"] or "I cannot find relevant information in the available guidelines."

        query_id = log_query(
            query=request.query,
            collection=request.collection,
            sources_retrieved=len(sources),
            grounding_score=state["grounding_score"],
            latency_ms=latency_ms,
        )

        return QueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            grounding_score=state["grounding_score"],
            confidence=state["confidence"],
            warning=state.get("warning"),
            query_id=query_id,
            latency_ms=latency_ms,
        )
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health", response_model=HealthResponse)
async def health_endpoint():
    stats = collection_stats()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        collections=[CollectionStats(**s) for s in stats],
        llm_provider=LLM_PROVIDER,
        llm_configured=groq_configured(),
        grading_model=GRADING_MODEL,
        generation_model=GENERATION_MODEL,
    )


@router.get("/collections")
async def collections_endpoint():
    return {"collections": collection_stats()}


@router.get("/audit")
async def audit_endpoint():
    return {"entries": get_recent_audit(100)}
