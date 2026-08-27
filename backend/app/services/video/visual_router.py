"""
Visual Asset Decision & Budget Engine (Hardened)
================================================
Determines the most cost-effective, pedagogically sound visual path for each scene:
Hierarchy: Cached Asset -> Python/SVG Graphics -> Stock Media -> AI Image -> AI Video
Uses deterministic ai_video_score thresholding and AI Intensity controls.
"""
from typing import Dict, Any, Tuple
from .schemas import SceneSpec, VisualAssetType, VideoQuality, VisualBudget, VideoStyle, AIIntensity


def get_visual_budget_for_quality(
    quality: VideoQuality,
    total_duration: int,
    intensity: AIIntensity = AIIntensity.BALANCED,
) -> VisualBudget:
    """Configures deterministic media budgets based on quality tier and AI intensity."""
    if quality == VideoQuality.QUICK or intensity == AIIntensity.MINIMAL:
        return VisualBudget(
            max_ai_video_seconds=0,
            max_ai_image_count=2,
            max_stock_requests=6,
            quality_level=quality,
        )
    elif quality == VideoQuality.PREMIUM or intensity == AIIntensity.MAXIMUM:
        max_ai_sec = min(60, int(total_duration * 0.25))
        return VisualBudget(
            max_ai_video_seconds=max_ai_sec,
            max_ai_image_count=8,
            max_stock_requests=12,
            quality_level=quality,
        )
    else:  # STANDARD / BALANCED
        max_ai_sec = min(24, int(total_duration * 0.15))
        return VisualBudget(
            max_ai_video_seconds=max_ai_sec,
            max_ai_image_count=4,
            max_stock_requests=8,
            quality_level=quality,
        )


def calculate_ai_video_necessity_score(scene: SceneSpec) -> float:
    """
    Computes an educational AI-video necessity score (0.0 to 1.0):
    - Static definition: 0.02
    - Technical diagram: 0.05
    - Simple process: 0.10
    - Real-world demonstration: 0.45
    - Dynamic scientific process: 0.75
    - Cinematic visual hook: 0.95
    """
    purpose = scene.purpose.lower()
    spec = scene.visual_spec

    if spec.diagram_type or spec.formula or purpose in ["definition", "quiz"]:
        return 0.02
    elif purpose in ["mechanism", "diagram"]:
        return 0.05
    elif purpose in ["example", "demo"]:
        return 0.45
    elif purpose in ["simulation", "physics", "chemical_reaction"]:
        return 0.75
    elif purpose in ["hook", "hero", "cinematic"]:
        return 0.95
    return 0.10


def route_scene_visual_asset(
    scene: SceneSpec,
    quality: VideoQuality,
    budget: VisualBudget,
    current_ai_video_seconds: int = 0,
    current_ai_image_count: int = 0,
) -> Tuple[VisualAssetType, Dict[str, Any]]:
    """
    Evaluates scene requirements against budget constraints and selects optimal visual path.
    """
    score = calculate_ai_video_necessity_score(scene)
    scene.ai_video_score = score
    purpose = scene.purpose.lower()
    spec = scene.visual_spec

    # 1. Deterministic Python/SVG Graphics check (Always preferred for diagrams/formulas)
    if spec.diagram_type or spec.formula or score < 0.15:
        return VisualAssetType.PYTHON_GRAPHICS, {
            "engine": "python_graphics",
            "diagram_type": spec.diagram_type or "cards",
            "ai_video_score": score,
            "estimated_cost_usd": 0.0,
        }

    # 2. AI Video candidate (Hero/Hook scene with score >= 0.85 and within budget)
    if score >= 0.85 and (current_ai_video_seconds + scene.duration) <= budget.max_ai_video_seconds:
        if quality in [VideoQuality.STANDARD, VideoQuality.PREMIUM]:
            return VisualAssetType.AI_VIDEO, {
                "engine": "veo_ai_video",
                "duration": min(8, scene.duration),
                "ai_video_score": score,
                "estimated_cost_usd": 0.05,
            }

    # 3. Stock Media candidate (Real-world examples, contextual footage)
    if purpose in ["hook", "hero", "example", "intro", "outro", "summary"] or spec.stock_keywords or (0.30 <= score < 0.85):
        return VisualAssetType.STOCK_VIDEO, {
            "engine": "pexels_stock",
            "keywords": spec.stock_keywords or [scene.concept_id or "technology"],
            "ai_video_score": score,
            "estimated_cost_usd": 0.0,
        }

    # 4. AI Image candidate (Conceptual illustrations)
    if current_ai_image_count < budget.max_ai_image_count and quality != VideoQuality.QUICK:
        return VisualAssetType.AI_IMAGE, {
            "engine": "gemini_imagen",
            "prompt": spec.ai_prompt or f"Educational illustration representing {scene.caption or scene.purpose}",
            "ai_video_score": score,
            "estimated_cost_usd": 0.01,
        }

    # Fallback to Deterministic Python Graphic Cards
    return VisualAssetType.PYTHON_GRAPHICS, {
        "engine": "python_graphics",
        "diagram_type": "cards",
        "ai_video_score": score,
        "estimated_cost_usd": 0.0,
    }
