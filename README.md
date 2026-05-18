# ClinicalRAG

Grounded clinical decision support API and physician-facing web console for answering guideline questions from a local clinical document collection.

ClinicalRAG is a portfolio project built to show practical AI engineering: retrieval, source-grounded generation, clinical guardrails, evaluation, audit logging, and deployment-ready app structure. It is not intended for real patient care.

## Screenshot

Add a production screenshot after deploying the frontend. The local app runs at `http://localhost:5173`.

## Why This Exists

Clinical LLM demos often fail in the exact place that matters: they can sound confident without showing where an answer came from. ClinicalRAG keeps the model constrained to ingested guideline text, returns source citations, computes a grounding score, and records an audit trail without storing raw physician queries.

The goal is to demonstrate the kind of backend architecture a clinical AI team would care about, while keeping the UI restrained and operational rather than flashy.

## Architecture

```text
React physician console
        |
        v
FastAPI /api/v1/query
        |
        v
LangGraph StateGraph
        |
        +--> retrieve_node
        |       ChromaDB + all-MiniLM-L6-v2 embeddings
        |       deterministic query/source reranking
        |
        +--> grade_relevance_node
        |       Groq llama-3.1-8b-instant
        |
        +--> conditional edge
        |       relevant docs -> generate
        |       no relevant docs -> evaluate/refuse
        |
        +--> generate_node
        |       Groq llama-3.3-70b-versatile
        |
        +--> evaluate_grounding_node
        |       sentence attribution + content-token overlap
        |
        v
Answer + citations + hashed audit log
```

## Key Features

- LangGraph RAG pipeline with retrieve, grade, generate, and grounding-evaluation nodes.
- Local embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
- ChromaDB persisted to disk for guideline chunks and metadata.
- Groq generation with `llama-3.3-70b-versatile`.
- Groq grading with `llama-3.1-8b-instant`.
- Deterministic reranking so the most query-relevant chunks appear first in the source list.
- Hybrid grounding score that handles both quoted and paraphrased guideline answers.
- HIPAA-aware audit logging that stores query hashes, not raw query text.
- React console with query examples, source citations, confidence label, grounding bar, audit view, and document ingestion.
- Evaluation harness for checking expected sources, grounding scores, and off-topic refusal behavior.

## Stack

- Backend: Python 3.11, FastAPI, LangGraph, LangChain Groq, ChromaDB, sentence-transformers, SQLite
- Frontend: React 18, Vite, Tailwind CSS v3, Axios
- LLM provider: Groq
- Deployment: Railway backend, Vercel frontend

## Repository Layout

```text
backend/
  api/              FastAPI routes and Pydantic response models
  audit/            SQLite audit logger
  data/             seed clinical guideline content
  rag/              ingestion, retrieval, LangGraph pipeline, grounding evaluator
  eval_cases.json   expected demo/eval queries
  run_evals.py      local evaluation harness
frontend/
  src/              React app and components
  public/           favicon and static assets
ARCHITECTURE.md     system design notes and production tradeoffs
README.md           setup, API, demo, deployment
```

## Local Setup

### Backend

```bash
cd /Users/karimladak/clinicalrag/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
```

Edit `backend/.env` and set your Groq key:

```bash
GROQ_API_KEY=your_groq_key_here
CHROMA_PATH=./chroma_db
AUDIT_DB_PATH=./audit.db
```

Start the API:

```bash
uvicorn main:app --reload
```

First startup seeds the `clinical_guidelines` collection if it is empty.

### Frontend

Open a second terminal:

```bash
cd /Users/karimladak/clinicalrag/frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Demo Script

Use these queries in the UI:

```text
What SGLT2 inhibitors are recommended for heart failure?
What are the diagnostic criteria for sepsis?
What are first-line treatments for HFrEF?
How should atrial fibrillation stroke risk be assessed?
What anticoagulants are on the WHO Essential Medicines List?
```

What to point out:

- The answer is short and clinical, not chatty.
- Source cards show the guideline chunks used.
- Grounding score is high for on-topic guideline questions.
- The Audit tab stores query hashes, not raw query text.
- The top bar shows both API status and Groq configuration status.

Guardrail test:

```text
What is the capital of France?
```

Expected behavior: low confidence, warning/refusal, and no fabricated clinical answer.

## Evaluation Harness

Run:

```bash
cd /Users/karimladak/clinicalrag/backend
source .venv/bin/activate
python run_evals.py
```

The harness runs known clinical queries and an off-topic refusal case. It checks source titles, expected medical terms, and grounding score thresholds.

## API Reference

### Health

```bash
curl http://localhost:8000/health | python -m json.tool
```

Health includes collection stats and LLM provider status:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_provider": "groq",
  "llm_configured": true
}
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

### Ingest

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Example Hospital Protocol",
    "content": "Patients with suspected sepsis should have lactate measured and blood cultures obtained before antibiotics when this does not delay treatment.",
    "document_type": "protocol",
    "source_url": "https://example.org/protocol",
    "collection": "clinical_guidelines"
  }'
```

### Audit

```bash
curl http://localhost:8000/api/v1/audit | python -m json.tool
```

## Deployment

### Railway Backend

Deploy the `backend/` directory.

Set Railway environment variables:

```bash
GROQ_API_KEY=your_key
CHROMA_PATH=/data/chroma_db
AUDIT_DB_PATH=/data/audit.db
```

Add a Railway volume mounted at `/data` so ChromaDB and SQLite persist across deploys.

### Vercel Frontend

Deploy the `frontend/` directory.

Set:

```bash
VITE_API_URL=https://your-railway-backend.up.railway.app
```

## Limitations

- This is not a medical device and should not be used for real patient care.
- The seed corpus is intentionally small for demo purposes.
- ChromaDB local persistence is good for a portfolio deployment, but production multi-instance deployments should use shared vector storage.
- SQLite audit logging should become PostgreSQL in production.
- A production HIPAA deployment would require BAAs, encryption controls, access control, monitoring, incident response, and formal clinical validation.

## Live Demo Links

- Backend health: add Railway URL after deployment.
- Frontend: add Vercel URL after deployment.
