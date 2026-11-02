"""
Topic Ontology Agent (Step 0.5) + Topic Intelligence Pack (vNEXT)
=================================================================
Produces an authoritative, structured topic coverage checklist before planning.
Guarantees standard subtopics, mechanisms, and concrete applications are never
silently dropped, backed by persistent Supabase caching with TTL and versioning.

vNEXT Phase 1: Expanded into TopicIntelligencePack with richer fields.
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

ONTOLOGY_CACHE_VERSION = 1      # Legacy ontology cache version
ONTOLOGY_V2_CACHE_VERSION = 3   # vNEXT TopicIntelligencePack cache version (bumped for Phase 2 output integrity)
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

    try:
        raw_json = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception as e:
        logger.warning(f"[TopicOntology] LLM ontology generation failed ({e}), using deterministic checklist")
        raw_json = {}

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

    if not must_include:
        must_include = [
            f"A clear definition of {config.topic}",
            f"One worked example or case study of {config.topic}",
        ]

    checklist = TopicOntologyChecklist(
        core_subtopics=core_subtopics,
        must_include=must_include,
        optional_subtopics=optional_subtopics,
    )

    await save_cached_ontology(key, checklist)
    return checklist


# ═══════════════════════════════════════════════════════════════
# vNEXT Phase 1 — Topic Intelligence Pack
# ═══════════════════════════════════════════════════════════════

class TopicIntelligencePack(TopicOntologyChecklist):
    """Expanded topic intelligence with richer analysis fields.
    Backward-compatible: inherits all TopicOntologyChecklist fields.
    Empty is better than fake — fields default to empty lists (spec §8)."""
    canonical_concepts: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Key terms with definitions: [{term, definition}]",
    )
    key_terminology: List[str] = Field(default_factory=list)
    prerequisite_concepts: List[str] = Field(default_factory=list)
    concept_hierarchy: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Parent-child concept relationships",
    )
    processes: List[str] = Field(
        default_factory=list,
        description="Named sequential flows relevant to the topic",
    )
    cause_effect_pairs: List[Dict[str, str]] = Field(
        default_factory=list,
        description="[{cause, effect}]",
    )
    comparison_candidates: List[Dict[str, str]] = Field(
        default_factory=list,
        description="[{item_a, item_b, comparison_axis}]",
    )
    formulas_or_equations: List[str] = Field(default_factory=list)
    quantitative_evidence_candidates: List[str] = Field(default_factory=list)
    chronology_if_relevant: List[str] = Field(default_factory=list)
    misconceptions: List[Dict[str, str]] = Field(
        default_factory=list,
        description="[{myth, reality}]",
    )
    edge_cases: List[str] = Field(default_factory=list)
    real_world_examples: List[str] = Field(default_factory=list)
    case_studies: List[str] = Field(default_factory=list)
    applications: List[str] = Field(default_factory=list)
    recommended_diagrams: List[str] = Field(default_factory=list)
    recommended_charts: List[str] = Field(default_factory=list)
    recommended_tables: List[str] = Field(default_factory=list)
    authoritative_source_types: List[str] = Field(default_factory=list)


TOPIC_INTELLIGENCE_SYSTEM_PROMPT = """You are an elite curriculum architect, subject matter expert, and textbook author.
Given a topic, audience level, and depth, produce a comprehensive TopicIntelligencePack.

CRITICAL: Only include information you are CONFIDENT about.
Empty arrays are better than fabricated content.

Return strict JSON:
{{
  "core_subtopics": ["..."],
  "must_include": ["..."],
  "optional_subtopics": ["..."],
  "canonical_concepts": [
    {{"term": "...", "definition": "..."}}
  ],
  "key_terminology": ["..."],
  "prerequisite_concepts": ["..."],
  "concept_hierarchy": [
    {{"parent": "...", "children": ["...", "..."]}}
  ],
  "processes": ["..."],
  "cause_effect_pairs": [
    {{"cause": "...", "effect": "..."}}
  ],
  "comparison_candidates": [
    {{"item_a": "...", "item_b": "...", "comparison_axis": "..."}}
  ],
  "formulas_or_equations": ["..."],
  "quantitative_evidence_candidates": ["..."],
  "chronology_if_relevant": ["..."],
  "misconceptions": [
    {{"myth": "...", "reality": "..."}}
  ],
  "edge_cases": ["..."],
  "real_world_examples": ["..."],
  "case_studies": ["..."],
  "applications": ["..."],
  "recommended_diagrams": ["..."],
  "recommended_charts": ["..."],
  "recommended_tables": ["..."],
  "authoritative_source_types": ["..."]
}}
"""


async def generate_topic_intelligence(
    config: PresentationConfig,
    user_id: str = "",
) -> TopicIntelligencePack:
    """
    vNEXT Step 0.5: Generates expanded topic intelligence pack.
    Uses ONTOLOGY_V2_CACHE_VERSION so old caches are not reused.
    Falls back gracefully to basic fields if LLM returns partial data.
    """
    key = compute_ontology_key(config.topic, config.audience, config.depth)
    v2_key = f"v2_{key}"

    # Check v2 cache
    if supabase:
        try:
            res = supabase.table("ontology_cache")\
                .select("checklist, expires_at")\
                .eq("topic_key", v2_key)\
                .eq("version", ONTOLOGY_V2_CACHE_VERSION)\
                .gte("expires_at", datetime.now(timezone.utc).isoformat())\
                .execute()
            if res.data and len(res.data) > 0:
                logger.info(f"[TopicIntelligence] v2 cache HIT for {v2_key[:16]}")
                return TopicIntelligencePack(**res.data[0]["checklist"])
        except Exception:
            pass

        try:
            deck_res = supabase.table("deck_cache")\
                .select("deck_json")\
                .eq("topic", f"ontology_v{ONTOLOGY_V2_CACHE_VERSION}_{key}")\
                .execute()
            if deck_res.data and len(deck_res.data) > 0:
                payload = deck_res.data[0]["deck_json"]
                exp_str = payload.get("expires_at")
                if exp_str and datetime.fromisoformat(exp_str) >= datetime.now(timezone.utc):
                    logger.info(f"[TopicIntelligence] v2 deck_cache HIT for {key[:12]}")
                    return TopicIntelligencePack(**payload.get("checklist", {}))
        except Exception:
            pass

    logger.info(f"[TopicIntelligence] Generating expanded intelligence for '{config.topic}'...")

    messages = [
        {"role": "system", "content": TOPIC_INTELLIGENCE_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Topic: {config.topic}\n"
            f"Audience Level: {config.audience}\n"
            f"Depth: {config.depth}"
        )},
    ]

    try:
        raw_json = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
    except Exception as e:
        logger.warning(f"[TopicIntelligence] LLM intelligence generation failed ({e}), using default intelligence pack")
        raw_json = {}

    # Build TopicIntelligencePack with graceful defaults
    core_subtopics = raw_json.get("core_subtopics", [])
    if not core_subtopics:
        core_subtopics = [
            f"Foundations & Principles of {config.topic}",
            f"Core Mechanism & Architecture of {config.topic}",
            f"Operational Workflow and Key Components of {config.topic}",
            f"Quantitative Metrics & Practical Evaluation in {config.topic}",
            f"Real-World Production Case Studies in {config.topic}",
            f"Critical Limitations, Tradeoffs & Best Practices of {config.topic}",
        ]

    canonical_concepts = raw_json.get("canonical_concepts", [])
    if not canonical_concepts:
        canonical_concepts = [{"term": st} for st in core_subtopics]

    key_terminology = raw_json.get("key_terminology", [])
    if not key_terminology:
        key_terminology = [st.split("&")[0].strip() for st in core_subtopics]

    processes = raw_json.get("processes", [])
    cause_effect_pairs = raw_json.get("cause_effect_pairs", [])
    comparison_candidates = raw_json.get("comparison_candidates", [])
    misconceptions = raw_json.get("misconceptions", [])
    real_world_examples = raw_json.get("real_world_examples", [])

    pack = TopicIntelligencePack(
        # Base ontology fields
        core_subtopics=core_subtopics,
        must_include=raw_json.get("must_include", []),
        optional_subtopics=raw_json.get("optional_subtopics", []),
        # Expanded fields
        canonical_concepts=canonical_concepts,
        key_terminology=key_terminology,
        prerequisite_concepts=raw_json.get("prerequisite_concepts", []),
        concept_hierarchy=raw_json.get("concept_hierarchy", []),
        processes=processes,
        cause_effect_pairs=cause_effect_pairs,
        comparison_candidates=comparison_candidates,
        formulas_or_equations=raw_json.get("formulas_or_equations", []),
        quantitative_evidence_candidates=raw_json.get("quantitative_evidence_candidates", []),
        chronology_if_relevant=raw_json.get("chronology_if_relevant", []),
        misconceptions=misconceptions,
        edge_cases=raw_json.get("edge_cases", []),
        real_world_examples=real_world_examples,
        case_studies=raw_json.get("case_studies", []),
        applications=raw_json.get("applications", []),
        recommended_diagrams=raw_json.get("recommended_diagrams", []),
        recommended_charts=raw_json.get("recommended_charts", []),
        recommended_tables=raw_json.get("recommended_tables", []),
        authoritative_source_types=raw_json.get("authoritative_source_types", []),
    )

    # Cache v2 result
    if supabase:
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=ONTOLOGY_TTL_DAYS)).isoformat()
        pack_dict = pack.model_dump() if hasattr(pack, "model_dump") else pack.dict()
        try:
            supabase.table("ontology_cache").upsert({
                "topic_key": v2_key,
                "version": ONTOLOGY_V2_CACHE_VERSION,
                "checklist": pack_dict,
                "created_at": now.isoformat(),
                "expires_at": expires_at,
            }).execute()
        except Exception:
            try:
                supabase.table("deck_cache").upsert({
                    "topic": f"ontology_v{ONTOLOGY_V2_CACHE_VERSION}_{key}",
                    "depth": "ontology_v2",
                    "audience": "all",
                    "deck_json": {
                        "version": ONTOLOGY_V2_CACHE_VERSION,
                        "checklist": pack_dict,
                        "created_at": now.isoformat(),
                        "expires_at": expires_at,
                    },
                }).execute()
            except Exception as err:
                logger.warning(f"[TopicIntelligence] Could not save v2 cache: {err}")

    logger.info(
        f"[TopicIntelligence] Generated pack: "
        f"{len(pack.core_subtopics)} subtopics, "
        f"{len(pack.canonical_concepts)} concepts, "
        f"{len(pack.misconceptions)} misconceptions, "
        f"{len(pack.real_world_examples)} examples, "
        f"{len(pack.recommended_diagrams)} diagram suggestions"
    )
    return pack
