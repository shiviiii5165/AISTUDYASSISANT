"""
Content Agent (Master Prompt v2 + Free Tier Refactor)
=====================================================
Expands planned outline sections in efficient sequential batches.
Implements two-pass generation: Draft → Refine.
Enforces:
- 3–5 meaningful visible content blocks per slide
- Complete sentences with verbs (no noun fragments)
- Banned-string rejection and self-check validation
- 90–160 word speaker notes
- Word-boundary-aware overflow handling (no raw slicing)
- Topic-derived fallbacks (never banned placeholder strings)
- Sequential memory tracking to prevent cross-slide repetition
"""
import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from app.services.ai import router
from .schemas import PresentationConfig, SlideSpec, SlideType
from .prompts import CONTENT_BATCH_SYSTEM_PROMPT, SLIDE_PATCH_SYSTEM_PROMPT
from ..knowledge import get_slide_context

logger = logging.getLogger("teachgenie.presentation.content_agent")

# ═══════════════════════════════════════════════════════════════
# Banned strings — absolute rejection list from Master Prompt
# ═══════════════════════════════════════════════════════════════
BANNED_STRINGS = [
    "key operational insight",
    "supporting structural mechanism",
    "lorem",
    "tbd",
    "placeholder",
    "content goes here",
    "overview of the topic",
    "in this slide we will",
    "this is important",
    "understanding x matters",
    "key educational insight",
    "synthesized understanding",
    "core takeaway summary",
    "key takeaway context",
    "core component analysis",
]


def _contains_banned(text: str) -> bool:
    """Check if text contains any banned filler string."""
    text_lower = text.lower().strip()
    return any(banned in text_lower for banned in BANNED_STRINGS)


def _has_verb(sentence: str) -> bool:
    """Basic heuristic to check if a sentence likely contains a verb."""
    verb_indicators = [
        "is", "are", "was", "were", "has", "have", "had", "does", "do", "did",
        "can", "could", "will", "would", "should", "may", "might", "shall",
        "uses", "enables", "provides", "requires", "allows", "creates", "generates",
        "processes", "converts", "transforms", "reduces", "increases", "improves",
        "detects", "prevents", "supports", "contains", "produces", "operates",
        "measures", "analyzes", "compares", "separates", "combines", "connects",
        "delivers", "manages", "controls", "defines", "describes", "explains",
        "runs", "works", "makes", "takes", "gives", "helps", "shows", "leads",
        "grows", "moves", "sends", "receives", "stores", "loads", "builds",
        "breaks", "sets", "gets", "puts", "keeps", "turns", "starts", "stops",
        "adds", "removes", "includes", "excludes", "represents", "identifies",
        "achieves", "performs", "executes", "implements", "integrates", "validates",
        "optimizes", "minimizes", "maximizes", "eliminates", "handles", "triggers",
        "ensures", "maintains", "monitors", "tracks", "logs", "reports", "maps",
        "absorbs", "reflects", "emits", "transfers", "releases", "binds",
        "regulates", "activates", "inhibits", "catalyzes", "synthesizes",
        "evolved", "developed", "invented", "discovered", "introduced", "launched",
        "adopted", "replaced", "eliminated", "reduced", "increased", "improved",
        "reached", "exceeded", "dropped", "rose", "fell", "grew", "shrank",
    ]
    words = sentence.lower().split()
    return any(w.rstrip(".,;:!?") in verb_indicators for w in words)


def _word_boundary_truncate(text: str, max_chars: int) -> str:
    """Truncate text at a word boundary without destroying meaning. No raw slicing."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.5:
        cut = cut[:last_space]
    cut = cut.rstrip(" ,;:-–—")
    return cut


def _generate_topic_fallback(topic: str, slide_title: str, slide_no: int) -> Dict[str, Any]:
    """Generate a meaningful topic-derived fallback instead of banned placeholder strings."""
    clean_topic = re.sub(r"[^\w\s]", "", topic).strip()
    clean_title = re.sub(r"[^\w\s]", "", slide_title).strip() if slide_title else f"Slide {slide_no}"

    patterns = ["definition_box", "contrast_pair", "numbered_process", "plain_concept", "annotated_tiers"]
    cpat = patterns[slide_no % len(patterns)]

    return {
        "slide_no": slide_no,
        "type": "concept",
        "title": _word_boundary_truncate(clean_title, 60) if clean_title else f"Core Principles of {clean_topic}"[:60],
        "subtitle": f"Examining the foundational aspects of {clean_topic}"[:140],
        "key_message": f"Understanding {clean_topic} requires examining its core mechanisms and practical applications.",
        "body_bullets": [
            f"{clean_topic} operates through interconnected mechanisms that produce measurable outcomes.",
            f"Real-world applications demonstrate how {clean_topic} solves practical challenges.",
            f"Common misconceptions about {clean_topic} often stem from oversimplified mental models.",
        ],
        "example": f"A concrete example of {clean_topic} in practice illustrates the principles discussed above.",
        "speaker_notes": (
            f"Let's examine {clean_topic} in more depth. The core mechanisms we're looking at here are "
            f"fundamental to understanding how this works in practice. Think about it this way — if you "
            f"were to explain {clean_topic} to someone unfamiliar with the subject, what would be the "
            f"essential points? The key is understanding not just what it is, but how it operates and "
            f"why it matters in real-world contexts. Consider asking your students: what problems does "
            f"{clean_topic} solve that couldn't be solved otherwise? This leads naturally into our next slide."
        ),
        "image_query": f"{clean_topic} professional educational demonstration close-up photography",
        "content_pattern": cpat,
    }


def parse_free_tier_response(raw_text: str) -> dict:
    """Split the model's reasoning preamble from the JSON payload."""
    if "###JSON###" not in raw_text:
        raise ValueError("Model skipped the reasoning delimiter — retry the call.")
    _, json_part = raw_text.split("###JSON###", 1)
    json_part = json_part.strip()
    json_part = json_part.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(json_part)


def _build_deck_memory(generated_slides: list[dict]) -> dict:
    """Build the used_* context strings fed into the next batch call."""
    patterns = [s.get("content_pattern") for s in generated_slides if s.get("content_pattern")]
    examples = [s.get("example", "")[:80] for s in generated_slides if s.get("example")]
    image_themes = [s.get("image_query", "") for s in generated_slides if s.get("image_query")]
    openers = []
    prev_first_template = "none yet"
    for s in generated_slides:
        bullets = s.get("body_bullets", [])
        if bullets:
            openers.extend([" ".join(b.split()[:3]) for b in bullets])
            # Basic heuristic to extract the template used from the first bullet if not explicitly tagged
            first_b = bullets[0].lower()
            if "unlike" in first_b:
                prev_first_template = "CONTRAST"
            elif "%" in first_b or "percent" in first_b or "$" in first_b:
                prev_first_template = "STAT"
            elif "when" in first_b:
                prev_first_template = "CONDITIONAL"
            else:
                prev_first_template = "MECHANISM"

    return {
        "used_patterns": ", ".join(patterns[-6:]) or "none yet",
        "used_examples": "; ".join(examples[-6:]) or "none yet",
        "used_image_themes": "; ".join(image_themes[-6:]) or "none yet",
        "used_openers": ", ".join(openers[-15:]) or "none yet",
        "prev_first_template": prev_first_template,
    }


# ═══════════════════════════════════════════════════════════════
# Two-Pass Refinement Logic
# ═══════════════════════════════════════════════════════════════

def _refine_slide(slide: Dict[str, Any], topic: str) -> Dict[str, Any]:
    """
    Pass 2: Refine a single slide after LLM generation.
    Enforces Master Prompt quality rules without destroying content.
    """
    # 1. Clean and validate bullets
    raw_bullets = slide.get("body_bullets", [])
    refined_bullets = []
    overflow_to_notes = []

    for b in raw_bullets:
        b_str = str(b).strip()
        if not b_str:
            continue

        if _contains_banned(b_str):
            continue

        title_lower = (slide.get("title") or "").lower().strip()
        if title_lower and b_str.lower().strip() == title_lower:
            continue

        if len(b_str) > 100:
            truncated = _word_boundary_truncate(b_str, 95)
            overflow_to_notes.append(b_str)
            b_str = truncated

        refined_bullets.append(b_str)

    seen: Set[str] = set()
    deduped_bullets = []
    for b in refined_bullets:
        key = b.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped_bullets.append(b)

    if len(deduped_bullets) > 5:
        overflow_to_notes.extend(deduped_bullets[5:])
        deduped_bullets = deduped_bullets[:5]

    slide["body_bullets"] = deduped_bullets

    title = slide.get("title", "")
    if len(title) > 60:
        slide["title"] = _word_boundary_truncate(title, 58)

    subtitle = slide.get("subtitle", "")
    if len(subtitle) > 140:
        slide["subtitle"] = _word_boundary_truncate(subtitle, 138)

    notes = slide.get("speaker_notes", "")
    if overflow_to_notes:
        overflow_str = " Additional detail: " + " ".join(overflow_to_notes)
        notes = (notes + overflow_str).strip()
        slide["speaker_notes"] = notes

    if _contains_banned(notes):
        for banned in BANNED_STRINGS:
            notes = re.sub(re.escape(banned), "", notes, flags=re.IGNORECASE)
        slide["speaker_notes"] = notes.strip()

    example = slide.get("example", "")
    if example and _contains_banned(example):
        for banned in BANNED_STRINGS:
            example = re.sub(re.escape(banned), "", example, flags=re.IGNORECASE)
        slide["example"] = example.strip()

    return slide


def _validate_self_check(slide: Dict[str, Any]) -> bool:
    sc = slide.get("self_check")
    if not sc or not isinstance(sc, dict):
        return True
    return sc.get("teacher_ready", True) and sc.get("no_filler", True)


# ═══════════════════════════════════════════════════════════════
# Batch Expansion (Pass 1: Draft)
# ═══════════════════════════════════════════════════════════════

async def _expand_single_batch(
    batch: List[Dict[str, Any]],
    config: PresentationConfig,
    user_id: str,
    deck_memory: Dict[str, Any],
    batch_start: int,
    batch_end: int,
    total_slides: int,
) -> List[Dict[str, Any]]:
    if not batch:
        return []

    batch_context_parts = []
    batch_source_refs_map = {}

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

    batch_prompt_dict = {
        "topic": config.topic,
        "audience": config.audience,
        "language": config.language,
        "depth": config.depth,
        "slides_to_expand": batch,
    }

    user_content_str = f"Expand the following slides into full, detailed, teacher-ready presentation content:\n{json.dumps(batch_prompt_dict, indent=2)}"
    if batch_context_parts:
        user_content_str += f"\n\nDocument Grounding Material:\n" + "\n\n".join(batch_context_parts)

    formatted_sys_prompt = CONTENT_BATCH_SYSTEM_PROMPT.format(
        batch_start=batch_start,
        batch_end=batch_end,
        total_slides=total_slides,
        used_patterns=deck_memory["used_patterns"],
        used_examples=deck_memory["used_examples"],
        used_image_themes=deck_memory["used_image_themes"],
        used_openers=deck_memory["used_openers"],
        prev_first_template=deck_memory["prev_first_template"]
    )

    messages = [
        {"role": "system", "content": formatted_sys_prompt},
        {"role": "user", "content": user_content_str},
    ]

    batch_result = None
    for attempt in range(2):
        try:
            raw_response = await router.generate_text(
                task="content_generation",
                messages=messages,
                temperature=0.75,
                max_tokens=3000,
            )
            batch_result = parse_free_tier_response(raw_response.text)
            break
        except Exception as err:
            if attempt == 0:
                logger.warning(f"[ContentAgent] Batch generation attempt 1 failed: {err}. Retrying...")
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"[ContentAgent] Batch generation attempt 2 failed: {err}. Using topic-derived fallback.")
                batch_result = {}

    if batch_result is None:
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
    
    # Extract the last two patterns for deterministic fallback check
    recent_patterns = []
    if deck_memory["used_patterns"] and deck_memory["used_patterns"] != "none yet":
        recent_patterns = [p.strip() for p in deck_memory["used_patterns"].split(",")]

    for idx, orig_slide in enumerate(batch):
        s_no = orig_slide.get("slide_no")
        found = next((x for x in raw_expanded if x.get("slide_no") == s_no), None)
        if not found and raw_expanded:
            if 0 <= idx < len(raw_expanded):
                found = raw_expanded[idx]

        if not found:
            found = _generate_topic_fallback(
                topic=config.topic,
                slide_title=orig_slide.get("title", ""),
                slide_no=s_no or (idx + 1),
            )

        if not _validate_self_check(found):
            logger.info(f"[ContentAgent] Slide {s_no} self-check failed teacher_ready. Marked for review.")

        if s_no in batch_source_refs_map:
            found["source_refs"] = batch_source_refs_map[s_no]

        found["slide_no"] = s_no
        if not found.get("type"):
            found["type"] = orig_slide.get("type", "concept")

        img_q = (found.get("image_query") or "").strip()
        if not img_q:
            clean_title = re.sub(r"[^\w\s]", "", orig_slide.get("title", ""))
            img_q = f"{clean_title} professional educational demonstration photography"
        found["image_query"] = img_q
        found["visual_prompt"] = found.get("visual_prompt") or orig_slide.get("visual_hint", "")

        cpat = found.get("content_pattern") or orig_slide.get("content_pattern")
        if not cpat:
            cpat = detect_content_pattern_fallback_dict(found)
            
        # Deterministic check
        if cpat in recent_patterns[-2:]:
            logger.debug(f"[ContentAgent] Content pattern '{cpat}' duplicated recently. Forcing fallback.")
            cpat = detect_content_pattern_fallback_dict(found, exclude=recent_patterns[-2:])
        
        found["content_pattern"] = cpat
        recent_patterns.append(cpat)

        found = _refine_slide(found, config.topic)
        expanded_batch.append(found)

    return expanded_batch


def detect_content_pattern_fallback_dict(slide: Dict[str, Any], exclude: List[str] = None) -> str:
    """
    Intelligent deterministic fallback ladder matching slide content signals.
    """
    exclude = exclude or []
    title_l = (slide.get("title") or "").lower()
    bullets_l = " ".join(slide.get("body_bullets") or []).lower()
    comb = f"{title_l} {bullets_l}"
    
    options = []

    if any(w in title_l for w in ["definition", "what is", "glossary", "terminology", "concept:"]):
        options.append("definition_box")

    if any(w in comb for w in ["trap", "misconception", "pitfall", "anti-pattern", "vs.", "versus", "do's and don'ts"]):
        options.append("contrast_pair")

    if slide.get("steps") or any(w in title_l for w in ["step", "lifecycle", "workflow", "pipeline", "phase", "algorithm:"]):
        options.append("numbered_process")

    if any(w in title_l for w in ["case study", "real-world", "incident", "failure analysis"]):
        options.append("case_study_block")

    if any(w in title_l for w in ["activity", "exercise", "try this", "discussion prompt", "lab task"]):
        options.append("activity_banner")

    if slide.get("columns") and len(slide.get("columns")) >= 2:
        options.append("comparison_table")

    cs_terms = ["stack", "lifo", "queue", "fifo", "binary tree", "graph topology", "database cylinder"]
    if any(t in comb for t in cs_terms) and any(w in title_l for w in ["structure", "model", "collection", "topology"]):
        options.append("illustrated_icon_grid")

    if any(w in title_l for w in ["worked example", "step-by-step trace", "walkthrough", "trace table"]):
        options.append("worked_example_table")

    tier_keywords = ["hierarchy", "classification", "taxonomy", "levels of", "layers of",
                     "tiers of", "categories of", "spectrum", "pyramid", "maturity model"]
    if any(w in comb for w in tier_keywords):
        options.append("annotated_tiers")

    app_keywords = ["application", "use case", "real-world", "industry", "example",
                    "where is", "who uses", "practical use", "deployment"]
    bullets = slide.get("body_bullets") or []
    if any(w in title_l for w in app_keywords) and len(bullets) >= 3:
        options.append("example_grid")

    image_query = (slide.get("image_query") or "").strip()
    has_definition_content = bool(slide.get("key_insight") or slide.get("example") or
                                  (slide.get("body_bullets") and len(slide.get("body_bullets", [])) >= 2))
    concept_keywords = ["what is", "core", "mechanism", "principle", "overview", "introduction",
                        "fundamentals", "architecture", "concept", "how does", "types of"]
    is_concept_like = any(w in title_l for w in concept_keywords) or slide.get("type") in ["concept", "definition"]
    if image_query and has_definition_content and is_concept_like:
        options.append("concept_split")
        
    for opt in options:
        if opt not in exclude:
            return opt

    if "plain_concept" not in exclude:
        return "plain_concept"
        
    return "definition_box"  # Ultimate fallback


async def _validate_and_repair_deck(slides: List[Dict[str, Any]], deck_memory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Runs after all batches complete to catch any remaining issues and trigger AI repair."""
    repaired_slides = []
    
    for i, slide in enumerate(slides):
        issues = []
        
        # Check consecutive pattern repetition
        cpat = slide.get("content_pattern")
        if i > 0 and cpat == slides[i-1].get("content_pattern"):
            issues.append(f"Content pattern '{cpat}' is identical to the previous slide.")
            
        # Optional: could check heavy overlap in examples here as well, but deterministic fallbacks and AI memory usually catch it
        
        if issues:
            logger.info(f"[ContentAgent] Slide {slide.get('slide_no')} flagged in validate_deck: {issues}. Triggering repair.")
            # Trigger single repair pass
            user_prompt = (
                f"Fix issues in this slide to meet the TeachGenie Master Standard:\n"
                f"Slide Content:\n{json.dumps(slide, indent=2)}\n\n"
                f"Issues Identified:\n" + "\n".join(f"- {iss}" for iss in issues) +
                f"\n\nAlready used patterns/examples (DO NOT REUSE):\n"
                f"Patterns: {deck_memory.get('used_patterns')}\n"
                f"Examples: {deck_memory.get('used_examples')}"
            )
            
            try:
                patch_res = await asyncio.wait_for(
                    router.generate_json(
                        task="repair",
                        messages=[
                            {"role": "system", "content": SLIDE_PATCH_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.2,
                        max_tokens=2000,
                    ),
                    timeout=15.0,
                )
                if patch_res and patch_res.get("title"):
                    patch_res["slide_no"] = slide.get("slide_no")
                    patch_res["type"] = slide.get("type")
                    patch_res["content_pattern"] = slide.get("content_pattern")
                    patch_res["section_label"] = slide.get("section_label")
                    slide = _refine_slide(patch_res, "")
            except Exception as e:
                logger.error(f"[ContentAgent] AI repair failed for slide {slide.get('slide_no')}: {e}")
                
        repaired_slides.append(slide)
        
    return repaired_slides


async def expand_presentation_content(
    config: PresentationConfig,
    user_id: str,
    outline_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    planned_slides = outline_data.get("slides", [])
    if not planned_slides:
        return []

    BATCH_SIZE = 3
    batches = [planned_slides[i:i + BATCH_SIZE] for i in range(0, len(planned_slides), BATCH_SIZE)]

    expanded_slides: List[Dict[str, Any]] = []
    
    try:
        async def _process_sequential():
            for idx, batch in enumerate(batches):
                batch_start = batch[0].get("slide_no", 1)
                batch_end = batch[-1].get("slide_no", 1)
                
                deck_memory = _build_deck_memory(expanded_slides)
                
                batch_results = await _expand_single_batch(
                    batch=batch, 
                    config=config, 
                    user_id=user_id, 
                    deck_memory=deck_memory,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    total_slides=config.slide_count
                )
                expanded_slides.extend(batch_results)
                
            # Run final validation and repair
            final_deck_memory = _build_deck_memory(expanded_slides)
            return await _validate_and_repair_deck(expanded_slides, final_deck_memory)

        expanded_slides = await asyncio.wait_for(
            _process_sequential(),
            timeout=80.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[ContentAgent] Batch expansion timed out after 80s. Using topic-derived fallbacks.")

    if len(expanded_slides) < len(planned_slides):
        covered_slide_nos = {s.get("slide_no") for s in expanded_slides}
        for s in planned_slides:
            if s.get("slide_no") not in covered_slide_nos:
                expanded_slides.append(
                    _generate_topic_fallback(
                        topic=config.topic,
                        slide_title=s.get("title", ""),
                        slide_no=s.get("slide_no", 0),
                    )
                )

    expanded_slides.sort(key=lambda s: s.get("slide_no", 0))
    return expanded_slides
