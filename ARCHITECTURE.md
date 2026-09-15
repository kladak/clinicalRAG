# ClinicalRAG Architecture

The pipeline retrieves relevant guideline material, constrains generation to that material, reports which sources were used with per-sentence attribution, refuses when evidence is missing or an answer invents a dosage, and writes an audit trail keyed on a query hash.

## Pipeline shape (LangGraph)

The request state carries the original query, collection, max sources, decomposed subqueries / clinical terms, retrieved and relevance-filtered docs, answer, grounding score, confidence, warning, `refusal_reason`, citations, citation coverage, query id, and timing.

Nodes, in order:

1. **guard_query**: deterministic off-topic refusal before any embedding work.
2. **decompose**: split compound questions and extract a small clinical lexicon; no LLM required.
3. **retrieve**: embed a few retrieval variants, merge by content hash, rerank deterministically on tokens and title, hard-cap the merge window.
4. **grade_relevance**: Groq YES/NO grader, or a score-floor fallback under `MOCK_LLM` or a missing key.
5. **generate**: Groq grounded generation, or extractive sentence selection offline.
6. **evaluate_grounding**: sentence-level attribution, unsupported-dosage faithfulness check, citation coverage.

Conditional edges skip generation when the guard fired or no relevant docs remain.

## Why LangGraph

A linear chain is enough for a toy RAG demo. ClinicalRAG needs inspectable stages and early exits: refuse before retrieve, skip generate when evidence is empty, and attach citation metadata after scoring. The graph leaves room for future nodes (PHI detection, specialty routing, human review) without rewriting the API.

## Query decomposition & retrieval

Decomposition is deliberately boring and deterministic. Compound physician questions ("HFrEF first-line therapy and which SGLT2 inhibitors?") should not depend on a second model call just to retrieve well. Subqueries plus a clinical-term boost query are embedded independently; results merge with a capped window so weakly related chunks do not drown the best paragraph. A small token/title reranker fixes the ordering.

## Citation fidelity & grounding

Cosine similarity is for retrieval, not attribution. The evaluator checks whether each answer sentence can be tied to a source chunk via exact n-gram overlap or normalized content-token overlap. Separately, `rag/citations.py` maps sentences to source titles for the API. Low grounding triggers warnings; unsupported dosage strings that never appear in retrieved text trigger refusal.

These thresholds are tuned against the seed corpus and pinned by the eval harness.

## Refusal / dosage heuristics

`rag/guards.py` encodes product policy:

- Off-topic patterns (capitals, weather, jokes) refuse immediately.
- Queries with no clinical lexicon/intent refuse as non-clinical.
- Answers that introduce `mg`/`mcg` claims absent from the sources are refused.

## MOCK_LLM path

`MOCK_LLM=1` (or `CLINICALRAG_MOCK_LLM`) disables Groq, forces extractive answers, and keeps evals/CI offline. The same graph runs; only the LLM-backed nodes swap behavior. This is how the project stays runnable end to end without putting a key in CI.

## FastAPI hardening

- Central `config.Settings` for paths, models, thresholds, rate limits.
- Structured JSON logging without raw query text; `X-Request-Id` on responses.
- Typed request/response models including `refusal_reason` and `citations`.
- In-process fixed-window rate limit on `/query` (single-instance demo).
- `/health` should be process liveness (no Chroma). `/api/v1/ready` is readiness (audit DB + vector store). Root `/ready` is removed/aliased to real readiness.

## Query-hash audit

Audit rows store SHA-256(query), collection, source count, grounding score, latency, timestamp and id. Production PHI handling would additionally require BAAs, encryption, access control, a retention policy and incident response. The ingest and audit routes are unauthenticated here.

## Why ChromaDB

Portable, low-cost, disk-persisted. The retrieval contract is narrow (`query → ranked docs + metadata + distances`) so a later move to Pinecone/Qdrant/pgvector does not rewrite the graph.

## Production scaling notes

- SQLite audit → PostgreSQL with indexes on timestamp / query hash.
- Shared rate limits and query cache (Redis) once horizontally scaled.
- Async ingestion workers for large protocol libraries; do not block API workers.
- Shared vector store when running multiple API replicas.
- Replace in-process limiter and local Chroma volume accordingly.

## Evaluation philosophy

`eval_cases.json` and `run_evals.py` are regression checks against the seed corpus: expected sources and terms, grounding floors, refusal cases, compound decomposition. `--offline` (or `--mock`) runs the extractive path. The numbers pin behaviour on the seed corpus.
