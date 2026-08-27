"""
Design Templates Package
========================
Maps DesignSystem enum to deterministic Python template renderers.
"""
from .academic import render_academic_slide
from .minimal import render_minimal_slide
from .technical import render_technical_slide
from .editorial import render_editorial_slide
from .visual_learning import render_visual_learning_slide

TEMPLATE_ROUTER = {
    "academic": render_academic_slide,
    "minimal": render_minimal_slide,
    "technical": render_technical_slide,
    "editorial": render_editorial_slide,
    "visual": render_visual_learning_slide,
}

__all__ = [
    "TEMPLATE_ROUTER",
    "render_academic_slide",
    "render_minimal_slide",
    "render_technical_slide",
    "render_editorial_slide",
    "render_visual_learning_slide",
]
