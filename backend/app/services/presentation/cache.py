"""
Presentation Engine — Semantic & Deterministic Cache
=====================================================
Calculates normalized request hashes to return cached presentations instantly
without wasting model tokens or re-rendering identical decks.
"""
import hashlib
import json
from typing import Optional, Dict, Any
from app.db.supabase_client import supabase
from .schemas import PresentationConfig, PresentationSpec


def compute_presentation_hash(config: PresentationConfig) -> str:
    """Compute a deterministic hash for a given presentation configuration."""
    normalized_dict = {
        "topic": config.topic.strip().lower(),
        "slide_count": config.slide_count,
        "audience": config.audience.strip().lower(),
        "language": config.language.strip().lower(),
        "depth": config.depth.strip().lower(),
        "design": config.design.value if hasattr(config.design, 'value') else str(config.design),
        "theme": config.theme.strip().lower(),
        "source_type": config.source_type,
        "source_id": config.source_id or "",
        "options": {
            "diagrams": config.enable_diagrams,
            "images": config.enable_images,
            "speaker_notes": config.enable_speaker_notes,
            "sources": config.enable_sources,
            "examples": config.enable_examples,
            "quiz": config.enable_quiz,
        }
    }
    raw_str = json.dumps(normalized_dict, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


async def get_cached_presentation(config: PresentationConfig) -> Optional[Dict[str, Any]]:
    """Retrieve cached presentation spec from Supabase deck_cache if present."""
    if not supabase:
        return None
    cache_key = compute_presentation_hash(config)
    try:
        res = supabase.table("deck_cache")\
            .select("deck_json")\
            .eq("topic", f"v2_{cache_key}")\
            .execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("deck_json")
    except Exception as e:
        print(f"[Cache] Error checking presentation cache (non-fatal): {e}")
    return None


async def save_cached_presentation(config: PresentationConfig, spec_json: Dict[str, Any]) -> None:
    """Store generated presentation spec in deck_cache."""
    if not supabase:
        return
    cache_key = compute_presentation_hash(config)
    try:
        supabase.table("deck_cache").insert({
            "topic": f"v2_{cache_key}",
            "depth": config.depth,
            "audience": config.audience,
            "deck_json": spec_json,
        }).execute()
    except Exception as e:
        print(f"[Cache] Warning: Could not cache presentation: {e}")
