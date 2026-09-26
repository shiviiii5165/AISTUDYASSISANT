"""
LearnByGenie PPT vNext — Phase 3.5 Rendered Visual QA Models & Audit Contracts
=============================================================================
Defines strongly typed models, enums, evidence contracts, and audit outcomes
for rendered visual quality assurance of exported PowerPoint presentations.

Governed by LearnByGenie PPT vNext Phase 3.5 specifications:
  - Strongly typed defect taxonomy (27 visual defect codes)
  - Pixel and structural evidence models with reproducible metrics
  - Transactional repair action provenance records
  - Honest multi-level certification (STRUCTURAL_QA_PASS, RENDERED_QA_PASS, HUMAN_VISUAL_REVIEW_REQUIRED)
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, List, Tuple, Dict, Any
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# 1. DEFECT TAXONOMY & ENUMS (27 CODES)
# ═══════════════════════════════════════════════════════════════

class VisualDefectCode(str, Enum):
    """
    Authoritative Phase 3.5 Visual Defect Taxonomy.
    Every visual defect detected during rendered QA must map to one of these codes.
    """
    # Typography & Text Fit
    TEXT_CLIPPED                  = "TEXT_CLIPPED"
    TITLE_CLIPPED                 = "TITLE_CLIPPED"
    TEXT_RENDER_OVERFLOW          = "TEXT_RENDER_OVERFLOW"
    FONT_SUBSTITUTION_OVERFLOW    = "FONT_SUBSTITUTION_OVERFLOW"
    TEXT_TOO_SMALL_TO_READ        = "TEXT_TOO_SMALL_TO_READ"
    LINE_SPACING_COLLISION        = "LINE_SPACING_COLLISION"
    TITLE_BODY_VISUAL_COLLISION   = "TITLE_BODY_VISUAL_COLLISION"
    VISUAL_OBJECT_OVERLAP         = "VISUAL_OBJECT_OVERLAP"

    # Native Charts
    CHART_LABEL_COLLISION         = "CHART_LABEL_COLLISION"
    CHART_AXIS_LABEL_CLIPPED      = "CHART_AXIS_LABEL_CLIPPED"
    CHART_LEGEND_COLLISION        = "CHART_LEGEND_COLLISION"

    # Diagrams & Connectors
    DIAGRAM_NODE_COLLISION        = "DIAGRAM_NODE_COLLISION"
    DIAGRAM_CONNECTOR_OBSCURED    = "DIAGRAM_CONNECTOR_OBSCURED"
    DIAGRAM_LABEL_CLIPPED         = "DIAGRAM_LABEL_CLIPPED"
    ARROWHEAD_OBSCURED            = "ARROWHEAD_OBSCURED"

    # Visual Assets & Images
    IMAGE_SUBJECT_CROPPED         = "IMAGE_SUBJECT_CROPPED"
    IMAGE_STRETCHED               = "IMAGE_STRETCHED"
    IMAGE_RESOLUTION_INSUFFICIENT = "IMAGE_RESOLUTION_INSUFFICIENT"
    IMAGE_ATTRIBUTION_CLIPPED     = "IMAGE_ATTRIBUTION_CLIPPED"
    CITATION_UNREADABLE           = "CITATION_UNREADABLE"

    # Contrast & Color
    INSUFFICIENT_TEXT_CONTRAST    = "INSUFFICIENT_TEXT_CONTRAST"

    # Composition & Layout
    POOR_VISUAL_HIERARCHY         = "POOR_VISUAL_HIERARCHY"
    UNINTENDED_EMPTY_REGION       = "UNINTENDED_EMPTY_REGION"
    VISUAL_DENSITY_EXCESSIVE      = "VISUAL_DENSITY_EXCESSIVE"
    UNEXPECTED_FONT_RENDERING     = "UNEXPECTED_FONT_RENDERING"
    PALETTE_INCONSISTENCY         = "PALETTE_INCONSISTENCY"
    SLIDE_EDGE_CLIPPING           = "SLIDE_EDGE_CLIPPING"


class DefectSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # Renders slide illegible, severely corrupted, or clipped off-canvas
    MAJOR    = "MAJOR"      # Noticeable rendering defect (overlap, unreadable small text, low contrast)
    MINOR    = "MINOR"      # Subtle visual defect (tight margins, slight spacing imbalance)
    WARNING  = "WARNING"    # Heuristic warning / review recommended


class RepairabilityType(str, Enum):
    AUTOMATIC               = "AUTOMATIC"                # Can be boundedly repaired automatically
    MANUAL_REVIEW_REQUIRED  = "MANUAL_REVIEW_REQUIRED"   # Needs human editor inspection
    REFLOW_REQUIRED         = "REFLOW_REQUIRED"          # Requires layout compiler reflow
    UNREPAIRABLE            = "UNREPAIRABLE"             # Hard structural/semantic constraint cannot fit


class VisualRepairStrategy(str, Enum):
    EXPAND_TEXT_FRAME       = "expand_text_frame"        # Expand box height/width into available gutter
    SHRINK_FONT_SIZE        = "shrink_font_size"         # Bounded reduction of font size
    ADJUST_PADDING          = "adjust_padding"           # Reduce internal margins
    SHIFT_REGION            = "shift_region"             # Relocate region within constraint envelope
    REPOSITION_LEGEND       = "reposition_legend"        # Move chart legend to prevent collision
    REPOSITION_DIAGRAM_NODES = "reposition_diagram_nodes" # Increase node clearance
    ADJUST_IMAGE_CROP       = "adjust_image_crop"        # Switch to fit/crop_center to fix stretch
    ADD_CONTRAST_SURFACE    = "add_contrast_surface"     # Add opaque/translucent backing surface
    REPLACE_IMAGE_ASSET     = "replace_image_asset"      # Switch to alternative verified asset
    REFLOW_LAYOUT           = "reflow_layout"            # Re-invoke layout compiler with tighter density
    NOOP                    = "noop"                     # No safe repair available


class VisualCertificationOutcome(str, Enum):
    STRUCTURAL_QA_PASS          = "STRUCTURAL_QA_PASS"
    RENDERED_QA_PASS            = "RENDERED_QA_PASS"
    HUMAN_VISUAL_REVIEW_REQUIRED = "HUMAN_VISUAL_REVIEW_REQUIRED"


# ═══════════════════════════════════════════════════════════════
# 2. EVIDENCE MODELS
# ═══════════════════════════════════════════════════════════════

class PixelEvidence(BaseModel):
    """Objective, reproducible pixel measurements from rendered slide image."""
    box_px: Optional[Tuple[int, int, int, int]] = None       # (x, y, w, h) in pixels
    foreground_color_rgb: Optional[Tuple[int, int, int]] = None
    background_color_rgb: Optional[Tuple[int, int, int]] = None
    measured_contrast_ratio: Optional[float] = None
    overlap_box_px: Optional[Tuple[int, int, int, int]] = None
    edge_distance_px: Optional[int] = None
    measured_density_ratio: Optional[float] = None
    patch_hash: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class StructuralEvidence(BaseModel):
    """Authoritative structural attributes from PPTX and CompositionPlan."""
    region_id: Optional[str] = None
    shape_id: Optional[int] = None
    shape_name: Optional[str] = None
    allocated_bounds_in: Optional[Tuple[float, float, float, float]] = None  # (left, top, width, height)
    allocated_bounds_px: Optional[Tuple[int, int, int, int]] = None          # (x, y, w, h)
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    line_count: Optional[int] = None
    character_count: Optional[int] = None
    text_snippet: Optional[str] = None
    aspect_ratio_deviation: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# 3. DEFECT & AUDIT RESULT CONTRACTS
# ═══════════════════════════════════════════════════════════════

class RenderedVisualDefect(BaseModel):
    """Strongly typed model representing a verified visual defect on a rendered slide."""
    slide_no: int
    defect_code: VisualDefectCode
    severity: DefectSeverity
    affected_region_ids: List[str] = Field(default_factory=list)
    affected_shape_ids: List[int] = Field(default_factory=list)
    pixel_evidence: Optional[PixelEvidence] = None
    structural_evidence: Optional[StructuralEvidence] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    repairability: RepairabilityType = RepairabilityType.AUTOMATIC
    recommended_repair: VisualRepairStrategy = VisualRepairStrategy.NOOP
    message: str


class RenderedVisualAuditResult(BaseModel):
    """Visual audit findings for a single rendered slide."""
    slide_no: int
    renderer_backend: str = ""
    renderer_version: str = ""
    render_resolution: Tuple[int, int] = (1920, 1080)
    defects: List[RenderedVisualDefect] = Field(default_factory=list)
    warnings: List[RenderedVisualDefect] = Field(default_factory=list)
    fatal_defects: List[RenderedVisualDefect] = Field(default_factory=list)
    visual_valid: bool = True
    repair_required: bool = False
    unverified_checks: List[str] = Field(default_factory=list)
    audit_latency_ms: float = 0.0
    rendered_image_path: Optional[str] = None

    def update_validity(self) -> None:
        """Updates validity status based on collected defects."""
        self.fatal_defects = [d for d in self.defects if d.severity == DefectSeverity.CRITICAL]
        self.warnings = [d for d in self.defects if d.severity == DefectSeverity.WARNING]
        self.visual_valid = len(self.fatal_defects) == 0 and len([d for d in self.defects if d.severity == DefectSeverity.MAJOR]) == 0
        self.repair_required = not self.visual_valid


class DeckVisualAuditResult(BaseModel):
    """Visual audit report across an entire multi-slide presentation deck."""
    total_slides: int = 0
    audited_slides: int = 0
    slides_valid: int = 0
    total_defects: int = 0
    total_warnings: int = 0
    total_fatal_defects: int = 0
    deck_valid: bool = True
    renderer_backend: str = ""
    renderer_version: str = ""
    slide_results: List[RenderedVisualAuditResult] = Field(default_factory=list)
    deck_defects: List[RenderedVisualDefect] = Field(default_factory=list)
    deck_consistency_score: float = 100.0
    execution_time_ms: float = 0.0
    verification_outcome: VisualCertificationOutcome = VisualCertificationOutcome.STRUCTURAL_QA_PASS
    notes: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 4. REPAIR PROVENANCE CONTRACT (SECTION 18)
# ═══════════════════════════════════════════════════════════════

class VisualRepairAction(BaseModel):
    """
    Immutable provenance record documenting a single targeted visual repair action.
    Maintains before/after states, hashes, and commit/rollback decisions.
    """
    slide_no: int
    defect_code: VisualDefectCode
    affected_region_ids: List[str] = Field(default_factory=list)
    affected_shape_ids: List[int] = Field(default_factory=list)
    repair_strategy: VisualRepairStrategy
    before_geometry: Dict[str, Any] = Field(default_factory=dict)
    after_geometry: Dict[str, Any] = Field(default_factory=dict)
    before_render_reference: Optional[str] = None
    after_render_reference: Optional[str] = None
    defect_resolved: bool = False
    new_defects: List[str] = Field(default_factory=list)
    content_hashes_before: Dict[str, str] = Field(default_factory=dict)
    content_hashes_after: Dict[str, str] = Field(default_factory=dict)
    commit_status: str = "COMMITTED"  # COMMITTED | ROLLED_BACK | SKIPPED
    rollback_reason: Optional[str] = None
    repair_latency_ms: float = 0.0
