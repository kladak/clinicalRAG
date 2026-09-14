# ClinicalRAG

![ClinicalRAG — Guideline Query Console](docs/screenshot.png)

Grounded clinical Q&A over a local guideline corpus — citations, grounding checks, and refusals when evidence is missing.

**Educational / research CDS only — not a medical device, not for real patient care.**

## Try the demo

<!-- DEMO_URL -->
**Frontend (Vercel):** [https://clinicalrag-three.vercel.app](https://clinicalrag-three.vercel.app)

_UI is live. **API URL pending** — backend not deployed yet (Railway CLI auth required; code still waiting on deploy box). Until `VITE_API_URL` points at a live mock API (`MOCK_LLM=1`, `ENABLE_INGEST=0`), queries will not reach a public backend. Hosting: [docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md)._

## Run locally

```bash
# Backend (mock LLM — no GROQ_API_KEY required)
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
# set MOCK_LLM=1 in .env (optional: ENABLE_INGEST=1 for local corpus writes)
MOCK_LLM=1 uvicorn main:app --reload
```

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Or: `MOCK_LLM=1 docker compose up --build` → API `:8000`, UI `:5173`.

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
- Per-sentence source attribution (content-token overlap) plus a separate hybrid grounding score.
- Heuristic refusal for off-topic prompts and unsupported dosage strings (not a general faithfulness model).
- Query-hash audit logging (no raw query storage) — privacy-minimizing, not a HIPAA compliance claim.
- FastAPI hardening: Pydantic models, readiness probe, structured logs, in-process rate limit.
- Eval harness + unit/API tests runnable without API keys.
- `docker-compose` local bring-up; GitHub Actions runs the lean offline unit suite (evals/compose verified locally).

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

## Local Setup (detail)

Quick start is under **Run locally** above. Full options:

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
- (Low grounding does **not** hard-refuse today — it returns the answer with `confidence=low` and a warning. Off-topic / empty evidence / unsupported dosage do refuse.)

Refusal is a product feature. A confident wrong answer is worse than "I cannot find this in the available guidelines."

## Deployment

Public **mock recruiter** demo (recommended for portfolio): **no Groq key** — see **[docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md)** for exact Railway + Vercel env vars (`MOCK_LLM=1`, `ENABLE_INGEST=0`, `CORS_ORIGINS`, `VITE_API_URL`).

Live Groq path (optional): Railway `backend/` with `MOCK_LLM=0` + `GROQ_API_KEY`, volume at `/data` (`CHROMA_PATH=/data/chroma_db`, `AUDIT_DB_PATH=/data/audit.db`); Vercel `frontend/` with `VITE_API_URL` pointing at Railway.

## Verification (2026-09-13)

Local gates run on this branch (MOCK_LLM / extractive path unless noted):

- `pytest`: **23 passed**
- `python run_evals.py --offline --json` with Chroma + sentence-transformers: **10/10** cases passed (regression signal only — not clinical accuracy)
- Native uvicorn smoke: `/health`, `/api/v1/ready`, clinical query, off-topic refusal
- `docker compose` backend: healthy; sepsis query grounded; France refused as `off_topic`
- Frontend: `npm run build` succeeded
- GitHub Actions `backend-tests` / `unit`: success on PR branch

Do not quote these as clinical performance metrics.

## Limitations

- `/api/v1/ingest` and `/api/v1/audit` are **unauthenticated** demo endpoints. Fine for localhost; public mock deploys must set `ENABLE_INGEST=0` and prefer a locked `CORS_ORIGINS` (see [docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md)). Compose defaults `CORS_ORIGINS=*`.

- Not a medical device; not for real patient care.
- Seed corpus is intentionally small.
- In-process rate limiting is demo-grade; multi-replica needs shared limits.
- Chroma local persistence is suitable for a local/demo deploy; shared vector storage is required for multi-instance production.
- SQLite audit → PostgreSQL in production.
- Real HIPAA deployments need BAAs, encryption, access control, monitoring, incident response, and formal clinical validation.

## Live Demo Links

<!-- DEMO_URL -->

- Frontend (Vercel): https://clinicalrag-three.vercel.app — **API pending** (set `VITE_API_URL` after Railway/Render).
- Backend health (Railway): `https://YOUR-BACKEND/health` — expect `"mock_llm": true` on the public mock deploy.
- Hosting checklist: [docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md)
