import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone

from config import get_settings


def _db_path() -> str:
    return get_settings().audit_db_path


def init_audit_db():
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            query_hash TEXT,
            collection TEXT,
            sources_retrieved INTEGER,
            grounding_score REAL,
            latency_ms INTEGER
        )
    """
    )
    conn.commit()
    conn.close()


def log_query(
    query: str,
    collection: str,
    sources_retrieved: int,
    grounding_score: float,
    latency_ms: int,
) -> str:
    query_id = str(uuid.uuid4())
    query_hash = hashlib.sha256(query.encode()).hexdigest()
    conn = sqlite3.connect(_db_path())
    conn.execute(
        "INSERT INTO audit_log VALUES (?,?,?,?,?,?,?)",
        (
            query_id,
            datetime.now(timezone.utc).isoformat(),
            query_hash,
            collection,
            sources_retrieved,
            grounding_score,
            latency_ms,
        ),
    )
    conn.commit()
    conn.close()
    return query_id


def get_recent_audit(limit: int = 100) -> list:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
