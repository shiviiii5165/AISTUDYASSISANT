"""
Visual Agent
============
Determines visual strategies per slide.
Prefers deterministic Python diagram rendering (flowcharts, architectures, timelines, comparisons).
Only generates AI images when genuine explanatory value is added (capped at 2-4 per deck).
"""
import asyncio
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import PresentationConfig, VisualSpec, VisualKind, DiagramSpec


async def resolve_slide_visuals(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
    max_ai_images: int = 3,
) -> List[Dict[str, Any]]:
    """
    Analyzes and attaches visual specifications (diagrams or AI images) to each slide.
    """
    image_tasks = []
    image_slide_indices = []

    for i, slide in enumerate(slides):
        stype = slide.get("type", "concept")
        visual_prompt = slide.get("visual_prompt", "")
        visual_kind = VisualKind.NONE
        diagram_spec = None

        # 1. Check for Diagram opportunities (Deterministic Python preferred)
        if config.enable_diagrams:
            if stype in ["architecture", "concept"] and slide.get("layers"):
                visual_kind = VisualKind.ARCHITECTURE
                diagram_spec = DiagramSpec(
                    diagram_type="architecture",
                    title=slide.get("title", ""),
                    layers=slide.get("layers", []),
                )
            elif stype in ["process_flow", "concept"] and slide.get("steps"):
                visual_kind = VisualKind.FLOW
                diagram_spec = DiagramSpec(
                    diagram_type="flow",
                    title=slide.get("title", ""),
                    steps=slide.get("steps", []),
                )
            elif stype == "timeline" or slide.get("milestones"):
                visual_kind = VisualKind.TIMELINE
                diagram_spec = DiagramSpec(
                    diagram_type="timeline",
                    title=slide.get("title", ""),
                    milestones=slide.get("milestones", []),
                )
            elif stype == "comparison" or slide.get("columns"):
                visual_kind = VisualKind.COMPARISON
                diagram_spec = DiagramSpec(
                    diagram_type="comparison",
                    title=slide.get("title", ""),
                    columns=slide.get("columns", []),
                )

        # 2. Check for AI Image opportunities (Selective, max 2-4 per deck)
        if config.enable_images and visual_kind == VisualKind.NONE and visual_prompt:
            if stype in ["hero", "image_insight", "case_study"] and len(image_tasks) < max_ai_images:
                visual_kind = VisualKind.IMAGE
                image_tasks.append(router.generate_image(visual_prompt))
                image_slide_indices.append(i)

        # Attach initial visual spec
        slide["visual_spec"] = {
            "kind": visual_kind.value if hasattr(visual_kind, "value") else str(visual_kind),
            "asset_required": (visual_kind == VisualKind.IMAGE),
            "image_prompt": visual_prompt if visual_kind == VisualKind.IMAGE else "",
            "diagram_spec": diagram_spec.dict() if diagram_spec else None,
        }

    # 3. Resolve parallel AI images if any were requested
    if image_tasks:
        try:
            image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
            for idx, img_res in zip(image_slide_indices, image_results):
                if not isinstance(img_res, Exception) and img_res:
                    slides[idx]["visual_spec"]["image_bytes"] = img_res
        except Exception as e:
            print(f"[VisualAgent] Parallel image generation error: {e}")

    return slides
