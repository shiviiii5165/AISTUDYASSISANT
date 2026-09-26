"""
Presentation Services Package
=============================
"""
from .schemas import (
    SlideType, DesignSystem, VisualKind,
    PresentationConfig, SlideSpec, VisualSpec, DiagramSpec, SlideSourceRef, PresentationSpec,
    SemanticStatus, SemanticFailureReason, QualityGateError,
)
from .content_quality_auditor import (
    detect_incomplete_title,
    detect_ungrammatical_statement,
    sanitize_and_complete_title,
)
from .orchestrator import generate_presentation_pipeline
from .planner_agent import plan_presentation
from .content_agent import expand_presentation_content
from .visual_agent import resolve_slide_visuals
from .qa_agent import run_presentation_qa
from .cache import compute_presentation_hash, get_cached_presentation
from .composition_renderer import (
    render_composed_slide,
    render_composed_presentation,
    RenderResult,
    RenderDefectCode,
    audit_rendered_slide_editability,
)
from .chart_intelligence import (
    ChartType,
    ChartDataPayload,
    DataSeries,
    ChartRenderResult,
    ChartDefectCode,
    extract_chart_payload_from_content,
    validate_chart_type_suitability,
    select_appropriate_chart_type,
    render_native_chart,
)
from .diagram_intelligence import (
    DiagramArchetype,
    DiagramNode,
    DiagramConnector,
    DiagramSpec,
    DiagramRenderResult,
    select_diagram_archetype,
    build_diagram_spec,
    render_editable_diagram,
)
from .visual_router import (
    VisualRoutingDecision,
    VisualRoutingResult,
    route_visual_decision,
    audit_diagram_structure,
    repair_diagram_geometry,
)
from .rendering_adapter import (
    RenderBackendType,
    RenderedSlide,
    RenderingResult,
    PowerPointCOMRenderer,
    PowerPointPDFiumRenderer,
    MockOfflineRenderer,
    discover_available_backends,
)
from .rendered_visual_qa import (
    VisualDefectCode,
    DefectSeverity,
    RepairabilityType,
    VisualRepairStrategy,
    VisualCertificationOutcome,
    PixelEvidence,
    StructuralEvidence,
    RenderedVisualDefect,
    RenderedVisualAuditResult,
    DeckVisualAuditResult,
    VisualRepairAction,
)
from .visual_defect_detector import (
    VisualDefectDetector,
    DeckVisualConsistencyAuditor,
    bounds_to_pixels,
    calculate_relative_luminance,
    calculate_contrast_ratio,
)
from .visual_repair_engine import (
    VisualRepairEngine,
)

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
    "SemanticStatus",
    "SemanticFailureReason",
    "QualityGateError",
    "detect_incomplete_title",
    "detect_ungrammatical_statement",
    "sanitize_and_complete_title",
    "generate_presentation_pipeline",
    "plan_presentation",
    "expand_presentation_content",
    "resolve_slide_visuals",
    "run_presentation_qa",
    "compute_presentation_hash",
    "get_cached_presentation",
    "render_composed_slide",
    "render_composed_presentation",
    "RenderResult",
    "RenderDefectCode",
    "audit_rendered_slide_editability",
    "ChartType",
    "ChartDataPayload",
    "DataSeries",
    "ChartRenderResult",
    "ChartDefectCode",
    "extract_chart_payload_from_content",
    "validate_chart_type_suitability",
    "select_appropriate_chart_type",
    "render_native_chart",
    "DiagramArchetype",
    "DiagramNode",
    "DiagramConnector",
    "DiagramRenderResult",
    "select_diagram_archetype",
    "build_diagram_spec",
    "render_editable_diagram",
    "VisualRoutingDecision",
    "VisualRoutingResult",
    "route_visual_decision",
    "audit_diagram_structure",
    "repair_diagram_geometry",
    # Phase 3.5
    "RenderBackendType",
    "RenderedSlide",
    "RenderingResult",
    "PowerPointCOMRenderer",
    "PowerPointPDFiumRenderer",
    "MockOfflineRenderer",
    "discover_available_backends",
    "VisualDefectCode",
    "DefectSeverity",
    "RepairabilityType",
    "VisualRepairStrategy",
    "VisualCertificationOutcome",
    "PixelEvidence",
    "StructuralEvidence",
    "RenderedVisualDefect",
    "RenderedVisualAuditResult",
    "DeckVisualAuditResult",
    "VisualRepairAction",
    "VisualDefectDetector",
    "DeckVisualConsistencyAuditor",
    "bounds_to_pixels",
    "calculate_relative_luminance",
    "calculate_contrast_ratio",
    "VisualRepairEngine",
]

