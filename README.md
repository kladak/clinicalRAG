# ClinicalRAG

Grounded clinical decision support API and physician-facing web console for answering guideline questions from a local clinical document collection.

ClinicalRAG is a portfolio project for Karim Ladak ([github.com/kladak](https://github.com/kladak)). It shows practical Applied AI engineering: query decomposition, retrieval, source-grounded generation, citation fidelity, refusal/hallucination guards, evaluation, audit logging, and a deployment-ready app structure. **Educational / research CDS only — not a medical device, not for real patient care.**

## Screenshot

![ClinicalRAG — Guideline Query Console](docs/screenshot.png)

## Why This Exists

Clinical LLM demos often fail where it matters: they sound confident without showing where an answer came from. ClinicalRAG keeps the model constrained to ingested guideline text, returns source citations (including per-sentence attribution), computes a grounding score, refuses off-topic or ungrounded dosage claims, and records an audit trail without storing raw physician queries.

The UI stays restrained and operational rather than flashy. The interesting work is in the graph.

## Architecture (as implemented)

```text
React physician console
        |
        v
FastAPI /api/v1/query  (+ rate limit, request IDs, typed models)
        |
        v
LangGraph StateGraph
        |
        +--> guard_query
        |       off-topic / non-clinical refusal
        |
        +--> decompose
        |       compound split + clinical term lexicon (no LLM)
        |
        +--> retrieve
        |       multi-query ChromaDB + MiniLM embeddings
        |       deterministic rerank + merge cap
        |
        +--> grade_relevance
        |       Groq llama-3.1-8b-instant  |  MOCK_LLM → score floor
        |
        +--> generate  (or skip on refusal / empty evidence)
        |       Groq llama-3.3-70b-versatile  |  MOCK_LLM → extractive
        |
        +--> evaluate_grounding
        |       sentence attribution + unsupported-dosage check
        |       citation coverage
        v
Answer + citations + refusal_reason + hashed audit log
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for design rationale and production tradeoffs.

## Key Features

- LangGraph pipeline: guard → decompose → retrieve → grade → generate → grounding/citations.
- Deterministic query decomposition for compound clinical questions (offline-friendly).
- Local embeddings (`all-MiniLM-L6-v2`) + ChromaDB persistence.
- Groq generation/grading with a first-class `MOCK_LLM` extractive path for CI.
- Per-sentence citation mapping and hybrid grounding score.
- Refusal guards for off-topic prompts and unsupported dosage claims.
- HIPAA-aware audit logging (query hashes, not raw text).
- FastAPI hardening: Pydantic models, readiness probe, structured logs, in-process rate limit.
- Eval harness + unit/API tests runnable without API keys.
- `docker-compose` one-command local bring-up; GitHub Actions CI.

## Stack

- Backend: Python 3.11, FastAPI, LangGraph, LangChain Groq, ChromaDB, sentence-transformers, SQLite
- Frontend: React 18, Vite, Tailwind CSS v3, Axios
- LLM provider: Groq (optional when `MOCK_LLM=1`)
- Deployment: Railway backend, Vercel frontend; local via Docker Compose

## Repository Layout

```text
backend/
  api/              routes, Pydantic models, rate limiter
  audit/            SQLite audit logger (hashed queries)
  config.py         env-backed settings
  logging_config.py JSON / text logging
  data/             seed clinical guideline content
  rag/              decompose, retrieve, guards, citations, pipeline, evaluator
  tests/            offline unit + API contract tests
  eval_cases.json   regression cases (not clinical validation)
  run_evals.py      harness (--mock/--offline, --json)
frontend/           restrained physician console
docker-compose.yml  backend + frontend local bring-up
.github/workflows/  CI for offline tests
ARCHITECTURE.md     design notes
```

## Local Setup

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
```

Edit `backend/.env`:

```bash
GROQ_API_KEY=your_groq_key_here   # optional if MOCK_LLM=1
CHROMA_PATH=./chroma_db
AUDIT_DB_PATH=./audit.db
MOCK_LLM=0
RATE_LIMIT_PER_MINUTE=30
```

```bash
uvicorn main:app --reload
```

First startup seeds `clinical_guidelines` if empty.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Docker Compose

```bash
# optional: export GROQ_API_KEY=...
docker compose up --build
```

API: `http://localhost:8000` · UI: `http://localhost:5173`

## Demo Script

```text
What SGLT2 inhibitors are recommended for heart failure?
What are the diagnostic criteria for sepsis?
What are first-line treatments for HFrEF?
How should atrial fibrillation stroke risk be assessed?
What anticoagulants are on the WHO Essential Medicines List?
What are first-line treatments for HFrEF? Also which SGLT2 inhibitors are recommended?
```

Point out: short clinical answers, source cards, grounding score, citation coverage, Audit tab (hashes only), API + Groq status in the top bar.

Guardrail tests:

```text
What is the capital of France?
What is the weather in Toronto tomorrow?
```

Expected: refusal / low confidence, `refusal_reason` set, no fabricated clinical answer.

## Tests & Evaluation

Unit / contract tests (no embedding download for the pure-logic suite):

```bash
cd backend
source .venv/bin/activate
pytest -q tests/test_config.py tests/test_guards.py tests/test_decompose.py \
  tests/test_evaluator.py tests/test_citations.py tests/test_rate_limit.py
# API contracts stub retrieval (needs fastapi/httpx from requirements.txt):
pytest -q tests/test_api_unit.py
```

Eval harness:

```bash
# Live path (Groq + seeded Chroma)
python run_evals.py

# Offline extractive path — CI-friendly, no API key
MOCK_LLM=1 python run_evals.py --offline
# alias: python run_evals.py --mock
```

Harness checks are **local regression signals only** — not clinical performance claims, not device validation.

## API Reference

### Liveness / readiness

```bash
curl http://localhost:8000/health | python -m json.tool
curl http://localhost:8000/api/v1/ready | python -m json.tool
```

### Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are first-line treatments for HFrEF?",
    "max_sources": 3,
    "collection": "clinical_guidelines"
  }' | python -m json.tool
```

Response includes `sources`, `grounding_score`, `confidence`, optional `warning` / `refusal_reason`, `citations`, and `citation_coverage`.

### Ingest / audit

Same shapes as before — see `/api/v1/ingest` and `/api/v1/audit`. Raw queries are never stored in the audit DB.

## When ClinicalRAG Should Refuse

- Clearly off-topic (trivia, weather, jokes).
- No relevant guideline chunks after retrieval + grading.
- Post-generation checks find dosage claims absent from retrieved sources.
- Grounding score too low to present as guideline-supported.

Refusal is a product feature. A confident wrong answer is worse than "I cannot find this in the available guidelines."

## Deployment

**Railway (backend):** deploy `backend/`, set `GROQ_API_KEY`, `CHROMA_PATH=/data/chroma_db`, `AUDIT_DB_PATH=/data/audit.db`, mount volume at `/data`.

**Vercel (frontend):** deploy `frontend/`, set `VITE_API_URL` to the Railway URL.

## Limitations

- Not a medical device; not for real patient care.
- Seed corpus is intentionally small.
- In-process rate limiting is demo-grade; multi-replica needs shared limits.
- Chroma local persistence is fine for a portfolio deploy; production needs shared vector storage.
- SQLite audit → PostgreSQL in production.
- Real HIPAA deployments need BAAs, encryption, access control, monitoring, incident response, and formal clinical validation.

## Live Demo Links

- Backend health: add Railway URL after deployment.
- Frontend: add Vercel URL after deployment.
