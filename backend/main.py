from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.routes import router
from audit.logger import init_audit_db
from data.seed_data import seed_if_empty
from rag.pipeline import GENERATION_MODEL, GRADING_MODEL, LLM_PROVIDER, groq_configured
from rag.retriever import collection_stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_audit_db()
    seed_if_empty()
    yield


app = FastAPI(
    title="ClinicalRAG API",
    description="Grounded clinical decision support - responses strictly from ingested guidelines",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "collections": collection_stats(),
        "llm_provider": LLM_PROVIDER,
        "llm_configured": groq_configured(),
        "grading_model": GRADING_MODEL,
        "generation_model": GENERATION_MODEL,
    }
