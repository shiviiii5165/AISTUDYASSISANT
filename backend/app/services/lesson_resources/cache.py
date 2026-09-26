"""
LearnByGenie Lesson Planner — Durable Resource Cache & Request Deduplication
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

PROVIDER_POLICY_VERSION = "2.4.0"
RESOURCE_SCHEMA_VERSION = "2.2.0"

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


def compute_cache_key(profile: ResourceIntentProfile, resource_type: str = "all", provider: Optional[str] = None) -> str:
    """
    Computes deterministic SHA-256 identity based on stage-specific semantic resource context:
    - roadmap_id
    - plan_version
    - stage_id
    - normalized_topic
    - normalized_stage_title
    - stage_archetype
    - stage_learning_objectives
    - canonical_concept_ids
    - fallback_concept_id
    - domain
    - specialization
    - learner_level
    - primary_intent
    - instructional_mode
    - resource_type
    - provider_policy_version
    - resource_schema_version
    """
    import re
    res_type = (provider or resource_type or "all").strip().lower()

    # Canonical concept IDs (sanitize generic concept_N)
    raw_concepts = profile.canonical_concept_ids or []
    cleaned_concepts = []
    for c in raw_concepts:
        c_str = str(c).strip()
        if re.match(r"^concept_\d+$", c_str, re.IGNORECASE):
            continue
        cleaned_concepts.append(c_str.lower())
    canonical_concept_ids = sorted(list(set(cleaned_concepts)))

    # Fallback concept ID: if provided, sanitize it too
    fallback_id = getattr(profile, "fallback_concept_id", None)
    if not fallback_id and getattr(profile, "concept_ids", None):
        fallback_id = profile.concept_ids[0] if profile.concept_ids else None
    if fallback_id and re.match(r"^concept_\d+$", str(fallback_id).strip(), re.IGNORECASE):
        fallback_id = "UNRESOLVED_CANONICAL_CONCEPT"
    elif fallback_id:
        fallback_id = str(fallback_id).strip().lower()

    # Stage archetype
    stage_archetype = getattr(profile, "stage_archetype", None)
    if not stage_archetype and profile.context:
        stage_archetype = getattr(profile.context, "stage_type", None)
    stage_archetype = (stage_archetype or "concept_intro").strip().lower()

    # Plan version
    plan_ver = getattr(profile, "plan_version", 1)
    if not plan_ver and profile.context:
        plan_ver = getattr(profile.context, "plan_version", 1)
    try:
        if isinstance(plan_ver, str) and plan_ver.isdigit():
            plan_ver = int(plan_ver)
    except Exception:
        pass

    # Learning objectives
    stage_learning_objectives = [
        obj.strip().lower() for obj in (profile.learning_objectives or [])
    ]

    # Normalized stage title and topic
    norm_stage_title = (profile.stage_title or "").strip().lower()
    norm_topic = (profile.canonical_topic or "").strip().lower()

    # Primary intent
    stage_intent = profile.stage_intent
    primary_intent = stage_intent.value if hasattr(stage_intent, "value") else str(stage_intent or "CONCEPT_LEARNING")
    primary_intent = primary_intent.strip().lower()

    payload = {
        "roadmap_id": (profile.roadmap_id or "").strip().lower(),
        "plan_version": plan_ver,
        "stage_id": (profile.stage_id or "").strip().lower(),
        "normalized_topic": norm_topic,
        "normalized_stage_title": norm_stage_title,
        "stage_archetype": stage_archetype,
        "stage_learning_objectives": stage_learning_objectives,
        "canonical_concept_ids": canonical_concept_ids,
        "fallback_concept_id": fallback_id,
        "domain": (profile.domain or "general").strip().lower(),
        "specialization": (profile.specialization or "").strip().lower() if profile.specialization else None,
        "learner_level": (profile.learner_level or "b.tech").strip().lower(),
        "primary_intent": primary_intent,
        "instructional_mode": (profile.instructional_mode or "direct_instruction").strip().lower(),
        "resource_type": res_type,
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

