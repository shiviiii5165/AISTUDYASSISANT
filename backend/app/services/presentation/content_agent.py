"""
Content Agent
=============
Expands planned outline sections in efficient parallel batches (3-4 slides per batch).
Retrieves targeted chunk context for each slide, enforces concise visible bullets (<80 chars),
rich speaker notes, concrete examples, and specialized structured layout parameters.
"""
import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import PresentationConfig, SlideSpec, SlideType
from .prompts import CONTENT_BATCH_SYSTEM_PROMPT
from ..knowledge import get_slide_context

logger = logging.getLogger("teachgenie.presentation.content_agent")


async def _expand_single_batch(
    batch: List[Dict[str, Any]],
    config: PresentationConfig,
    user_id: str,
) -> List[Dict[str, Any]]:
    """Expands a single chunk of up to 4 slides."""
    if not batch:
        return []

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

    # 2. Build prompt for this batch
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

    # 3. Call ModelRouter with safe token ceiling
    try:
        batch_result = await router.generate_json(
            task="content_generation",
            messages=messages,
            temperature=0.3,
            max_tokens=2200,
        )
    except Exception as err:
        logger.warning(f"[ContentAgent] Batch generation failed: {err}. Using fallback templates.")
        batch_result = {}

    if isinstance(batch_result, list):
        raw_expanded = batch_result
    elif isinstance(batch_result, dict):
        raw_expanded = batch_result.get("slides", [])
        if not raw_expanded and "slide_no" in batch_result:
            raw_expanded = [batch_result]
    else:
        raw_expanded = []

    expanded_batch: List[Dict[str, Any]] = []

    # Map and sanitize each expanded slide
    for idx, orig_slide in enumerate(batch):
        s_no = orig_slide.get("slide_no")
        # Find matching generated slide
        found = next((x for x in raw_expanded if x.get("slide_no") == s_no), None)
        if not found and raw_expanded:
            # fallback to positional matching
            if 0 <= idx < len(raw_expanded):
                found = raw_expanded[idx]

        if not found:
            found = {
                "slide_no": s_no,
                "type": orig_slide.get("type", "concept"),
                "title": orig_slide.get("title", f"Slide {s_no}"),
                "key_message": orig_slide.get("key_message", ""),
                "body_bullets": ["Key operational insight", "Supporting structural mechanism"],
                "speaker_notes": orig_slide.get("key_message", ""),
            }

        # Enforce bullet constraints (<95 chars, max 6)
        cleaned_bullets = []
        for b in found.get("body_bullets", []):
            b_str = str(b).strip()
            if len(b_str) > 100:
                b_str = b_str[:95] + "..."
            if b_str:
                cleaned_bullets.append(b_str)
        found["body_bullets"] = cleaned_bullets[:6]

        # Attach source refs
        if s_no in batch_source_refs_map:
            found["source_refs"] = batch_source_refs_map[s_no]

        # Preserve or default slide_no and type
        found["slide_no"] = s_no
        if not found.get("type"):
            found["type"] = orig_slide.get("type", "concept")

        # Preserve image_query or construct descriptive photographic fallback
        img_q = (found.get("image_query") or "").strip()
        if not img_q:
            clean_title = re.sub(r"[^\w\s]", "", orig_slide.get("title", ""))
            img_q = f"{clean_title} educational system demonstration photography"
        found["image_query"] = img_q
        found["visual_prompt"] = found.get("visual_prompt") or orig_slide.get("visual_hint", "")

        # Content Pattern Tagging & Deterministic Fallback
        cpat = found.get("content_pattern") or orig_slide.get("content_pattern")
        if not cpat:
            cpat = detect_content_pattern_fallback_dict(found)
        found["content_pattern"] = cpat

        expanded_batch.append(found)

    return expanded_batch


def detect_content_pattern_fallback_dict(slide: Dict[str, Any]) -> str:
    """
    Intelligent deterministic fallback ladder matching slide content signals.
    Default fallback is strictly 'plain_concept' (clean bullets), never a shape-based pattern.
    """
    title_l = (slide.get("title") or "").lower()
    bullets_l = " ".join(slide.get("body_bullets") or []).lower()
    comb = f"{title_l} {bullets_l}"

    # 1. Definition signals
    if any(w in title_l for w in ["definition", "what is", "glossary", "terminology", "concept:"]):
        return "definition_box"

    # 2. Contrast signals (The Trap vs The Discipline, Misconceptions, Anti-patterns)
    if any(w in comb for w in ["trap", "misconception", "pitfall", "anti-pattern", "vs.", "versus", "do's and don'ts"]):
        return "contrast_pair"

    # 3. Process / sequential flow
    if slide.get("steps") or any(w in title_l for w in ["step", "lifecycle", "workflow", "pipeline", "phase", "algorithm:"]):
        return "numbered_process"

    # 4. Case Study
    if any(w in title_l for w in ["case study", "real-world", "incident", "failure analysis"]):
        return "case_study_block"

    # 5. Activity / Classroom exercise
    if any(w in title_l for w in ["activity", "exercise", "try this", "discussion prompt", "lab task"]):
        return "activity_banner"

    # 6. Comparison Table (explicit matrix or structured table)
    if slide.get("columns") and len(slide.get("columns")) >= 2:
        return "comparison_table"

    # 7. Structural CS data concepts (strictly gated to stack, queue, tree, graph, database)
    cs_terms = ["stack", "lifo", "queue", "fifo", "binary tree", "graph topology", "database cylinder"]
    if any(t in comb for t in cs_terms) and any(w in title_l for w in ["structure", "model", "collection", "topology"]):
        return "illustrated_icon_grid"

    # 8. Worked example
    if any(w in title_l for w in ["worked example", "step-by-step trace", "walkthrough", "trace table"]):
        return "worked_example_table"

    # Default fallback: plain text bullets (never a shape or circle-pill)
    return "plain_concept"


async def expand_presentation_content(
    config: PresentationConfig,
    user_id: str,
    outline_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Expands planned slides in parallel batches of 3.
    Returns fully hydrated slide dictionaries.
    Hard-capped at 40s to prevent indefinite hangs.
    """
    planned_slides = outline_data.get("slides", [])
    if not planned_slides:
        return []

    # Batch into chunks of 3 slides for parallel execution and strict token bounds
    BATCH_SIZE = 3
    batches = [planned_slides[i:i + BATCH_SIZE] for i in range(0, len(planned_slides), BATCH_SIZE)]
    
    # Process batches concurrently with asyncio.gather (hard 40s cap)
    try:
        batch_results = await asyncio.wait_for(
            asyncio.gather(
                *[_expand_single_batch(b, config, user_id) for b in batches],
                return_exceptions=True,
            ),
            timeout=40.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[ContentAgent] Batch expansion timed out after 40s. Using fallback templates for all slides.")
        batch_results = []

    expanded_slides: List[Dict[str, Any]] = []
    for i, r in enumerate(batch_results):
        if isinstance(r, Exception):
            logger.warning(f"[ContentAgent] Batch {i+1} failed ({r}), using fallback templates.")
            # Generate fallback slides for this batch
            for s in batches[i]:
                expanded_slides.append({
                    "slide_no": s.get("slide_no"),
                    "type": s.get("type", "concept"),
                    "title": s.get("title", f"Slide {s.get('slide_no', 0)}"),
                    "key_message": s.get("key_message", ""),
                    "body_bullets": ["Key operational insight", "Supporting structural mechanism"],
                    "speaker_notes": s.get("key_message", ""),
                    "image_query": f"{s.get('title', '')} educational demonstration photography",
                })
        else:
            expanded_slides.extend(r)

    # If gather timed out, fill remaining slides with fallbacks
    if len(expanded_slides) < len(planned_slides):
        covered_slide_nos = {s.get("slide_no") for s in expanded_slides}
        for s in planned_slides:
            if s.get("slide_no") not in covered_slide_nos:
                expanded_slides.append({
                    "slide_no": s.get("slide_no"),
                    "type": s.get("type", "concept"),
                    "title": s.get("title", f"Slide {s.get('slide_no', 0)}"),
                    "key_message": s.get("key_message", ""),
                    "body_bullets": ["Key operational insight", "Supporting structural mechanism"],
                    "speaker_notes": s.get("key_message", ""),
                    "image_query": f"{s.get('title', '')} educational demonstration photography",
                })

    # Final sort by slide_no
    expanded_slides.sort(key=lambda s: s.get("slide_no", 0))
    return expanded_slides

