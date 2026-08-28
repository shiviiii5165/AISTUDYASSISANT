"""
Planner Agent
=============
Plans the narrative arc and exact N-slide layout structure (10..15 slides).
Decides the pedagogical sequencing, slide purposes, and visual hints without
generating verbose content yet (saving tokens).
"""
import json
from typing import Dict, Any, List, Optional
from app.services.ai import router
from .schemas import PresentationConfig, SlideType
from .prompts import PLANNER_SYSTEM_PROMPT
from ..knowledge import get_topic_overview_context


async def plan_presentation(
    config: PresentationConfig,
    user_id: str,
    custom_context: str = "",
) -> Dict[str, Any]:
    """
    Generate an outline for EXACTLY config.slide_count slides.
    Uses hybrid knowledge retrieval if uploaded material is selected.
    """
    # 1. Retrieve knowledge context if requested
    context_str = custom_context
    if not context_str and config.source_type in ["uploaded_material", "uploaded_material_plus_web"] and config.source_id:
        context_str = await get_topic_overview_context(
            document_id=config.source_id,
            user_id=user_id,
            topic=config.topic,
            max_chunks=10,
        )

    # 2. Format planner prompt
    closing_desc = "Interactive Knowledge Check Quiz" if config.enable_quiz else "Closing / Q&A & Open Discussion"
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        slide_count=config.slide_count,
        n_minus_1=config.slide_count - 1,
        n_minus_2=config.slide_count - 2,
        closing_slide_desc=closing_desc,
    )
    
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
        f"Exact Slides Required: {config.slide_count}",
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

    # 3. Generate structured plan via ModelRouter
    plan_json = await router.generate_json(
        task="planning",
        messages=messages,
        temperature=0.3,
        max_tokens=4000,
    )

    # 4. Strict Validation & Repair of Exact Slide Count
    raw_slides = plan_json.get("slides", [])

    # If count mismatch, adjust strictly to config.slide_count
    if len(raw_slides) > config.slide_count:
        raw_slides = raw_slides[:config.slide_count]
    elif len(raw_slides) < config.slide_count:
        # Fill missing intermediate slides
        while len(raw_slides) < config.slide_count:
            idx = len(raw_slides) + 1
            raw_slides.append({
                "slide_no": idx,
                "type": "concept",
                "title": f"Key Principle & Mechanism {idx}",
                "key_message": f"Core component analysis for {config.topic}",
                "visual_hint": "diagram",
            })

    # Ensure correct numbering 1..N
    for i, s in enumerate(raw_slides):
        s["slide_no"] = i + 1

    # Ensure slide 1 is hero and slide N matches requirement
    raw_slides[0]["type"] = "hero"
    if config.enable_quiz:
        raw_slides[-1]["type"] = "quiz"
    elif raw_slides[-1].get("type") not in ["summary", "qa"]:
        raw_slides[-1]["type"] = "qa"

    plan_json["slides"] = raw_slides
    if not plan_json.get("deck_title"):
        plan_json["deck_title"] = config.topic
    if not plan_json.get("subtitle"):
        plan_json["subtitle"] = f"{config.audience.title()} Level  •  {config.language.title()}"

    return plan_json
