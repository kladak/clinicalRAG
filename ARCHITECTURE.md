# ClinicalRAG Architecture

ClinicalRAG is designed as grounded educational clinical decision support, not a general chatbot and **not a medical device**. The product requirement is not fluency alone: retrieve relevant guideline material, constrain generation to that material, show which sources were used (including per-sentence attribution), refuse when evidence is missing or answers invent dosages, and leave a privacy-conscious audit trail.

## Pipeline shape (LangGraph)

The request state carries the original query, collection, max sources, decomposed subqueries / clinical terms, retrieved and relevance-filtered docs, answer, grounding score, confidence, warning, `refusal_reason`, citations, citation coverage, query id, and timing.

Nodes, in order:

1. **guard_query** — deterministic off-topic / non-clinical refusal before any embedding work.
2. **decompose** — split compound questions and extract a small clinical lexicon; no LLM required.
3. **retrieve** — embed up to a few retrieval variants, merge by content hash, deterministic token/title rerank, hard-cap merge window.
4. **grade_relevance** — Groq YES/NO grader, or score-floor fallback under `MOCK_LLM` / missing key.
5. **generate** — Groq grounded generation, or extractive sentence selection offline.
6. **evaluate_grounding** — sentence-level attribution, unsupported-dosage faithfulness check, citation coverage.

Conditional edges skip generation when the guard fired or no relevant docs remain.

## Why LangGraph

A linear chain is enough for a toy RAG demo. ClinicalRAG needs inspectable stages and early exits: refuse before retrieve, skip generate when evidence is empty, and attach citation metadata after scoring. The graph leaves room for future nodes (PHI detection, specialty routing, human review) without rewriting the API.

## Query decomposition & retrieval

Decomposition is deliberately boring and deterministic. Compound physician questions ("HFrEF first-line therapy and which SGLT2 inhibitors?") should not depend on a second model call just to retrieve well. Subqueries plus a clinical-term boost query are embedded independently; results merge with a capped window so weakly related chunks do not drown the best paragraph. A small token/title reranker keeps ordering transparent.

## Citation fidelity & grounding

Cosine similarity is for retrieval, not attribution. The evaluator checks whether each answer sentence can be tied to a source chunk via exact n-gram overlap or normalized content-token overlap. Separately, `rag/citations.py` maps sentences to source titles for the API. Low grounding triggers warnings; unsupported dosage strings that never appear in retrieved text trigger refusal.

These are engineering signals for demos and regression tests — **not** clinical validation.

## Refusal / dosage heuristics

`rag/guards.py` encodes product policy:

- Off-topic patterns (capitals, weather, jokes) refuse immediately.
- Queries with no clinical lexicon/intent refuse as non-clinical.
- Answers that introduce `mg`/`mcg`/etc. claims absent from sources are refused rather than shown.

## MOCK_LLM path

`MOCK_LLM=1` (or `CLINICALRAG_MOCK_LLM`) disables Groq, forces extractive answers, and keeps evals/CI offline. The same graph runs; only the LLM-backed nodes swap behavior. This is how the portfolio stays demoable without leaking keys into CI.

## FastAPI hardening

- Central `config.Settings` for paths, models, thresholds, rate limits.
- Structured JSON logging without raw query text; `X-Request-Id` on responses.
- Typed request/response models including `refusal_reason` and `citations`.
- In-process fixed-window rate limit on `/query` (single-instance demo).
- `/health` liveness vs `/api/v1/ready` readiness (audit DB + vector store listable).

## Query-hash audit (not HIPAA certification)

Audit rows store SHA-256(query), collection, source count, grounding score, latency, timestamp, and id — not the physician's text. This is privacy-minimizing demo hygiene, not a HIPAA compliance claim. Production PHI handling still needs BAAs, encryption, access control, retention policy, and incident response. Ingest/audit HTTP routes are unauthenticated in this demo.

## Why ChromaDB

Portable, low-cost, disk-persisted. The retrieval contract is narrow (`query → ranked docs + metadata + distances`) so a later move to Pinecone/Qdrant/pgvector does not rewrite the graph.

## Production scaling notes

- SQLite audit → PostgreSQL with indexes on timestamp / query hash.
- Shared rate limits and query cache (Redis) once horizontally scaled.
- Async ingestion workers for large protocol libraries; do not block API workers.
- Shared vector store when running multiple API replicas.
- Replace in-process limiter and local Chroma volume accordingly.

## Evaluation philosophy

`eval_cases.json` + `run_evals.py` are regression checks against the seed corpus (expected sources/terms, grounding floors, refusal cases, compound decomposition). `--offline` / `--mock` runs the extractive path. Numbers are local signals only — never present them as clinical accuracy, sensitivity, or device performance.
