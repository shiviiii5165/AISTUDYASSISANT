"""
Planner Agent
=============
Plans the narrative arc and slide layout structure (10..17 slides).
Ingests the Topic Ontology checklist to guarantee complete pedagogical coverage.
Maps each core subtopic to at least one slide, merging closely related concepts
or flexing up to +2 slides when necessary to ensure zero dropped subtopics.
"""
from app.core.logging import logger
import json
import re
from typing import Dict, Any, List, Optional
from app.services.ai import router
from .schemas import PresentationConfig, SlideType
from .prompts import PLANNER_SYSTEM_PROMPT
from .topic_ontology_agent import generate_topic_ontology, TopicOntologyChecklist
from ..knowledge import get_topic_overview_context


def check_subtopic_coverage(core_subtopics: List[str], slides: List[Dict[str, Any]]) -> tuple[List[str], List[str]]:
    """
    Deterministic check: verifies which core subtopics are covered in planned slides
    via keyword overlap in title, key_message, and visual_hint.
    Returns (covered_subtopics, missing_subtopics).
    """
    covered = []
    missing = []
    
    # Concatenate all slide text into searchable text
    slide_texts = []
    for s in slides:
        text = f"{s.get('title', '')} {s.get('key_message', '')} {s.get('subtitle', '')}".lower()
        slide_texts.append(text)
    full_deck_text = " ".join(slide_texts)

    for subtopic in core_subtopics:
        # Extract meaningful keywords (>3 chars, ignore common stop words)
        words = [re.sub(r"[^\w]", "", w.lower()) for w in subtopic.split()]
        meaningful_words = [w for w in words if len(w) > 3 and w not in ["with", "from", "that", "this", "into", "over", "under", "about", "scope", "core", "mechanism"]]
        
        if not meaningful_words:
            covered.append(subtopic)
            continue

        # Check if at least 1 key term appears anywhere in the deck text
        is_covered = any(w in full_deck_text for w in meaningful_words)
        if is_covered:
            covered.append(subtopic)
        else:
            missing.append(subtopic)

    return covered, missing


def _build_deterministic_plan(config: PresentationConfig, ontology: TopicOntologyChecklist) -> Dict[str, Any]:
    """
    Deterministic fallback outline generator when LLM providers are unavailable or fail.
    Preserves exact structural planner invariants:
    - Hero slide at index 0.
    - Closing slide at index -1 (quiz or qa).
    - If core subtopics fit comfortably within target slide count (len(core_subtopics) < slide_count - 2),
      generates exactly config.slide_count slides with zero unnecessary expansion.
    - If core subtopics exceed/tightly fill slide count (len(core_subtopics) >= slide_count - 2),
      flexes up to config.slide_count + 2 to avoid dropping core subtopics.
    """
    slides = []

    # Hero Slide
    slides.append({
        "slide_no": 1,
        "type": "hero",
        "title": f"{config.topic}: Architecture & Foundations",
        "key_message": f"Core principles and pedagogical overview of {config.topic}.",
        "visual_hint": "diagram",
    })

    expansion_permitted = len(ontology.core_subtopics) >= (config.slide_count - 2)

    # Intermediate concept slides from ontology core subtopics
    for idx, subtopic in enumerate(ontology.core_subtopics):
        slides.append({
            "slide_no": len(slides) + 1,
            "type": "concept",
            "title": f"{subtopic}: Core Architecture & Mechanism",
            "key_message": f"Essential operational principles governing {subtopic} in {config.topic}.",
            "visual_hint": "diagram",
        })

    # If subtopic count fits comfortably, pad with structured concept slides up to target (target - 1 for closing)
    target_intermediate = config.slide_count - 2
    if len(ontology.core_subtopics) < target_intermediate:
        counter = len(ontology.core_subtopics) + 1
        while len(slides) < (config.slide_count - 1):
            slides.append({
                "slide_no": len(slides) + 1,
                "type": "concept",
                "title": f"Applied Analysis & Verification Part {counter}",
                "key_message": f"Deep-dive technical mechanics and edge-case validation for {config.topic}.",
                "visual_hint": "diagram",
            })
            counter += 1

    # Closing Slide
    closing_type = "quiz" if config.enable_quiz else "qa"
    slides.append({
        "slide_no": len(slides) + 1,
        "type": closing_type,
        "title": "Interactive Knowledge Check" if config.enable_quiz else "Q&A, Review & Key Takeaways",
        "key_message": f"Synthesis and mastery assessment for {config.topic}.",
        "visual_hint": "cards",
    })

    expansion_reason = ""
    if len(slides) > config.slide_count and expansion_permitted:
        expansion_reason = f"Expanded to {len(slides)} slides to provide complete coverage for {len(ontology.core_subtopics)} core subtopics"

    return {
        "deck_title": config.topic,
        "subtitle": f"{config.audience.title()} Level  •  {config.language.title()}",
        "slides": slides,
        "expansion_reason": expansion_reason,
    }


async def plan_presentation(
    config: PresentationConfig,
    user_id: str,
    custom_context: str = "",
    ontology: Optional[TopicOntologyChecklist] = None,
) -> Dict[str, Any]:
    """
    Generate an outline calibrated against the Topic Ontology checklist.
    Guarantees every core subtopic is mapped without silent omissions.
    """
    # 1. Obtain Topic Ontology Checklist (Step 0.5)
    if ontology is None:
        ontology = await generate_topic_ontology(config, user_id=user_id)

    # 2. Retrieve knowledge context if requested
    context_str = custom_context
    if not context_str and config.source_type in ["uploaded_material", "uploaded_material_plus_web"] and config.source_id:
        context_str = await get_topic_overview_context(
            document_id=config.source_id,
            user_id=user_id,
            topic=config.topic,
            max_chunks=10,
        )

    # 3. Format planner prompt with Topic Ontology injection
    closing_desc = "Interactive Knowledge Check Quiz" if config.enable_quiz else "Closing / Q&A & Open Discussion"
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        slide_count=config.slide_count,
        n_minus_1=config.slide_count - 1,
        n_minus_2=config.slide_count - 2,
        closing_slide_desc=closing_desc,
    )
    
    ontology_guidance = (
        "\n\nTOPIC ONTOLOGY COVERAGE CONTRACT:\n"
        "You must map every one of the following CORE SUBTOPICS into at least one slide:\n"
        + "\n".join(f"- {st}" for st in ontology.core_subtopics)
        + "\n\nMust include: " + "; ".join(ontology.must_include)
        + "\nIf slide count is tight, merge closely related subtopics onto one slide or expand by up to +2 slides. NEVER drop a core subtopic."
    )
    system_prompt += ontology_guidance

    if config.custom_context:
        system_prompt += (
            "\n\nIMPORTANT INSTRUCTION: Use the following source material to generate the outline. "
            "DO NOT fabricate facts beyond this provided context:\n\n"
            f"{config.custom_context}"
        )

    user_msg_parts = [
        f"Topic: {config.topic}",
        f"Target Audience: {config.audience}",
        f"Language: {config.language}",
        f"Depth: {config.depth}",
        f"Design System: {config.design.value if hasattr(config.design, 'value') else config.design}",
        f"Target Slide Count: {config.slide_count} (allowed flex up to {config.slide_count + 2} for full coverage)",
    ]
    if config.enable_quiz:
        user_msg_parts.append("Special Requirement: The final slide must be an interactive Quiz slide.")
    if context_str:
        user_msg_parts.append(f"\nDocument Reference Material:\n{context_str[:3000]}")

    user_prompt = "\n".join(user_msg_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4. Generate structured plan via ModelRouter with deterministic fallback
    try:
        plan_json = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
    except Exception as e:
        logger.warning(f"[Planner] LLM generation failed ({e}), using deterministic fallback outline")
        plan_json = _build_deterministic_plan(config, ontology)

    raw_slides = plan_json.get("slides", [])
    expansion_reason = plan_json.get("expansion_reason", "")

    # 5. Deterministic Coverage Audit & Repair
    expansion_permitted = len(ontology.core_subtopics) >= (config.slide_count - 2)
    max_allowed = (config.slide_count + 2) if expansion_permitted else config.slide_count

    covered, missing = check_subtopic_coverage(ontology.core_subtopics, raw_slides)

    if missing:
        logger.info(f"[Planner] {len(missing)} core subtopics initially unmapped: {missing}")
        # Repair: add or merge missing subtopics
        for m_sub in missing:
            if expansion_permitted and len(raw_slides) < max_allowed:
                # Add slide before closing slides
                insert_pos = max(1, len(raw_slides) - 2)
                raw_slides.insert(insert_pos, {
                    "slide_no": insert_pos + 1,
                    "type": "concept",
                    "title": f"{m_sub}: Core Architecture & Mechanism",
                    "key_message": f"Essential operational principles governing {m_sub} in {config.topic}.",
                    "visual_hint": "diagram",
                })
                expansion_reason = f"Expanded to {len(raw_slides)} slides to fully cover: {', '.join(missing)}"
            else:
                # Check if there is a generic placeholder slide to repurpose without increasing slide count
                repurposed = False
                for s in raw_slides[1:-1]:
                    s_title = s.get("title", "")
                    if any(s_title.startswith(prefix) for prefix in ["Key Principle", "Applied Analysis", "Overview"]):
                        s["title"] = f"{m_sub}: Core Architecture & Mechanism"
                        s["key_message"] = f"Essential operational principles governing {m_sub} in {config.topic}."
                        repurposed = True
                        break
                if not repurposed:
                    # Merge into the last concept slide
                    for s in reversed(raw_slides):
                        if s.get("type") in ["concept", "definition", "two_column"]:
                            s["title"] = f"{s.get('title', '')} & {m_sub}"[:100]
                            s["key_message"] = f"{s.get('key_message', '')} Covers {m_sub}."
                            break

    # 6. Slide Count Clamping strictly according to expansion allowance
    if len(raw_slides) > max_allowed:
        raw_slides = raw_slides[:max_allowed]
    elif len(raw_slides) < config.slide_count:
        while len(raw_slides) < config.slide_count:
            idx = len(raw_slides) + 1
            raw_slides.append({
                "slide_no": idx,
                "type": "concept",
                "title": f"Key Principle & Mechanism {idx}",
                "key_message": f"Core component analysis for {config.topic}",
                "visual_hint": "diagram",
            })

    if len(raw_slides) <= config.slide_count:
        expansion_reason = ""
    elif not expansion_reason and len(raw_slides) > config.slide_count:
        expansion_reason = f"Expanded to {len(raw_slides)} slides to provide complete coverage for {len(ontology.core_subtopics) if ontology else 0} core subtopics"

    # Renumber strictly 1..N
    for i, s in enumerate(raw_slides):
        s["slide_no"] = i + 1

    # Guarantee slide 1 is hero and closing slide matches requirement
    raw_slides[0]["type"] = "hero"
    raw_slides[0].pop("section_label", None)  # Hero never gets eyebrow tag
    if config.enable_quiz:
        raw_slides[-1]["type"] = "quiz"
        raw_slides[-1].pop("section_label", None)
    elif raw_slides[-1].get("type") not in ["summary", "qa"]:
        raw_slides[-1]["type"] = "qa"
    # Strip section_label from closing/summary/qa slides
    if raw_slides[-1].get("type") in ["qa", "summary", "quiz"]:
        raw_slides[-1].pop("section_label", None)

    plan_json["slides"] = raw_slides
    plan_json["expansion_reason"] = expansion_reason
    plan_json["topic_ontology"] = ontology.model_dump() if hasattr(ontology, "model_dump") else ontology.dict()
    if not plan_json.get("deck_title"):
        plan_json["deck_title"] = config.topic
    if not plan_json.get("subtitle"):
        plan_json["subtitle"] = f"{config.audience.title()} Level  •  {config.language.title()}"

    return plan_json
