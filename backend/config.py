"""Central settings — keep env reads in one place so routes/pipeline don't scatter getenv."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    app_version: str

    @property
    def groq_configured(self) -> bool:
        key = self.groq_api_key.strip()
        return bool(key and key not in {"your_key_here", "your_groq_key_here"})


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "*")
    origin_tuple = tuple(o.strip() for o in origins.split(",") if o.strip()) or ("*",)
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        chroma_path=os.getenv("CHROMA_PATH", "./chroma_db"),
        audit_db_path=os.getenv("AUDIT_DB_PATH", "./audit.db"),
        default_collection=os.getenv("DEFAULT_COLLECTION", "clinical_guidelines"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
        cors_origins=origin_tuple,
        mock_llm=_bool(os.getenv("MOCK_LLM"), default=False),
        log_json=_bool(os.getenv("LOG_JSON"), default=True),
        app_version=os.getenv("APP_VERSION", "1.1.0"),
    )


def reset_settings_cache() -> None:
    """Test helper — clear lru_cache after monkeypatching env."""
    get_settings.cache_clear()
