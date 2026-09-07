"""
Topic Ontology Agent (Step 0.5)
===============================
Produces an authoritative, structured topic coverage checklist before planning.
Guarantees standard subtopics, mechanisms, and concrete applications are never
silently dropped, backed by persistent Supabase caching with TTL and versioning.
"""
from app.core.logging import logger
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.ai import router
from app.db.supabase_client import supabase
from .schemas import PresentationConfig
from .prompts import TOPIC_ONTOLOGY_SYSTEM_PROMPT

ONTOLOGY_CACHE_VERSION = 1
ONTOLOGY_TTL_DAYS = 90


class TopicOntologyChecklist(BaseModel):
    core_subtopics: List[str] = Field(default_factory=list)
    must_include: List[str] = Field(default_factory=list)
    optional_subtopics: List[str] = Field(default_factory=list)


def compute_ontology_key(topic: str, audience: str, depth: str) -> str:
    """Deterministic normalized hash for topic ontology."""
    normalized = f"{topic.strip().lower()}::{audience.strip().lower()}::{depth.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def get_cached_ontology(key: str) -> Optional[TopicOntologyChecklist]:
    """Retrieve persistent checklist from Supabase with version and TTL validation."""
    if not supabase:
        return None
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        # Try primary ontology_cache table
        res = supabase.table("ontology_cache")\
            .select("checklist, expires_at")\
            .eq("topic_key", key)\
            .eq("version", ONTOLOGY_CACHE_VERSION)\
            .gte("expires_at", now_iso)\
            .execute()
        if res.data and len(res.data) > 0:
            logger.info(f"[TopicOntology] Persistent cache HIT in ontology_cache for {key[:12]}")
            return TopicOntologyChecklist(**res.data[0]["checklist"])
    except Exception as e:
        # Fallback to deck_cache table if ontology_cache migration not yet executed
        try:
            deck_res = supabase.table("deck_cache")\
                .select("deck_json")\
                .eq("topic", f"ontology_v{ONTOLOGY_CACHE_VERSION}_{key}")\
                .execute()
            if deck_res.data and len(deck_res.data) > 0:
                payload = deck_res.data[0]["deck_json"]
                exp_str = payload.get("expires_at")
                if exp_str and datetime.fromisoformat(exp_str) >= datetime.now(timezone.utc):
                    logger.info(f"[TopicOntology] Persistent cache HIT in deck_cache fallback for {key[:12]}")
                    return TopicOntologyChecklist(**payload.get("checklist", {}))
        except Exception:
            pass
    return None


async def save_cached_ontology(key: str, checklist: TopicOntologyChecklist) -> None:
    """Store checklist in persistent Supabase cache with version and TTL."""
    if not supabase:
        return
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=ONTOLOGY_TTL_DAYS)).isoformat()
    checklist_dict = checklist.model_dump() if hasattr(checklist, "model_dump") else checklist.dict()

    try:
        supabase.table("ontology_cache").upsert({
            "topic_key": key,
            "version": ONTOLOGY_CACHE_VERSION,
            "checklist": checklist_dict,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
        }).execute()
        logger.info(f"[TopicOntology] Cached checklist in ontology_cache for {key[:12]}")
    except Exception:
        # Fallback save to deck_cache
        try:
            supabase.table("deck_cache").upsert({
                "topic": f"ontology_v{ONTOLOGY_CACHE_VERSION}_{key}",
                "depth": "ontology",
                "audience": "all",
                "deck_json": {
                    "version": ONTOLOGY_CACHE_VERSION,
                    "checklist": checklist_dict,
                    "created_at": now.isoformat(),
                    "expires_at": expires_at,
                },
            }).execute()
            logger.info(f"[TopicOntology] Cached checklist in deck_cache fallback for {key[:12]}")
        except Exception as err:
            logger.warning(f"[TopicOntology] Could not save cache: {err}")


async def generate_topic_ontology(
    config: PresentationConfig,
    user_id: str = "",
) -> TopicOntologyChecklist:
    """
    Step 0.5: Generates a complete topic coverage checklist.
    Checks persistent Supabase cache first, then makes one fast structured LLM call.
    """
    key = compute_ontology_key(config.topic, config.audience, config.depth)

    cached = await get_cached_ontology(key)
    if cached:
        return cached

    logger.info(f"[TopicOntology] Generating coverage checklist for '{config.topic}'...")

    messages = [
        {"role": "system", "content": TOPIC_ONTOLOGY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Topic: {config.topic}\nAudience Level: {config.audience}\nDepth: {config.depth}"},
    ]

    raw_json = await router.generate_json(
        task="planning",
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    core_subtopics = raw_json.get("core_subtopics", [])
    must_include = raw_json.get("must_include", [])
    optional_subtopics = raw_json.get("optional_subtopics", [])

    # Ensure baseline fallback if model returned empty
    if not core_subtopics:
        core_subtopics = [
            f"Foundations & Principles of {config.topic}",
            f"Core Mechanism & Architecture of {config.topic}",
            f"Operational Workflow and Key Components",
            f"Quantitative Metrics & Practical Evaluation",
            f"Real-World Production Case Studies",
            f"Critical Limitations, Tradeoffs & Best Practices",
        ]

    checklist = TopicOntologyChecklist(
        core_subtopics=core_subtopics,
        must_include=must_include,
        optional_subtopics=optional_subtopics,
    )

    await save_cached_ontology(key, checklist)
    return checklist
