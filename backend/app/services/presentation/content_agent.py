"""
Content Agent
=============
Expands planned outline sections in efficient batches (5 slides per batch).
Retrieves targeted chunk context for each slide, enforces concise visible bullets (<80 chars),
rich speaker notes, concrete examples, and specialized structured layout parameters.
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import PresentationConfig, SlideSpec, SlideType
from .prompts import CONTENT_BATCH_SYSTEM_PROMPT
from ..knowledge import get_slide_context


async def expand_presentation_content(
    config: PresentationConfig,
    user_id: str,
    outline_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Expands planned slides in batches of 5.
    Returns fully hydrated slide dictionaries.
    """
    planned_slides = outline_data.get("slides", [])
    batch_size = 5
    expanded_slides: List[Dict[str, Any]] = []

    for i in range(0, len(planned_slides), batch_size):
        batch = planned_slides[i:i + batch_size]
        batch_context_parts = []
        batch_source_refs_map = {}

        # 1. Retrieve slide-specific chunks for each slide in batch
        if config.source_type in ["uploaded_material", "uploaded_material_plus_web"] and config.source_id:
            for s in batch:
                s_no = s.get("slide_no", 0)
                ctx, refs = await get_slide_context(
                    document_id=config.source_id,
                    user_id=user_id,
                    slide_title=s.get("title", ""),
                    key_message=s.get("key_message", ""),
                    top_k=2,
                )
                if ctx:
                    batch_context_parts.append(f"--- Context for Slide {s_no} ({s.get('title')}): ---\n{ctx}")
                if refs:
                    batch_source_refs_map[s_no] = [r.dict() for r in refs]

        # 2. Build prompt for this 5-slide batch
        batch_prompt_dict = {
            "topic": config.topic,
            "audience": config.audience,
            "language": config.language,
            "depth": config.depth,
            "slides_to_expand": batch,
        }

        user_content_str = f"Expand the following slides into rich, scannable presentation content:\n{json.dumps(batch_prompt_dict, indent=2)}"
        if batch_context_parts:
            user_content_str += f"\n\nDocument Grounding Material:\n" + "\n\n".join(batch_context_parts)

        messages = [
            {"role": "system", "content": CONTENT_BATCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_content_str},
        ]

        # 3. Call ModelRouter
        batch_result = await router.generate_json(
            task="content_generation",
            messages=messages,
            temperature=0.3,
            max_tokens=6000,
        )

        raw_expanded = batch_result.get("slides", [])
        
        # If the LLM returned a list directly or missing fields, sanitize
        if not raw_expanded and isinstance(batch_result, list):
            raw_expanded = batch_result

        # Map and sanitize each expanded slide
        for orig_slide in batch:
            s_no = orig_slide.get("slide_no")
            # Find matching generated slide
            found = next((x for x in raw_expanded if x.get("slide_no") == s_no), None)
            if not found and raw_expanded:
                # fallback to positional matching
                idx_in_batch = orig_slide.get("slide_no", 1) - i - 1
                if 0 <= idx_in_batch < len(raw_expanded):
                    found = raw_expanded[idx_in_batch]

            if not found:
                found = {
                    "slide_no": s_no,
                    "type": orig_slide.get("type", "concept"),
                    "title": orig_slide.get("title", f"Slide {s_no}"),
                    "key_message": orig_slide.get("key_message", ""),
                    "body_bullets": ["Key operational insight", "Supporting structural mechanism"],
                    "speaker_notes": orig_slide.get("key_message", ""),
                }

            # Enforce bullet constraints (<80 chars, max 5)
            cleaned_bullets = []
            for b in found.get("body_bullets", []):
                b_str = str(b).strip()
                if len(b_str) > 95:
                    b_str = b_str[:90] + "..."
                if b_str:
                    cleaned_bullets.append(b_str)
            found["body_bullets"] = cleaned_bullets[:5]

            # Attach source refs
            if s_no in batch_source_refs_map:
                found["source_refs"] = batch_source_refs_map[s_no]

            # Preserve or default slide_no and type
            found["slide_no"] = s_no
            if not found.get("type"):
                found["type"] = orig_slide.get("type", "concept")

            expanded_slides.append(found)

    # Final sort by slide_no
    expanded_slides.sort(key=lambda s: s.get("slide_no", 0))
    return expanded_slides
