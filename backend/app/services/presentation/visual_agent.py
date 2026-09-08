"""
Visual Agent
============
Determines visual strategies per slide.
Prefers deterministic Python diagram rendering (flowcharts, architectures, timelines, comparisons).
Selectively attaches high-relevance stock photography (capped at 2-4 per deck)
via the new ImageService (Pexels → Pixabay → Unsplash → Wikimedia, health-based routing).
Guarantees clean deterministic fallbacks when images cannot be resolved.
"""
from app.core.logging import logger
import asyncio
from typing import List, Dict, Any, Optional
from .schemas import PresentationConfig, VisualSpec, VisualKind, DiagramSpec


async def resolve_slide_visuals(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
    max_images: int = 3,
) -> List[Dict[str, Any]]:
    """
    Analyzes and attaches visual specifications (diagrams or stock photos) to each slide.
    Concurrently fetches images for eligible slides using the ImageService.
    """
    image_tasks = []
    image_slide_indices = []

    # ═══════════════════════════════════════════════════════════════════════
    # Deck-Level Visual Style Decision (consistent visual cohesion)
    # ═══════════════════════════════════════════════════════════════════════
    topic_lower = config.topic.lower()

    # Abstract/conceptual topics → prefer illustration-style visuals
    illustration_signals = ["algorithm", "theory", "abstract", "logic", "mathematics",
                            "philosophy", "paradigm", "pattern", "principle", "model",
                            "framework", "computation", "automata", "formal"]
    # Concrete/physical topics → prefer stock photography
    photo_signals = ["biology", "chemistry", "engineering", "medicine", "anatomy",
                     "ecology", "geology", "architecture", "manufacturing", "agriculture",
                     "food", "sports", "transport", "cooking", "wildlife", "ocean"]

    illustration_score = sum(1 for s in illustration_signals if s in topic_lower)
    photo_score = sum(1 for s in photo_signals if s in topic_lower)

    if illustration_score > photo_score:
        deck_visual_style = "illustration"
    elif photo_score > illustration_score:
        deck_visual_style = "stock_photo"
    else:
        deck_visual_style = "stock_photo"  # Default to stock photo for most topics

    logger.info(f"[VisualAgent] Deck visual style: {deck_visual_style} "
                f"(illustration={illustration_score}, photo={photo_score})")

    # Consistent framing: all images in a deck use the same corner radius
    DECK_CORNER_RADIUS = 0.12  # inches — applied consistently to all images

    # Lazy-load ImageService to avoid import-time initialization
    image_service = None
    if config.enable_images:
        try:
            from app.services.image_service.service import ImageService
            image_service = ImageService.get_instance()
        except Exception as e:
            logger.warning(f"[VisualAgent] Could not initialize ImageService: {e}. Falling back to legacy router.")
            # Fallback to legacy router if ImageService fails to initialize
            try:
                from .image_source_router import resolve_stock_image
                image_service = None  # will use legacy path below
            except Exception:
                pass

    for i, slide in enumerate(slides):
        stype = slide.get("type", "concept")
        image_query = (slide.get("image_query") or slide.get("visual_prompt") or "").strip()
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

        # 2. Check for Stock Photo opportunities (Selective, max 2-4 per deck)
        # Avoid hero (template headers don't render hero images) and closing slides
        if config.enable_images and visual_kind == VisualKind.NONE and image_query:
            is_image_candidate = stype in ["image_insight", "case_study", "two_column"] or (
                stype == "concept" and not slide.get("example") and len(image_tasks) < max_images
            )
            if is_image_candidate and len(image_tasks) < max_images and stype not in ["hero", "qa", "summary"]:
                visual_kind = VisualKind.IMAGE

                if image_service:
                    # Use new ImageService with slide-aware query generation
                    image_tasks.append(
                        image_service.get_best_image_for_slide(
                            slide,
                            topic=config.topic,
                            aspect_ratio="landscape",
                        )
                    )
                else:
                    # Legacy fallback path
                    try:
                        from .image_source_router import resolve_stock_image
                        image_tasks.append(resolve_stock_image(image_query))
                    except Exception:
                        image_tasks.append(asyncio.coroutine(lambda: None)())

                image_slide_indices.append(i)

        # Attach initial visual spec with deck-level style metadata
        slide["visual_spec"] = {
            "kind": visual_kind.value if hasattr(visual_kind, "value") else str(visual_kind),
            "asset_required": (visual_kind == VisualKind.IMAGE),
            "image_prompt": image_query if visual_kind == VisualKind.IMAGE else "",
            "diagram_spec": diagram_spec.dict() if diagram_spec else None,
            "image_bytes": None,
            "deck_visual_style": deck_visual_style,
            "corner_radius_inches": DECK_CORNER_RADIUS,
        }

    # 3. Concurrently resolve stock photos for selected slides (hard 30s cap)
    if image_tasks:
        logger.info(f"[VisualAgent] Concurrently resolving {len(image_tasks)} stock photos...")
        try:
            image_results = await asyncio.wait_for(
                asyncio.gather(*image_tasks, return_exceptions=True),
                timeout=30.0,
            )
            for idx, img_res in zip(image_slide_indices, image_results):
                slide = slides[idx]
                if isinstance(img_res, Exception) or img_res is None:
                    # Explicit fallback to clean text layout
                    err_note = str(img_res) if isinstance(img_res, Exception) else "no match"
                    logger.info(f"[VisualAgent] Slide {idx+1} stock image not available ({err_note}). Falling back to clean text layout.")
                    slide["visual_spec"]["kind"] = VisualKind.NONE.value
                    slide["visual_spec"]["asset_required"] = False
                    continue

                # Handle new ImageResult objects from ImageService
                if hasattr(img_res, "image_bytes"):
                    # New ImageService result (ImageResult dataclass)
                    slide["visual_spec"]["image_bytes"] = img_res.image_bytes
                    slide["image_bytes"] = img_res.image_bytes  # backward compatibility alias
                    # Store attribution metadata for downstream rendering
                    slide["image_attribution"] = {
                        "photographer_name": img_res.attribution.photographer_name,
                        "photographer_url": img_res.attribution.photographer_url,
                        "source_url": img_res.attribution.source_url,
                        "provider": img_res.provider,
                        "license_type": img_res.attribution.license_type,
                    }
                    slide["image_query_used"] = img_res.query
                    logger.info(
                        f"[VisualAgent] Attached {len(img_res.image_bytes)} bytes from {img_res.provider} "
                        f"to slide {idx+1} ('{slide.get('title', '')[:30]}')"
                    )
                elif isinstance(img_res, bytes):
                    # Legacy resolve_stock_image returns raw bytes
                    slide["visual_spec"]["image_bytes"] = img_res
                    slide["image_bytes"] = img_res  # backward compatibility alias
                    logger.info(f"[VisualAgent] Attached {len(img_res)} image bytes to slide {idx+1} ('{slide.get('title', '')[:30]}')")
                else:
                    slide["visual_spec"]["kind"] = VisualKind.NONE.value
                    slide["visual_spec"]["asset_required"] = False

        except asyncio.TimeoutError:
            logger.warning(f"[VisualAgent] Image resolution timed out after 30s. Falling back to text layouts for all {len(image_tasks)} pending images.")
            for idx in image_slide_indices:
                slide = slides[idx]
                slide["visual_spec"]["kind"] = VisualKind.NONE.value
                slide["visual_spec"]["asset_required"] = False
        except Exception as e:
            logger.error(f"[VisualAgent] Batch image resolution error: {e}")

    return slides
