import logging
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.routes import router
from audit.logger import init_audit_db
from config import get_settings
from data.seed_data import seed_if_empty
from logging_config import configure_logging
from rag.pipeline import GENERATION_MODEL, GRADING_MODEL, LLM_PROVIDER, groq_configured
from rag.retriever import collection_stats

settings = get_settings()
configure_logging(level=settings.log_level, json_logs=settings.log_json)
logger = logging.getLogger("clinicalrag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_audit_db()
    seed_if_empty()
    logger.info(
        "startup_complete",
        extra={"event": "startup", "request_id": "startup"},
    )
    yield


app = FastAPI(
    title="ClinicalRAG API",
    description=(
        "Educational grounded clinical decision support — responses strictly from "
        "ingested guidelines. NOT a medical device."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "request",
        extra={
            "event": "http_request",
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    response.headers["X-Request-Id"] = request_id
    return response


app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    current = get_settings()
    return {
        "status": "ok",
        "version": current.app_version,
        "collections": collection_stats(),
        "llm_provider": LLM_PROVIDER,
        "llm_configured": groq_configured(),
        "mock_llm": current.mock_llm,
        "grading_model": GRADING_MODEL,
        "generation_model": GENERATION_MODEL,
    }


@app.get("/ready")
async def ready():
    """Liveness companion at root; detailed checks live under /api/v1/ready."""
    return {"status": "ready", "version": get_settings().app_version}
