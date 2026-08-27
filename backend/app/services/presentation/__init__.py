"""
Presentation Services Package
=============================
"""
from .schemas import (
    SlideType, DesignSystem, VisualKind,
    PresentationConfig, SlideSpec, VisualSpec, DiagramSpec, SlideSourceRef, PresentationSpec
)
from .orchestrator import generate_presentation_pipeline
from .planner_agent import plan_presentation
from .content_agent import expand_presentation_content
from .visual_agent import resolve_slide_visuals
from .qa_agent import run_presentation_qa
from .cache import compute_presentation_hash, get_cached_presentation

__all__ = [
    "SlideType",
    "DesignSystem",
    "VisualKind",
    "PresentationConfig",
    "SlideSpec",
    "VisualSpec",
    "DiagramSpec",
    "SlideSourceRef",
    "PresentationSpec",
    "generate_presentation_pipeline",
    "plan_presentation",
    "expand_presentation_content",
    "resolve_slide_visuals",
    "run_presentation_qa",
    "compute_presentation_hash",
    "get_cached_presentation",
]
