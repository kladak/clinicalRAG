"""Central settings — keep env reads in one place so routes/pipeline don't scatter getenv."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    chroma_path: str
    audit_db_path: str
    default_collection: str
    rate_limit_per_minute: int
    cors_origins: tuple[str, ...]
    mock_llm: bool
    log_json: bool
    log_level: str
    app_version: str
    grading_model: str
    generation_model: str
    embedding_model: str
    retrieval_overfetch: int
    # Intentionally tunable; evals caught an overly high floor once.
    relevance_floor: float
    high_grounding_threshold: float
    medium_grounding_threshold: float
    low_grounding_warn_threshold: float

    @property
    def groq_configured(self) -> bool:
        if self.mock_llm:
            return False
        key = self.groq_api_key.strip()
        return bool(key and key not in {"your_key_here", "your_groq_key_here"})

    @property
    def cors_origin_list(self) -> list[str]:
        return list(self.cors_origins)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "*")
    origin_tuple = tuple(o.strip() for o in origins.split(",") if o.strip()) or ("*",)
    mock = _bool(os.getenv("MOCK_LLM"), default=False) or _bool(
        os.getenv("CLINICALRAG_MOCK_LLM"), default=False
    )
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        chroma_path=os.getenv("CHROMA_PATH", "./chroma_db"),
        audit_db_path=os.getenv("AUDIT_DB_PATH", "./audit.db"),
        default_collection=os.getenv("DEFAULT_COLLECTION", "clinical_guidelines"),
        rate_limit_per_minute=_int(os.getenv("RATE_LIMIT_PER_MINUTE"), 30),
        cors_origins=origin_tuple,
        mock_llm=mock,
        log_json=_bool(os.getenv("LOG_JSON"), default=True),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        app_version=os.getenv("APP_VERSION", "1.1.0"),
        grading_model=os.getenv("GRADING_MODEL", "llama-3.1-8b-instant"),
        generation_model=os.getenv("GENERATION_MODEL", "llama-3.3-70b-versatile"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        retrieval_overfetch=_int(os.getenv("RETRIEVAL_OVERFETCH"), 2),
        relevance_floor=_float(os.getenv("RELEVANCE_FLOOR"), 0.2),
        high_grounding_threshold=_float(os.getenv("HIGH_GROUNDING_THRESHOLD"), 0.85),
        medium_grounding_threshold=_float(os.getenv("MEDIUM_GROUNDING_THRESHOLD"), 0.4),
        low_grounding_warn_threshold=_float(os.getenv("LOW_GROUNDING_WARN_THRESHOLD"), 0.5),
    )


def reset_settings_cache() -> None:
    """Test helper — clear lru_cache after monkeypatching env."""
    get_settings.cache_clear()
