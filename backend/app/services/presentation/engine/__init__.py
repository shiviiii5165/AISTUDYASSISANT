"""
Presentation Engine Package
===========================
"""
from .builder import build_presentation_spec
from .templates import TEMPLATE_ROUTER
from .diagrams import (
    render_flow_diagram,
    render_architecture_diagram,
    render_timeline_diagram,
    render_comparison_diagram,
)

__all__ = [
    "build_presentation_spec",
    "TEMPLATE_ROUTER",
    "render_flow_diagram",
    "render_architecture_diagram",
    "render_timeline_diagram",
    "render_comparison_diagram",
]
