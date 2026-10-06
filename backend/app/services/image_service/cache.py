"""
Image Service — Cache Layer
============================
Two-tier image cache:
  1. In-memory LRU dict (fast, 24h TTL, primary quota defense)
  2. Supabase persistent layer (secondary, same `image_cache` table)

Cache is the PRIMARY defense against quota exhaustion — built first, treated as main lever.
"""
from app.core.logging import logger
import hashlib
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from .models import ImageResult, Attribution

# In-memory cache config
MAX_MEMORY_ENTRIES = 500
MEMORY_TTL_SECONDS = 86400  # 24 hours
IMAGE_CACHE_VERSION = 2     # bumped from v1 to avoid stale entries from old router
PERSISTENT_TTL_DAYS = 30


def normalize_query_hash(query: str) -> str:
    """Compute normalized SHA256 hash for an image query."""
    clean = re.sub(r"[^\w\s]", "", query.strip().lower())
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


class _MemoryEntry:
    """Single in-memory cache entry with expiry timestamp."""
    __slots__ = ("result", "expires_at")

    def __init__(self, result: ImageResult, ttl_seconds: int = MEMORY_TTL_SECONDS):
        self.result = result
        self.expires_at = time.monotonic() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class ImageCache:
    """
    Two-tier image cache with in-memory LRU + Supabase persistent fallback.
    Thread-safe for async (single-threaded event loop).
    """

    def __init__(self, supabase_client=None):
        self._memory: OrderedDict[str, _MemoryEntry] = OrderedDict()
        self._supabase = supabase_client

    # ── Public API ──────────────────────────────────────────────────────

    async def get(self, query: str) -> Optional[ImageResult]:
        """Look up cached image for query. Memory first, then Supabase."""
        q_hash = normalize_query_hash(query)

        # 1. In-memory check
        entry = self._memory.get(q_hash)
        if entry and not entry.is_expired:
            self._memory.move_to_end(q_hash)
            logger.info(f"[ImageCache] Memory HIT for '{query[:40]}' (hash {q_hash[:12]})")
            return entry.result
        elif entry:
            # Expired — evict
            del self._memory[q_hash]

        # 2. Supabase persistent check
        result = await self._get_from_supabase(q_hash, query)
        if result:
            self._put_memory(q_hash, result)
            logger.info(f"[ImageCache] Supabase HIT for '{query[:40]}' (hash {q_hash[:12]})")
            return result

        return None

    async def put(self, query: str, result: ImageResult) -> None:
        """Store an image result in both memory and Supabase."""
        q_hash = normalize_query_hash(query)
        self._put_memory(q_hash, result)
        await self._save_to_supabase(q_hash, result)

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        now = time.monotonic()
        valid = sum(1 for e in self._memory.values() if not e.is_expired)
        return {
            "memory_entries": len(self._memory),
            "memory_valid": valid,
            "memory_expired": len(self._memory) - valid,
            "max_entries": MAX_MEMORY_ENTRIES,
        }

    # ── Private: Memory LRU ────────────────────────────────────────────

    def _put_memory(self, q_hash: str, result: ImageResult) -> None:
        """Add or update an entry in the in-memory LRU cache."""
        if q_hash in self._memory:
            self._memory.move_to_end(q_hash)
        self._memory[q_hash] = _MemoryEntry(result)
        # Evict oldest if over capacity
        while len(self._memory) > MAX_MEMORY_ENTRIES:
            self._memory.popitem(last=False)

    # ── Private: Supabase Persistent Layer ─────────────────────────────

    async def _get_from_supabase(self, q_hash: str, query: str) -> Optional[ImageResult]:
        """Retrieve cached image metadata from Supabase and re-download bytes."""
        if not self._supabase:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            res = self._supabase.table("image_cache") \
                .select("image_url, provider, metadata, expires_at") \
                .eq("query_hash", q_hash) \
                .eq("version", IMAGE_CACHE_VERSION) \
                .gte("expires_at", now_iso) \
                .execute()

            if not res.data:
                return None

            row = res.data[0]
            image_url = row.get("image_url", "")
            if not image_url:
                return None

            # Download the image bytes
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(image_url, headers={
                    "User-Agent": "LearnByGenieEduBot/2.0 (https://learnbygenie.online)"
                })
                if resp.status_code != 200 or len(resp.content) < 1000:
                    return None

            metadata = row.get("metadata", {}) or {}
            attribution = Attribution(
                photographer_name=metadata.get("photographer_name", ""),
                photographer_url=metadata.get("photographer_url", ""),
                source_url=metadata.get("source_url", image_url),
                provider=row.get("provider", ""),
                license_type=metadata.get("license_type", "free"),
            )

            return ImageResult(
                image_bytes=resp.content,
                provider=row.get("provider", "cached"),
                url=image_url,
                query=query,
                attribution=attribution,
            )
        except Exception as e:
            logger.warning(f"[ImageCache] Supabase read error: {e}")
            return None

    async def _save_to_supabase(self, q_hash: str, result: ImageResult) -> None:
        """Persist image metadata to Supabase with TTL."""
        if not self._supabase:
            return

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=PERSISTENT_TTL_DAYS)).isoformat()

        try:
            self._supabase.table("image_cache").upsert({
                "query_hash": q_hash,
                "version": IMAGE_CACHE_VERSION,
                "provider": result.provider,
                "image_url": result.url,
                "metadata": {
                    "photographer_name": result.attribution.photographer_name,
                    "photographer_url": result.attribution.photographer_url,
                    "source_url": result.attribution.source_url,
                    "license_type": result.attribution.license_type,
                    "query": result.query,
                },
                "created_at": now.isoformat(),
                "expires_at": expires_at,
            }).execute()
            logger.info(f"[ImageCache] Saved {result.provider} image to Supabase (hash {q_hash[:12]})")
        except Exception as e:
            logger.warning(f"[ImageCache] Supabase write error: {e}")
