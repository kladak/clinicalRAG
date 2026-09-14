# ClinicalRAG — public MOCK_LLM recruiter demo hosting

Educational / research CDS only — **not a medical device, not for real patient care.**

This guide is for a **public mock** deploy: extractive answers from the seeded guideline corpus, **no Groq API key required**. Do not invent or quote clinical performance metrics on the live page.

## Public-demo-safe defaults

| Variable | Public mock value | Why |
|---|---|---|
| `MOCK_LLM` | `1` | Extractive path; **no `GROQ_API_KEY` needed** |
| `ENABLE_INGEST` | `0` | Blocks unauthenticated `/api/v1/ingest` on the public internet |
| `CORS_ORIGINS` | Exact Vercel origin(s), comma-separated | Prefer locking to the frontend URL; `*` works for a short recruiter demo but is looser |
| `CHROMA_PATH` | `/data/chroma_db` | Persist vector store on Railway volume |
| `AUDIT_DB_PATH` | `/data/audit.db` | Persist hashed audit DB on volume |
| `RATE_LIMIT_PER_MINUTE` | `30` (or lower) | Demo-grade in-process limiter |

Optional aliases: `CLINICALRAG_MOCK_LLM=1` is accepted the same as `MOCK_LLM=1`.

**Do not set** `GROQ_API_KEY` for the mock recruiter path. With `MOCK_LLM=1`, `groq_configured` stays false even if a key is present.

Local/dev defaults remain permissive (`ENABLE_INGEST` defaults to on; `MOCK_LLM` defaults to off). Public hosting must set the table above explicitly.

---

## Railway (backend)

1. New project → deploy from GitHub → **Root Directory:** `backend`
2. Builder: Dockerfile (`backend/Dockerfile` + `backend/railway.toml`)
3. Attach a **volume** mounted at `/data` (survives restarts; seeds on first empty Chroma)
4. Set environment variables:

```bash
MOCK_LLM=1
ENABLE_INGEST=0
CHROMA_PATH=/data/chroma_db
AUDIT_DB_PATH=/data/audit.db
CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app
RATE_LIMIT_PER_MINUTE=30
LOG_JSON=1
LOG_LEVEL=INFO
# Do NOT set GROQ_API_KEY for the mock recruiter demo
```

5. After first deploy, note the public HTTPS URL, e.g. `https://clinicalrag-xxxx.up.railway.app` (no trailing slash).
6. Smoke checks:

```bash
curl -sS "$RAILWAY_URL/health" | python -m json.tool
# expect: "mock_llm": true, "llm_configured": false

curl -sS "$RAILWAY_URL/api/v1/ready" | python -m json.tool
```

Start command (already in `railway.toml`): `uvicorn main:app --host 0.0.0.0 --port $PORT`

Cold start may take a minute while embeddings load from the image cache and the seed corpus is written.

---

## Vercel (frontend)

1. New project → import the same repo → **Root Directory:** `frontend`
2. Framework: Vite (auto). Build: `npm run build`. Output: `dist`
3. `frontend/vercel.json` provides SPA fallback rewrites to `index.html`. `VITE_API_URL` is **build-time** (Vite); set it in the Vercel project **Environment Variables** for Production (and Preview if you want preview builds to hit the mock API).
4. Exact env vars:

```bash
VITE_API_URL=https://YOUR-BACKEND.up.railway.app
```

No trailing slash. Do not point at `localhost`. Rebuild after changing `VITE_API_URL` (Vite inlines it at build time).

5. Deploy → note the frontend URL, e.g. `https://clinicalrag-xxxx.vercel.app`
6. Go back to Railway and set `CORS_ORIGINS` to that exact origin (scheme + host, no path). Redeploy backend if CORS was wrong on first boot.

`vercel.json` does not need to list `VITE_API_URL`; Vercel injects project env into the build. Confirm Root Directory is `frontend` so this file is applied.

---

## After both are live

1. Replace the README placeholder `<!-- DEMO_URL -->` with the Vercel URL (and optionally link backend `/health`).
2. Recruiter walkthrough: use the **Demo Script** questions in the README; call out mock/extractive mode in the UI status if shown; show a refusal on an off-topic prompt.
3. Reminder on any public page: educational / research only — not for real patient care.

## Out of scope for this mock path

- Live Groq grading/generation (`MOCK_LLM=0` + `GROQ_API_KEY`)
- Public ingest / corpus uploads
- Claiming clinical accuracy, HIPAA compliance, or device clearance
