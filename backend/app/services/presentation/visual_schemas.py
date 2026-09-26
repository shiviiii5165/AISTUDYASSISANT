"""
LearnByGenie vNEXT Phase 3.1 — Visual Planning Schemas
=====================================================
Typed models governing visual semantic interpretation, design grammar,
and visual rhythm orchestration.

Governance:
  - Phase 1 & Phase 2 schemas in schemas.py are FROZEN — never imported
    from here, only referenced for adapter conversion.
  - All relationship/hierarchy structures use typed models, not Dict[str, str].
  - VisualIntent, VisualAssetType, and Phase3LayoutFamily are orthogonal.
  - ContentDensity is reused from schemas.py (shared vocabulary).
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Reuse Phase 1/2 frozen enums needed for adapters and shared vocabulary
from .schemas import (
    ContentDensity,
    LayoutFamily,
    VisualKind,
    SlideIntent,
    VisualTypeHint,
    VisualSpec,
    DiagramSpec,
)


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Intent Enum
# ═══════════════════════════════════════════════════════════════

class VisualIntent(str, Enum):
    """Semantic visual purpose — HOW the idea should be communicated visually.
    Orthogonal to SlideIntent (WHY the slide exists) and Phase3LayoutFamily
    (WHERE objects sit spatially)."""
    EXPLAIN_STRUCTURE         = "explain_structure"
    SHOW_PROCESS              = "show_process"
    SHOW_CAUSALITY            = "show_causality"
    COMPARE                   = "compare"
    SHOW_TIMELINE             = "show_timeline"
    SHOW_HIERARCHY            = "show_hierarchy"
    SHOW_DATA_PATTERN         = "show_data_pattern"
    SHOW_TRANSFORMATION       = "show_transformation"
    SHOW_SYSTEM_ARCHITECTURE  = "show_system_architecture"
    SHOW_RELATIONSHIP         = "show_relationship"
    SHOW_FORMULA              = "show_formula"
    SHOW_EXAMPLE              = "show_example"
    SHOW_EVIDENCE             = "show_evidence"
    SHOW_LOCATION             = "show_location"
    SHOW_OBJECT               = "show_object"
    HERO_STATEMENT            = "hero_statement"
    VISUAL_SUMMARY            = "visual_summary"
    TEXTUAL_SYNTHESIS         = "textual_synthesis"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Asset Type Enum
# ═══════════════════════════════════════════════════════════════

class VisualAssetType(str, Enum):
    """Physical visual asset form used to realize the visual intent.
    Independent from VisualIntent and Phase3LayoutFamily."""
    NATIVE_DIAGRAM            = "native_diagram"
    CHART                     = "chart"
    TABLE                     = "table"
    TIMELINE                  = "timeline"
    MATRIX                    = "matrix"
    PROCESS_FLOW              = "process_flow"
    HIERARCHY                 = "hierarchy"
    ARCHITECTURE_MAP          = "architecture_map"
    ANNOTATED_ILLUSTRATION    = "annotated_illustration"
    FORMULA_VISUAL            = "formula_visual"
    PHOTO                     = "photo"
    AI_ILLUSTRATION           = "ai_illustration"
    ICON_COMPOSITION          = "icon_composition"
    TEXTUAL_STATEMENT         = "textual_statement"
    HYBRID                    = "hybrid"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Phase 3 Layout Family Enum
# ═══════════════════════════════════════════════════════════════

class Phase3LayoutFamily(str, Enum):
    """Spatial composition layout families for slide construction.
    More granular than Phase 1 LayoutFamily; converted via adapter."""
    HERO_CENTER               = "hero_center"
    HERO_OFFSET               = "hero_offset"
    SPLIT_40_60               = "split_40_60"
    SPLIT_60_40               = "split_60_40"
    VISUAL_DOMINANT           = "visual_dominant"
    TEXT_DOMINANT              = "text_dominant"
    DIAGRAM_CANVAS            = "diagram_canvas"
    FULL_BLEED_IMAGE_WITH_PANEL = "full_bleed_image_with_panel"
    CARD_CLUSTER              = "card_cluster"
    COMPARISON_TWO_COLUMN     = "comparison_two_column"
    COMPARISON_MATRIX         = "comparison_matrix"
    TIMELINE_CANVAS           = "timeline_canvas"
    PROCESS_CANVAS            = "process_canvas"
    DATA_CANVAS               = "data_canvas"
    FORMULA_VISUAL            = "formula_visual"
    ANNOTATED_VISUAL          = "annotated_visual"
    QUOTE_OR_STATEMENT        = "quote_or_statement"
    SUMMARY_GRID              = "summary_grid"
    ASYMMETRIC_EDITORIAL      = "asymmetric_editorial"
    SYSTEM_ARCHITECTURE       = "system_architecture"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Relationship Type Enum
# ═══════════════════════════════════════════════════════════════

class RelationshipType(str, Enum):
    """Typed semantic relationship categories for structured visual rendering.
    Replaces unstructured Dict[str, str] per governance mandate."""
    CAUSAL           = "causal"
    SEQUENTIAL       = "sequential"
    STRUCTURAL       = "structural"
    HIERARCHICAL     = "hierarchical"
    COMPARATIVE      = "comparative"
    DEPENDENCY       = "dependency"
    ASSOCIATIVE      = "associative"
    TRANSFORMATION   = "transformation"
    FEEDBACK         = "feedback"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Data Grounding Status
# ═══════════════════════════════════════════════════════════════

class DataGroundingStatus(str, Enum):
    """Provenance state of data used in visual generation.
    Prevents confusion between descriptive claims and verified chart data.
    Phase 3.3 renderers MUST check this before authorizing empirical charts."""
    VERIFIED_DATA      = "verified_data"       # Data from verified source with citation
    SOURCE_GROUNDED    = "source_grounded"     # Derived from uploaded/cited source document
    MODEL_BACKGROUND   = "model_background"    # AI model general knowledge — NOT chart-safe
    STRUCTURAL_ONLY    = "structural_only"     # Structural/conceptual data (labels, categories)
    UNRESOLVED         = "unresolved"          # Origin unknown — must NOT generate quantitative viz


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Adapter Lossiness Classification
# ═══════════════════════════════════════════════════════════════

class AdapterLossiness(str, Enum):
    """Classification of Phase3→Legacy adapter mapping fidelity.
    LOSSY mappings preserve original Phase 3 metadata in VisualSemanticPacket
    so Phase 3.2 does not permanently lose semantic visual information."""
    LOSSLESS      = "lossless"       # 1:1 semantic equivalent
    LOSSY         = "lossy"          # Closest approximation; original intent preserved
    UNSUPPORTED   = "unsupported"    # No legacy equivalent; falls back to generic


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Typed Relationship Model
# ═══════════════════════════════════════════════════════════════

class VisualRelationship(BaseModel):
    """Typed semantic relationship between entities on a slide.
    Renderer consumes structured fields — no dictionary key parsing."""
    source_entity: str = ""
    relation: str = ""
    target_entity: str = ""
    relationship_type: RelationshipType = RelationshipType.ASSOCIATIVE
    direction: str = "forward"  # "forward" | "reverse" | "bidirectional"
    confidence: float = 0.8
    evidence_refs: List[str] = Field(default_factory=list)
    visual_importance: float = 0.5  # 0.0 - 1.0


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Typed Hierarchy Model
# ═══════════════════════════════════════════════════════════════

class HierarchyNode(BaseModel):
    """Typed hierarchy node with recursive children.
    Replaces flat List[str] hierarchy representation."""
    label: str = ""
    level: int = 0
    parent_label: str = ""
    children: List["HierarchyNode"] = Field(default_factory=list)
    visual_weight: float = 0.5
    is_leaf: bool = True

# Enable recursive model
HierarchyNode.model_rebuild()


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Candidate (Ranked)
# ═══════════════════════════════════════════════════════════════

class VisualCandidate(BaseModel):
    """Ranked visual representation candidate for a slide.
    Interpreter produces multiple ranked candidates; rhythm planner selects."""
    asset_type: VisualAssetType = VisualAssetType.TEXTUAL_STATEMENT
    layout_family: Phase3LayoutFamily = Phase3LayoutFamily.TEXT_DOMINANT
    suitability_score: float = 0.5  # 0.0 - 1.0
    rationale: str = ""
    requires_data: bool = False
    requires_image: bool = False
    complexity_estimate: str = "medium"  # "low" | "medium" | "high"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Density Profile (Independent)
# ═══════════════════════════════════════════════════════════════

class VisualDensityProfile(BaseModel):
    """Visual density dimensions independent from ContentDensity.
    ContentDensity controls text volume; VisualDensityProfile controls
    visual element count, spacing, and animation density."""
    element_count: str = "medium"     # "sparse" | "medium" | "dense"
    whitespace_ratio: float = 0.35    # 0.0 - 1.0 (higher = more whitespace)
    decoration_level: str = "moderate"  # "minimal" | "moderate" | "rich"
    animation_density: str = "subtle"  # "none" | "subtle" | "moderate" | "heavy"


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Semantic Packet
# ═══════════════════════════════════════════════════════════════

class VisualSemanticPacket(BaseModel):
    """Semantic visual requirements derived from SlideBlueprint + SlideContent.
    Uses typed VisualRelationship and HierarchyNode — no unstructured dicts."""
    slide_no: int = 1
    semantic_role: str = ""
    primary_visual_message: str = ""
    visual_intent: VisualIntent = VisualIntent.TEXTUAL_SYNTHESIS
    visual_priority: float = 0.5  # 0.0 - 1.0

    # Typed semantic structures (governance: no Dict[str, str])
    key_entities: List[str] = Field(default_factory=list)
    relationships: List[VisualRelationship] = Field(default_factory=list)
    hierarchy_tree: List[HierarchyNode] = Field(default_factory=list)

    # Domain-specific semantic data
    process_nodes: List[str] = Field(default_factory=list)
    comparison_targets: List[str] = Field(default_factory=list)
    quantitative_variables: List[str] = Field(default_factory=list)
    temporal_structure: List[str] = Field(default_factory=list)
    spatial_structure: List[str] = Field(default_factory=list)
    system_components: List[str] = Field(default_factory=list)
    formula_or_equation: Optional[str] = None

    # Typed causal structure (governance: no Dict[str, str])
    causal_structure: List[VisualRelationship] = Field(default_factory=list)

    # Visual production hints
    data_requirements: List[str] = Field(default_factory=list)
    image_candidate_concepts: List[str] = Field(default_factory=list)
    diagram_candidate: Optional[str] = None
    chart_candidate: Optional[str] = None
    annotation_candidates: List[str] = Field(default_factory=list)
    emphasis_targets: List[str] = Field(default_factory=list)
    must_visualize: List[str] = Field(default_factory=list)
    must_not_visualize: List[str] = Field(default_factory=list)

    # Ranked visual candidates
    visual_candidates: List[VisualCandidate] = Field(default_factory=list)

    # Density (independent from content density)
    content_density: ContentDensity = ContentDensity.MEDIUM
    visual_density: VisualDensityProfile = Field(default_factory=VisualDensityProfile)
    visual_confidence: float = 0.85

    # Grounding metadata
    grounding_source: str = "semantic_interpretation"  # provenance tag
    grounding_evidence: List[str] = Field(default_factory=list)
    data_grounding_status: str = "structural_only"  # DataGroundingStatus value


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Design DNA Typed Tokens
# ═══════════════════════════════════════════════════════════════

class TypographyScale(BaseModel):
    """Strongly typed typography token — no Dict[str, Any].
    Includes font fallback chain for PPTX portability."""
    font_family: str = "Inter"
    font_fallback: str = "Calibri"          # Fallback if primary not installed
    safe_office_fallback: str = "Calibri"   # Guaranteed Office-bundled font
    font_weight: int = 400
    font_size_pt: float = 12.0
    line_height_ratio: float = 1.4
    letter_spacing_em: float = 0.0
    text_transform: str = "none"  # "none" | "uppercase" | "capitalize"


class SpacingScale(BaseModel):
    """Strongly typed spacing scale — no Dict[str, float]."""
    xs: float = 4.0
    s: float = 8.0
    m: float = 16.0
    l: float = 24.0
    xl: float = 32.0
    xxl: float = 48.0


class ColorPalette(BaseModel):
    """Strongly typed accessible color palette — no Dict[str, str].
    All colors use hex notation. contrast_ratio tracks WCAG AA compliance."""
    primary: str = "#1A365D"
    primary_light: str = "#2A5298"
    secondary: str = "#4A6FA5"
    accent: str = "#E67E22"
    background: str = "#FFFFFF"
    surface: str = "#F8F9FA"
    text_primary: str = "#1A1A2E"
    text_secondary: str = "#4A5568"
    text_on_primary: str = "#FFFFFF"
    border: str = "#E2E8F0"
    success: str = "#38A169"
    warning: str = "#DD6B20"
    error: str = "#E53E3E"
    contrast_ratio_primary: float = 7.0  # WCAG AA minimum 4.5


class DesignDNA(BaseModel):
    """Deck-level visual design grammar derived from template and theme anchors.
    Uses strongly typed tokens throughout — no unstructured Dict fields."""
    # Identity
    theme_family: str = "academic_clean"
    tone: str = "professional"

    # Surface system
    background_strategy: str = "solid_light"  # "solid_light" | "gradient" | "textured" | "dark"
    surface_strategy: str = "card_elevation"  # "flat" | "card_elevation" | "glassmorphic" | "outlined"

    # Typography (typed scales)
    typographic_personality: str = "geometric_sans"  # "geometric_sans" | "humanist" | "neo_grotesque" | "serif_blend"
    title_scale: TypographyScale = Field(default_factory=lambda: TypographyScale(
        font_family="Inter", font_weight=700, font_size_pt=28.0,
        line_height_ratio=1.2, letter_spacing_em=-0.01
    ))
    body_scale: TypographyScale = Field(default_factory=lambda: TypographyScale(
        font_family="Inter", font_weight=400, font_size_pt=14.0,
        line_height_ratio=1.5, letter_spacing_em=0.0
    ))
    caption_scale: TypographyScale = Field(default_factory=lambda: TypographyScale(
        font_family="Inter", font_weight=400, font_size_pt=10.0,
        line_height_ratio=1.3, letter_spacing_em=0.02, text_transform="uppercase"
    ))

    # Geometry system
    corner_radius_system: str = "moderate"  # "sharp" | "subtle" | "moderate" | "rounded" | "pill"
    stroke_system: str = "thin_border"  # "none" | "thin_border" | "thick_accent" | "dashed"
    shadow_usage: str = "subtle"  # "none" | "subtle" | "medium" | "dramatic"

    # Spacing (typed scale)
    spacing_scale: SpacingScale = Field(default_factory=SpacingScale)
    grid_system: str = "12_column"  # "12_column" | "8_column" | "free_form"

    # Composition preferences
    preferred_composition_families: List[Phase3LayoutFamily] = Field(default_factory=list)

    # Asset styling
    icon_style: str = "outlined"  # "outlined" | "filled" | "duotone" | "flat"
    diagram_style: str = "clean_geometric"  # "clean_geometric" | "organic" | "technical" | "hand_drawn"
    chart_style: str = "minimal_axis"  # "minimal_axis" | "full_grid" | "decorative"
    image_treatment: str = "rounded_corners"  # "rounded_corners" | "full_bleed" | "masked" | "bordered"

    # Emphasis system
    highlight_treatment: str = "accent_bar"  # "accent_bar" | "background_tint" | "underline" | "bold_only"
    accent_strategy: str = "primary_accent"  # "primary_accent" | "complementary" | "monochromatic" | "triadic"

    # Density
    density_profile: ContentDensity = ContentDensity.MEDIUM
    visual_contrast_strategy: str = "alternating"  # "alternating" | "progressive" | "uniform"

    # Color (typed palette)
    color_palette: ColorPalette = Field(default_factory=ColorPalette)


# ═══════════════════════════════════════════════════════════════
# Phase 3.1 — Visual Rhythm Beat & Plan
# ═══════════════════════════════════════════════════════════════

class VisualWeight(str, Enum):
    """Visual dominance weight for rhythm planning."""
    LIGHT    = "light"
    MEDIUM   = "medium"
    DOMINANT = "dominant"


class VisualRhythmBeat(BaseModel):
    """Rhythm allocation for a single slide."""
    slide_no: int = 1
    visual_intent: VisualIntent = VisualIntent.TEXTUAL_SYNTHESIS
    suggested_asset_type: VisualAssetType = VisualAssetType.TEXTUAL_STATEMENT
    layout_family: Phase3LayoutFamily = Phase3LayoutFamily.TEXT_DOMINANT
    visual_weight: VisualWeight = VisualWeight.MEDIUM
    rationale: str = ""
    semantic_fit_score: float = 0.8  # how well this beat fits the content semantics


class DeckVisualRhythmPlan(BaseModel):
    """Deck-wide orchestration of visual pacing and layout variation."""
    topic: str = ""
    total_slides: int = 0
    beats: List[VisualRhythmBeat] = Field(default_factory=list)
    layout_distribution: Dict[str, int] = Field(default_factory=dict)
    asset_distribution: Dict[str, int] = Field(default_factory=dict)
    max_consecutive_layout_streak: int = 0
    card_cluster_percentage: float = 0.0
    rhythm_integrity_score: float = 0.0
    design_dna_reference: str = ""  # theme_family of the DesignDNA used


# ═══════════════════════════════════════════════════════════════
# BIDIRECTIONAL LEGACY ADAPTERS
# ═══════════════════════════════════════════════════════════════
# Phase 3.1 produces richer layout/asset specifications, but the
# existing renderer and tests consume LayoutFamily & VisualKind.
# These adapters ensure backward compatibility without modifying
# any frozen Phase 1/2 code.

_P3_TO_LEGACY_LAYOUT: Dict[Phase3LayoutFamily, LayoutFamily] = {
    Phase3LayoutFamily.HERO_CENTER:               LayoutFamily.HERO,
    Phase3LayoutFamily.HERO_OFFSET:               LayoutFamily.HERO,
    Phase3LayoutFamily.SPLIT_40_60:               LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    Phase3LayoutFamily.SPLIT_60_40:               LayoutFamily.LEFT_VISUAL_RIGHT_TEXT,
    Phase3LayoutFamily.VISUAL_DOMINANT:           LayoutFamily.DIAGRAM_DOMINANT,
    Phase3LayoutFamily.TEXT_DOMINANT:              LayoutFamily.CENTERED_FOCAL,
    Phase3LayoutFamily.DIAGRAM_CANVAS:            LayoutFamily.DIAGRAM_DOMINANT,
    Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL: LayoutFamily.EDITORIAL_ASYMMETRIC,
    Phase3LayoutFamily.CARD_CLUSTER:              LayoutFamily.THREE_CARD,
    Phase3LayoutFamily.COMPARISON_TWO_COLUMN:     LayoutFamily.TWO_COLUMN,
    Phase3LayoutFamily.COMPARISON_MATRIX:         LayoutFamily.MATRIX,
    Phase3LayoutFamily.TIMELINE_CANVAS:           LayoutFamily.TIMELINE_LAYOUT,
    Phase3LayoutFamily.PROCESS_CANVAS:            LayoutFamily.FULL_WIDTH_PROCESS,
    Phase3LayoutFamily.DATA_CANVAS:               LayoutFamily.DATA_DASHBOARD,
    Phase3LayoutFamily.FORMULA_VISUAL:            LayoutFamily.FORMULA_PLUS_EXAMPLE,
    Phase3LayoutFamily.ANNOTATED_VISUAL:          LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    Phase3LayoutFamily.QUOTE_OR_STATEMENT:        LayoutFamily.CENTERED_FOCAL,
    Phase3LayoutFamily.SUMMARY_GRID:              LayoutFamily.SUMMARY_GRID,
    Phase3LayoutFamily.ASYMMETRIC_EDITORIAL:      LayoutFamily.EDITORIAL_ASYMMETRIC,
    Phase3LayoutFamily.SYSTEM_ARCHITECTURE:       LayoutFamily.DIAGRAM_DOMINANT,
}

_P3_TO_LEGACY_VISUAL_KIND: Dict[VisualAssetType, VisualKind] = {
    VisualAssetType.NATIVE_DIAGRAM:         VisualKind.DIAGRAM,
    VisualAssetType.CHART:                  VisualKind.CHART_DEFERRED,  # explicit compatibility/deferred state (never generic table)
    VisualAssetType.TABLE:                  VisualKind.TABLE,
    VisualAssetType.TIMELINE:               VisualKind.TIMELINE,
    VisualAssetType.MATRIX:                 VisualKind.COMPARISON,
    VisualAssetType.PROCESS_FLOW:           VisualKind.FLOW,
    VisualAssetType.HIERARCHY:              VisualKind.HIERARCHY,
    VisualAssetType.ARCHITECTURE_MAP:       VisualKind.ARCHITECTURE,
    VisualAssetType.ANNOTATED_ILLUSTRATION: VisualKind.IMAGE,
    VisualAssetType.FORMULA_VISUAL:         VisualKind.NONE,
    VisualAssetType.PHOTO:                  VisualKind.IMAGE,
    VisualAssetType.AI_ILLUSTRATION:        VisualKind.IMAGE,
    VisualAssetType.ICON_COMPOSITION:       VisualKind.DIAGRAM,
    VisualAssetType.TEXTUAL_STATEMENT:      VisualKind.NONE,
    VisualAssetType.HYBRID:                 VisualKind.DIAGRAM,
}

_LEGACY_TO_P3_LAYOUT: Dict[LayoutFamily, Phase3LayoutFamily] = {
    LayoutFamily.HERO:                   Phase3LayoutFamily.HERO_CENTER,
    LayoutFamily.CENTERED_FOCAL:         Phase3LayoutFamily.TEXT_DOMINANT,
    LayoutFamily.LEFT_TEXT_RIGHT_VISUAL:  Phase3LayoutFamily.SPLIT_40_60,
    LayoutFamily.LEFT_VISUAL_RIGHT_TEXT:  Phase3LayoutFamily.SPLIT_60_40,
    LayoutFamily.TWO_COLUMN:             Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
    LayoutFamily.THREE_CARD:             Phase3LayoutFamily.CARD_CLUSTER,
    LayoutFamily.FOUR_CARD:              Phase3LayoutFamily.CARD_CLUSTER,
    LayoutFamily.DIAGRAM_DOMINANT:       Phase3LayoutFamily.DIAGRAM_CANVAS,
    LayoutFamily.FULL_WIDTH_PROCESS:     Phase3LayoutFamily.PROCESS_CANVAS,
    LayoutFamily.SPLIT_COMPARISON:       Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
    LayoutFamily.MATRIX:                 Phase3LayoutFamily.COMPARISON_MATRIX,
    LayoutFamily.TIMELINE_LAYOUT:        Phase3LayoutFamily.TIMELINE_CANVAS,
    LayoutFamily.EDITORIAL_ASYMMETRIC:   Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
    LayoutFamily.DATA_DASHBOARD:         Phase3LayoutFamily.DATA_CANVAS,
    LayoutFamily.CODE_PLUS_EXPLANATION:   Phase3LayoutFamily.SPLIT_40_60,
    LayoutFamily.FORMULA_PLUS_EXAMPLE:    Phase3LayoutFamily.FORMULA_VISUAL,
    LayoutFamily.CASE_STUDY_LAYOUT:       Phase3LayoutFamily.SPLIT_60_40,
    LayoutFamily.SUMMARY_GRID:            Phase3LayoutFamily.SUMMARY_GRID,
}


def to_legacy_layout_family(p3_layout: Phase3LayoutFamily) -> LayoutFamily:
    """Convert Phase 3 layout family to legacy LayoutFamily for renderer compatibility."""
    return _P3_TO_LEGACY_LAYOUT.get(p3_layout, LayoutFamily.CENTERED_FOCAL)


def to_legacy_visual_kind(asset_type: VisualAssetType) -> VisualKind:
    """Convert Phase 3 visual asset type to legacy VisualKind for renderer compatibility.
    VisualAssetType.CHART maps to VisualKind.CHART_DEFERRED, preserving semantic intent
    so that statistical charts are never silently flattened into generic tables."""
    return _P3_TO_LEGACY_VISUAL_KIND.get(asset_type, VisualKind.NONE)


def adapt_p3_candidate_to_legacy_visual_spec(
    candidate: "VisualCandidate",
    diagram_spec: Optional["DiagramSpec"] = None,
) -> VisualSpec:
    """Adapts a Phase 3 VisualCandidate into a legacy VisualSpec.
    Ensures CHART intent survives with an explicit compatibility/deferred rendering state
    (VisualKind.CHART_DEFERRED) and is never silently converted to an ordinary generic table."""
    legacy_kind = to_legacy_visual_kind(candidate.asset_type)
    compat = "deferred_rendering" if legacy_kind == VisualKind.CHART_DEFERRED else None
    return VisualSpec(
        kind=legacy_kind,
        asset_required=(legacy_kind == VisualKind.IMAGE),
        diagram_spec=diagram_spec,
        deferred_asset_type=candidate.asset_type.value if legacy_kind == VisualKind.CHART_DEFERRED else None,
        compatibility_state=compat,
    )


def from_legacy_layout_family(legacy: LayoutFamily) -> Phase3LayoutFamily:
    """Convert legacy LayoutFamily to Phase 3 layout family (reverse adapter)."""
    return _LEGACY_TO_P3_LAYOUT.get(legacy, Phase3LayoutFamily.TEXT_DOMINANT)


def from_legacy_visual_type_hint(vth: VisualTypeHint) -> VisualIntent:
    """Derive initial VisualIntent from legacy VisualTypeHint (best-effort mapping)."""
    _map: Dict[VisualTypeHint, VisualIntent] = {
        VisualTypeHint.NONE:                    VisualIntent.TEXTUAL_SYNTHESIS,
        VisualTypeHint.TYPOGRAPHY_ONLY:          VisualIntent.HERO_STATEMENT,
        VisualTypeHint.ICON_SUPPORT:             VisualIntent.TEXTUAL_SYNTHESIS,
        VisualTypeHint.LAYERED_ARCHITECTURE:     VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        VisualTypeHint.PIPELINE:                 VisualIntent.SHOW_PROCESS,
        VisualTypeHint.PROCESS_FLOW:             VisualIntent.SHOW_PROCESS,
        VisualTypeHint.SEQUENCE_FLOW:            VisualIntent.SHOW_PROCESS,
        VisualTypeHint.CYCLE:                    VisualIntent.SHOW_PROCESS,
        VisualTypeHint.TIMELINE:                 VisualIntent.SHOW_TIMELINE,
        VisualTypeHint.HIERARCHY:                VisualIntent.SHOW_HIERARCHY,
        VisualTypeHint.TAXONOMY:                 VisualIntent.SHOW_HIERARCHY,
        VisualTypeHint.CAUSE_EFFECT:             VisualIntent.SHOW_CAUSALITY,
        VisualTypeHint.COMPARISON_MATRIX:        VisualIntent.COMPARE,
        VisualTypeHint.DECISION_TREE:            VisualIntent.SHOW_HIERARCHY,
        VisualTypeHint.HUB_AND_SPOKE:            VisualIntent.SHOW_RELATIONSHIP,
        VisualTypeHint.FUNNEL:                   VisualIntent.SHOW_PROCESS,
        VisualTypeHint.TABLE:                    VisualIntent.COMPARE,
        VisualTypeHint.CHART:                    VisualIntent.SHOW_DATA_PATTERN,
        VisualTypeHint.KPI:                      VisualIntent.SHOW_DATA_PATTERN,
        VisualTypeHint.CODE_BLOCK:               VisualIntent.SHOW_EXAMPLE,
        VisualTypeHint.FORMULA:                  VisualIntent.SHOW_FORMULA,
        VisualTypeHint.ANNOTATED_ILLUSTRATION:   VisualIntent.EXPLAIN_STRUCTURE,
        VisualTypeHint.PHOTOGRAPH:               VisualIntent.SHOW_OBJECT,
        VisualTypeHint.MAP:                      VisualIntent.SHOW_LOCATION,
        VisualTypeHint.BEFORE_AFTER:             VisualIntent.SHOW_TRANSFORMATION,
    }
    return _map.get(vth, VisualIntent.TEXTUAL_SYNTHESIS)
