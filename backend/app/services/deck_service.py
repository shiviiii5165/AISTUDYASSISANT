"""
Deck Service — Bridge & Orchestration Support
==============================================
Provides legacy 3-step endpoint compatibility and direct orchestration functions.
"""
from app.core.logging import logger
import json
import asyncio
from typing import Dict, Any, List, Optional
from app.db.supabase_client import supabase
from app.services.ai import router
from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.planner_agent import plan_presentation
from app.services.presentation.content_agent import expand_presentation_content
from app.services.presentation.visual_agent import resolve_slide_visuals
from app.services.presentation.qa_agent import run_presentation_qa
from app.services.presentation.orchestrator import generate_presentation_pipeline
from app.services.ppt_renderer import generate_pptx_bytes


async def generate_outline_step(
    topic: str,
    depth: str = "full",
    audience: str = "university",
    slide_count: int = 12,
    design: str = "academic",
    theme: str = "blue_professional",
    source_type: str = "general",
    source_id: Optional[str] = None,
    user_id: str = "",
) -> Dict[str, Any]:
    """Step 1: Generate N-slide outline."""
    config = PresentationConfig(
        topic=topic,
        slide_count=slide_count if slide_count in [10, 11, 12, 13, 14, 15] else 12,
        audience=audience,
        depth=depth,
        design=DesignSystem(design) if design in [e.value for e in DesignSystem] else DesignSystem.ACADEMIC_CLEAN,
        theme=theme,
        source_type=source_type,
        source_id=source_id,
    )
    return await plan_presentation(config, user_id=user_id)


async def expand_outline_step(
    topic: str,
    audience: str,
    outline_data: Dict[str, Any],
    slide_count: int = 12,
    source_type: str = "general",
    source_id: Optional[str] = None,
    user_id: str = "",
) -> Dict[str, Any]:
    """Step 2: Expand outline to full slide content in 5-slide batches."""
    config = PresentationConfig(
        topic=topic,
        slide_count=slide_count if slide_count in [10, 11, 12, 13, 14, 15] else len(outline_data.get("slides", [])) or 12,
        audience=audience,
        source_type=source_type,
        source_id=source_id,
    )
    expanded_slides = await expand_presentation_content(config, user_id=user_id, outline_data=outline_data)
    
    return {
        "deck_title": outline_data.get("deck_title", topic),
        "subtitle": outline_data.get("subtitle", ""),
        "key_takeaways": outline_data.get("key_takeaways", []),
        "slides": expanded_slides,
        "sections": expanded_slides,  # backward compatibility alias
    }


async def quality_review_step(
    topic: str,
    audience: str,
    expanded_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Step 2.5: AI & Python QA pass on expanded content."""
    slides = expanded_data.get("slides") or expanded_data.get("sections") or []
    config = PresentationConfig(
        topic=topic,
        slide_count=len(slides) if len(slides) in [10, 11, 12, 13, 14, 15] else 12,
        audience=audience,
    )
    reviewed_slides = await run_presentation_qa(config, slides)
    expanded_data["slides"] = reviewed_slides
    expanded_data["sections"] = reviewed_slides
    return expanded_data


async def render_deck_step(
    deck_id: str,
    user_id: str,
    topic: str,
    depth: str,
    audience: str,
    final_deck_json: Dict[str, Any],
    design: str = "academic",
    theme: str = "blue_professional",
) -> str:
    """Step 3: Resolve visuals, render PPTX, upload to Supabase storage, update DB."""
    slides = final_deck_json.get("slides") or final_deck_json.get("sections") or []
    slide_count = len(slides) if len(slides) in [10, 11, 12, 13, 14, 15] else 12
    
    config = PresentationConfig(
        topic=topic,
        slide_count=slide_count,
        audience=audience,
        depth=depth,
        design=DesignSystem(design) if design in [e.value for e in DesignSystem] else DesignSystem.ACADEMIC_CLEAN,
        theme=theme,
    )

    # 1. Resolve visuals and diagrams
    slides_with_visuals = await resolve_slide_visuals(config, slides)
    final_deck_json["slides"] = slides_with_visuals
    final_deck_json["sections"] = slides_with_visuals

    # 2. Render PPTX bytes
    pptx_bytes = await generate_pptx_bytes(final_deck_json, audience=audience)

    # 3. Upload to Supabase Storage
    file_path = f"{user_id}/{deck_id}.pptx"
    try:
        supabase.storage.from_("topic-decks").upload(
            file_path,
            pptx_bytes,
            {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
        )
    except Exception as storage_err:
        logger.info(f"[DeckService] Storage upload note: {storage_err}")

    # 4. Update topic_decks DB record
    supabase.table("topic_decks").update({
        "status": "ready",
        "storage_path": file_path,
        "slide_count": len(slides)
    }).eq("id", deck_id).execute()

    return file_path
