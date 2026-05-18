from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)
    max_sources: int = Field(default=3, ge=1, le=10)
    collection: str = Field(default="clinical_guidelines")


class SourceDocument(BaseModel):
    title: str
    content_excerpt: str
    relevance_score: float
    document_id: str
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    document_type: Optional[str] = None
    source_url: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceDocument]
    grounding_score: float
    confidence: str
    warning: Optional[str] = None
    query_id: str
    latency_ms: int


class IngestRequest(BaseModel):
    title: str
    content: str
    document_type: str = Field(..., pattern="^(guideline|protocol|drug_label|fhir)$")
    source_url: Optional[str] = None
    collection: str = Field(default="clinical_guidelines")


class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int
    collection: str
    status: str


class AuditEntry(BaseModel):
    query_id: str
    timestamp: datetime
    query_hash: str
    collection: str
    sources_retrieved: int
    grounding_score: float
    latency_ms: int


class CollectionStats(BaseModel):
    name: str
    document_count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    collections: List[CollectionStats]
    llm_provider: str
    llm_configured: bool
    grading_model: str
    generation_model: str
