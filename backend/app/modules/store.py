"""Small table gateway: Supabase when connected, in-process memory otherwise.

Offline mode exists for tests and local development only; memory is lost on restart.
Remote errors propagate so that callers fail closed instead of pretending to succeed.
"""
from __future__ import annotations

import copy
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

_LOCK = threading.RLock()
_TABLES: dict[str, list[dict[str, Any]]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def _client():
    from app.db import supabase_client

    return supabase_client.supabase


def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(row.get(key) == value for key, value in filters.items())


def clear_memory() -> None:
    with _LOCK:
        _TABLES.clear()


def select(table: str, **filters: Any) -> list[dict[str, Any]]:
    client = _client()
    if client is not None:
        query = client.table(table).select("*")
        for key, value in filters.items():
            query = query.eq(key, value)
        return query.execute().data or []
    with _LOCK:
        return [copy.deepcopy(r) for r in _TABLES.get(table, []) if _matches(r, filters)]


def get_one(table: str, **filters: Any) -> Optional[dict[str, Any]]:
    rows = select(table, **filters)
    return rows[0] if rows else None


def insert(table: str, row: dict[str, Any]) -> dict[str, Any]:
    client = _client()
    if client is not None:
        return client.table(table).insert(row).execute().data[0]
    with _LOCK:
        stored = copy.deepcopy(row)
        stored.setdefault("id", str(uuid.uuid4()))
        _TABLES.setdefault(table, []).append(stored)
        return copy.deepcopy(stored)


def insert_unique(
    table: str, row: dict[str, Any], key_columns: tuple[str, ...]
) -> tuple[dict[str, Any], bool]:
    """Insert unless a row with the same key exists; the DB constraint settles races."""
    key = {column: row[column] for column in key_columns}
    with _LOCK:
        existing = get_one(table, **key)
        if existing is not None:
            return existing, False
        try:
            return insert(table, row), True
        except Exception as exc:
            if "23505" not in str(exc) and "duplicate key" not in str(exc):
                raise
    existing = get_one(table, **key)
    if existing is None:
        raise RuntimeError(f"Unique conflict on {table} without a visible row")
    return existing, False


def update(table: str, filters: dict[str, Any], patch: dict[str, Any]) -> int:
    client = _client()
    if client is not None:
        query = client.table(table).update(patch)
        for key, value in filters.items():
            query = query.eq(key, value)
        return len(query.execute().data or [])
    with _LOCK:
        count = 0
        for row in _TABLES.get(table, []):
            if _matches(row, filters):
                row.update(copy.deepcopy(patch))
                count += 1
        return count


def upsert(table: str, row: dict[str, Any], key_columns: tuple[str, ...]) -> dict[str, Any]:
    client = _client()
    if client is not None:
        return client.table(table).upsert(row, on_conflict=",".join(key_columns)).execute().data[0]
    with _LOCK:
        key = {column: row[column] for column in key_columns}
        if update(table, key, row):
            return get_one(table, **key)  # type: ignore[return-value]
        return insert(table, row)


def delete(table: str, **filters: Any) -> int:
    if not filters:
        raise ValueError("Refusing to delete without a filter")
    client = _client()
    if client is not None:
        query = client.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        return len(query.execute().data or [])
    with _LOCK:
        rows = _TABLES.get(table, [])
        kept = [r for r in rows if not _matches(r, filters)]
        _TABLES[table] = kept
        return len(rows) - len(kept)
