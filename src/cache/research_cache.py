from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from src.config.settings import get_settings

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "output"
CACHE_DB = CACHE_DIR / "research_cache.db"
SCHEMA_VERSION = 3


def _get_db() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cache (
            key_hash TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    return conn


def _make_key(student_class: str, subject: str, chapter: str, medium: str) -> str:
    raw = f"{SCHEMA_VERSION}|{student_class}|{subject.lower()}|{chapter.lower()}|{medium}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(
    student_class: str, subject: str, chapter: str, medium: str
) -> Optional[dict]:
    settings = get_settings()
    ttl_seconds = settings.cache_ttl_hours * 3600
    key = _make_key(student_class, subject, chapter, medium)
    conn = _get_db()
    row = conn.execute(
        "SELECT data_json, created_at FROM research_cache WHERE key_hash = ?",
        (key,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    data_json, created_at = row
    if time.time() - created_at > ttl_seconds:
        conn = _get_db()
        conn.execute("DELETE FROM research_cache WHERE key_hash = ?", (key,))
        conn.commit()
        conn.close()
        return None
    return json.loads(data_json)


def set_cached(
    student_class: str,
    subject: str,
    chapter: str,
    medium: str,
    data: dict,
) -> None:
    key = _make_key(student_class, subject, chapter, medium)
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO research_cache (key_hash, data_json, created_at) VALUES (?, ?, ?)",
        (key, json.dumps(data), time.time()),
    )
    conn.commit()
    conn.close()


def invalidate(
    student_class: str, subject: str, chapter: str, medium: str
) -> None:
    key = _make_key(student_class, subject, chapter, medium)
    conn = _get_db()
    conn.execute("DELETE FROM research_cache WHERE key_hash = ?", (key,))
    conn.commit()
    conn.close()
