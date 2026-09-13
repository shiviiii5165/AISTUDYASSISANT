"""
TeachGenie Lesson Planner — Durable Resource Cache & Request Deduplication
==========================================================================
Multi-tier persistent caching system guaranteeing durability across process restarts.
Uses SHA-256 semantic context hashing with configurable TTL expiration by source type:
- official docs: 7 days (long TTL)
- stable course metadata: 3 days (medium/long TTL)
- research papers: 1 day (medium TTL)
- YouTube: 6 hours (short/medium TTL)
- volatile software docs: 12 hours (shorter TTL)
In-flight request deduplication prevents duplicate concurrent upstream provider calls.
"""

import os
import json
import time
import hashlib
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from .schemas import ResourceIntentProfile

logger = logging.getLogger("teachgenie.lesson_resources.cache")

# Persistent cache directory on disk
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".cache", "lesson_resources")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory tier for sub-millisecond lookups
_MEM_CACHE: Dict[str, Dict[str, Any]] = {}

# In-flight request deduplication map
_IN_FLIGHT_REQUESTS: Dict[str, asyncio.Future] = {}
_DEDUP_LOCK = asyncio.Lock()

PROVIDER_POLICY_VERSION = "2.1.0"
RESOURCE_SCHEMA_VERSION = "2.0.0"

# Configurable TTLs by resource type
SOURCE_TYPE_TTL = {
    "official_docs": 86400 * 7,       # 7 days
    "courses": 86400 * 3,             # 3 days
    "research": 86400 * 1,            # 1 day
    "youtube": 3600 * 6,              # 6 hours
    "software_docs": 3600 * 12,       # 12 hours
    "learning_materials": 86400 * 1,  # 1 day
    "coding": 86400 * 3,              # 3 days
    "coding_resources": 86400 * 3     # 3 days
}


def compute_cache_key(profile: ResourceIntentProfile, resource_type: str) -> str:
    """
    Computes deterministic SHA-256 identity based on semantic resource context:
    - normalized_topic
    - canonical_concept_ids
    - domain
    - learner_level
    - resource_type
    - provider_policy_version
    - resource_schema_version
    """
    concept_ids = sorted(profile.canonical_concept_ids or [c.strip().lower() for c in profile.concept_names])
    payload = {
        "normalized_topic": profile.canonical_topic.strip().lower(),
        "canonical_concept_ids": concept_ids,
        "domain": profile.domain.strip().lower(),
        "learner_level": profile.learner_level.strip().lower(),
        "resource_type": resource_type.strip().lower(),
        "provider_policy_version": PROVIDER_POLICY_VERSION,
        "resource_schema_version": RESOURCE_SCHEMA_VERSION
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DurableResourceCache:
    """
    Persistent caching engine for external resource retrieval with request deduplication.
    """

    DEFAULT_TTL_SECONDS = 86400 * 3  # 3 days fallback

    @classmethod
    def get_ttl_for_resource(cls, resource_type: str) -> int:
        return SOURCE_TYPE_TTL.get(resource_type.lower(), cls.DEFAULT_TTL_SECONDS)

    @classmethod
    def get(cls, profile: ResourceIntentProfile, resource_type: str, bypass: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response if present and unexpired.
        Returns None if expired or if bypass=True.
        """
        if bypass:
            return None

        cache_key = compute_cache_key(profile, resource_type)

        # 1. Check in-memory tier
        if cache_key in _MEM_CACHE:
            entry = _MEM_CACHE[cache_key]
            if time.time() < entry.get("expires_at", 0):
                logger.debug(f"[ResourceCache] Mem hit for {resource_type} key={cache_key[:8]}")
                return entry.get("response_json")

        # 2. Check disk tier
        disk_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_path):
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                    if time.time() < entry.get("expires_at", 0):
                        _MEM_CACHE[cache_key] = entry
                        logger.info(f"[ResourceCache] Disk hit for {resource_type} key={cache_key[:8]}")
                        return entry.get("response_json")
            except Exception as e:
                logger.warning(f"[ResourceCache] Error reading disk cache: {e}")

        return None

    @classmethod
    def set(
        cls,
        profile: ResourceIntentProfile,
        resource_type: str,
        response_json: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Persists response in memory and disk cache with source-appropriate TTL.
        """
        cache_key = compute_cache_key(profile, resource_type)
        ttl = ttl_seconds or cls.get_ttl_for_resource(resource_type)
        now = time.time()

        entry = {
            "cache_key": cache_key,
            "resource_type": resource_type,
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
            logger.info(f"[ResourceCache] Cached {resource_type} response to disk ({cache_key[:8]}) TTL={ttl}s")
        except Exception as e:
            logger.warning(f"[ResourceCache] Error writing disk cache: {e}")

    @classmethod
    def invalidate(cls, profile: ResourceIntentProfile, resource_type: str) -> None:
        cache_key = compute_cache_key(profile, resource_type)
        _MEM_CACHE.pop(cache_key, None)
        disk_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_path):
            try:
                os.remove(disk_path)
            except Exception:
                pass

    @classmethod
    async def deduplicate_and_fetch(
        cls,
        profile: ResourceIntentProfile,
        resource_type: str,
        fetch_coroutine_fn: Callable[[], Awaitable[Dict[str, Any]]],
        bypass: bool = False
    ) -> Dict[str, Any]:
        """
        Guarantees that if multiple requests for the same semantic key are in flight,
        only ONE provider request is executed.
        """
        cache_key = compute_cache_key(profile, resource_type)

        # 1. Check cache first unless bypass
        if not bypass:
            cached = cls.get(profile, resource_type, bypass=False)
            if cached is not None:
                return cached

        # 2. Check if already in-flight
        is_creator = False
        async with _DEDUP_LOCK:
            if cache_key in _IN_FLIGHT_REQUESTS:
                logger.info(f"[ResourceCache] Deduplicating in-flight request for {resource_type} key={cache_key[:8]}")
                future = _IN_FLIGHT_REQUESTS[cache_key]
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                _IN_FLIGHT_REQUESTS[cache_key] = future
                is_creator = True

        # If another task created the in-flight future, simply await it
        if not is_creator:
            return await future

        # We are the single executor
        try:
            result = await fetch_coroutine_fn()
            if not future.done():
                future.set_result(result)
            cls.set(profile, resource_type, result)
            return result
        except Exception as e:
            if not future.done():
                future.set_exception(e)
            raise
        finally:
            async with _DEDUP_LOCK:
                _IN_FLIGHT_REQUESTS.pop(cache_key, None)


# Alias for backward compatibility and testing
ResourceCache = DurableResourceCache

