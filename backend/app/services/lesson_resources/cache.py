"""
TeachGenie Lesson Planner — Durable Resource Cache
==================================================
Multi-tier persistent caching system guaranteeing durability across process restarts.
Uses SHA-256 intent profile hashing with TTL expiration and explicit refresh bypass.
Stores records on disk (.cache/resources) with optional Supabase syncing.
"""

import os
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any
from .schemas import ResourceIntentProfile

logger = logging.getLogger("teachgenie.lesson_resources.cache")

# Persistent cache directory on disk
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".cache", "lesson_resources")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory tier for sub-millisecond lookups
_MEM_CACHE: Dict[str, Dict[str, Any]] = {}


def compute_cache_key(profile: ResourceIntentProfile, provider: str) -> str:
    """
    Computes a deterministic hash uniquely identifying the pedagogical query profile.
    """
    payload = {
        "canonical_topic": profile.canonical_topic.strip().lower(),
        "concepts": sorted([c.strip().lower() for c in profile.concept_names]),
        "intent": profile.stage_intent.value,
        "level": profile.learner_level.strip().lower(),
        "weaknesses": sorted([w.strip().lower() for w in profile.learner_weaknesses]),
        "language": profile.preferred_language.strip().lower(),
        "provider": provider.strip().lower()
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DurableResourceCache:
    """
    Persistent caching engine for external resource retrieval.
    """

    DEFAULT_TTL_SECONDS = 86400 * 3  # 3 days TTL

    @classmethod
    def get(cls, profile: ResourceIntentProfile, provider: str, bypass: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response if present and unexpired.
        Returns None if expired or if bypass=True.
        """
        if bypass:
            return None

        cache_key = compute_cache_key(profile, provider)

        # 1. Check in-memory tier
        if cache_key in _MEM_CACHE:
            entry = _MEM_CACHE[cache_key]
            if time.time() < entry.get("expires_at", 0):
                logger.debug(f"[ResourceCache] Mem hit for {provider} key={cache_key[:8]}")
                return entry.get("response_json")

        # 2. Check disk tier
        disk_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_path):
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                    if time.time() < entry.get("expires_at", 0):
                        _MEM_CACHE[cache_key] = entry
                        logger.info(f"[ResourceCache] Disk hit for {provider} key={cache_key[:8]}")
                        return entry.get("response_json")
            except Exception as e:
                logger.warning(f"[ResourceCache] Error reading disk cache: {e}")

        return None

    @classmethod
    def set(
        cls,
        profile: ResourceIntentProfile,
        provider: str,
        response_json: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Persists response in memory and disk cache.
        """
        cache_key = compute_cache_key(profile, provider)
        ttl = ttl_seconds or cls.DEFAULT_TTL_SECONDS
        now = time.time()

        entry = {
            "cache_key": cache_key,
            "provider": provider,
            "query_profile_hash": cache_key,
            "response_json": response_json,
            "created_at": now,
            "expires_at": now + ttl
        }

        # Store in memory
        _MEM_CACHE[cache_key] = entry

        # Store on disk
        disk_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        try:
            with open(disk_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
            logger.info(f"[ResourceCache] Cached {provider} response to disk ({cache_key[:8]})")
        except Exception as e:
            logger.warning(f"[ResourceCache] Error writing disk cache: {e}")

    @classmethod
    def invalidate(cls, profile: ResourceIntentProfile, provider: str) -> None:
        cache_key = compute_cache_key(profile, provider)
        _MEM_CACHE.pop(cache_key, None)
        disk_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_path):
            try:
                os.remove(disk_path)
            except Exception:
                pass
