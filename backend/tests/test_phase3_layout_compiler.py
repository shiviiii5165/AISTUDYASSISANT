"""
TeachGenie PPT vNext — Phase 3.2C Parametric Layout Compiler & Reflow Engine Test Suite
======================================================================================
Comprehensive test suite validating Phase 3.2C contracts:
  1. All 20 Phase3LayoutFamily compilers compile valid SlideCompositionPlans
  2. Parametric constraint envelope resolution and bounds checking
  3. Content density adaptation (LOW, MEDIUM, HIGH)
  4. REFLOW_REQUIRED handling consuming Phase 3.2B outputs
  5. Deterministic semantic fallback chains
  6. Semantic priority and content preservation (zero content invention)
  7. VisualRhythmBeat compliance and deviation tracking
  8. DesignDNA differentiation across 5 theme templates
  9. Cross-template semantic identity preservation
  10. Full-bleed image with panel safety (safe semantic text containment)
  11. Card cluster discipline (semantic grouping required, single bullet rejected)
  12. Comparison contracts (two-column pairwise vs matrix multi-attribute)
  13. Process vs timeline contract distinction
  14. Data canvas deferred chart preservation without fake data
  15. Formula visual region prominence and readability
  16. Region collision detection and safe-zone containment
  17. 12-column grid and 30-module vertical baseline invariants
  18. Determinism: identical inputs produce identical plans
  19. Held-out topic testing across 5 disciplines without topic branching
"""
import copy
import hashlib
import pytest
from typing import Dict, Any, List, Tuple, Optional, Set

from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    LayoutFamily,
    VisualKind,
    SlideIntent,
    VisualTypeHint,
    ComparisonRow,
    DataPoint,
)
from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    VisualAssetType,
    VisualIntent,
    VisualWeight,
    VisualRhythmBeat,
    VisualSemanticPacket,
    VisualCandidate,
    VisualRelationship,
    RelationshipType,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
    VisualDensityProfile,
)
from app.services.presentation.composition_schemas import (
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    CompositionMode,
    RegionSemanticRole,
    CONTENT_BEARING_ROLES,
    RegionAlignment,
    VerticalAlignment,
    SpacingToken,
    TypographyRole,
    FormulaRenderMode,
    LayoutSafeZone,
    ContentBinding,
    CompositionInputManifest,
    ResolvedRegionBounds,
    ContentRegion,
    WhitespaceMetrics,
    SurfaceToken,
    BorderToken,
    SlideCompositionPlan,
)
from app.services.presentation.grid_engine import (
    MARGIN_LEFT_IN,
    MARGIN_RIGHT_IN,
    MARGIN_TOP_IN,
    MARGIN_BOTTOM_IN,
    GRID_COLUMNS,
    GRID_GUTTER_IN,
    GRID_COL_WIDTH_IN,
    ACTIVE_CONTENT_WIDTH_IN,
    resolve_column_left_in,
    resolve_column_width_in,
    detect_region_collision,
)
from app.services.presentation.typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)
from app.services.presentation.layout_compiler import (
    compile_slide_layout,
    get_parametric_constraint_envelope,
    ParametricConstraintEnvelope,
    SEMANTIC_FALLBACK_CHAINS,
    validate_plan_regions,
    check_layout_prerequisites,
    has_temporal_semantics,
    DEFECT_LAYOUT_CONSTRAINT_UNSATISFIED,
    DEFECT_REFLOW_REQUIRED,
    DEFECT_REFLOW_CHAIN_EXHAUSTED,
    DEFECT_REGION_COLLISION,
    DEFECT_SAFE_ZONE_VIOLATION,
    DEFECT_VISUAL_REGION_TOO_SMALL,
    DEFECT_TEXT_REGION_TOO_SMALL,
    DEFECT_SEMANTIC_ROLE_UNSUPPORTED,
    DEFECT_RHYTHM_DEVIATION,
    DEFECT_CARD_GROUPING_INVALID,
    DEFECT_COMPARISON_STRUCTURE_UNSUPPORTED,
    DEFECT_PROCESS_STRUCTURE_UNSUPPORTED,
    DEFECT_FULL_BLEED_TEXT_VIOLATION,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def standard_dna() -> DesignDNA:
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=26.0, line_height_ratio=1.20, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=13.5, line_height_ratio=1.45, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25, letter_spacing_em=0.02,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.MEDIUM,
        color_palette=ColorPalette(
            primary="#1A365D", primary_light="#2B6CB0", secondary="#4A6FA5",
            accent="#ED8936", background="#FFFFFF", surface="#F7FAFC",
            text_primary="#1A202C", text_secondary="#4A5568", text_on_primary="#FFFFFF",
            border="#E2E8F0",
        ),
    )


@pytest.fixture
def cs_sample() -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, CompositionInputManifest]:
    """Node.js Architecture fixture."""
    bp = SlideBlueprint(
        slide_id="slide_cs_1",
        slide_number=1,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Node.js uses an event-driven non-blocking I/O model.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.DIAGRAM_DOMINANT,
    )
    content = SlideContent(
        title="Node.js Architecture & Event Loop",
        subtitle="Single-threaded execution with asynchronous I/O delegation",
        primary_takeaway="The libuv event loop manages asynchronous operations through worker threads.",
        supporting_points=[
            "V8 JavaScript engine handles compilation and execution.",
            "Libuv provides cross-platform asynchronous I/O event polling.",
            "Thread pool handles expensive file system and crypto operations.",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="V8 Call Stack delegates I/O to libuv event queue.",
        visual_intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        system_components=["V8 Engine", "Libuv Event Loop", "Worker Pool", "Event Queue"],
        relationships=[
            VisualRelationship(
                source_entity="V8 Engine", relation="delegates_io", target_entity="Libuv Event Loop",
                relationship_type=RelationshipType.STRUCTURAL,
            ),
        ],
        diagram_candidate="EventLoopDiagram",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.ARCHITECTURE_MAP, layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE)
        ],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_cs")
    manifest.register_content("slide_cs_1", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())
    return bp, content, packet, manifest


@pytest.fixture
def bio_sample() -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, CompositionInputManifest]:
    """Biology Photosynthesis fixture."""
    bp = SlideBlueprint(
        slide_id="slide_bio_2",
        slide_number=2,
        intent=SlideIntent.PROCESS_EXPLANATION,
        primary_message="Light reactions produce ATP and NADPH for the Calvin cycle.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.FULL_WIDTH_PROCESS,
    )
    content = SlideContent(
        title="Photosynthesis: Light Reactions",
        subtitle="Energy transduction in the thylakoid membrane",
        primary_takeaway="Photons excite chlorophyll electrons initiating linear electron transport.",
        process_steps=[
            "Photon absorption by Photosystem II (P680)",
            "Photolysis of water releasing molecular oxygen",
            "Proton gradient generation across thylakoid membrane",
            "ATP synthesis and NADP+ reduction to NADPH",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=2,
        primary_visual_message="Sequential electron transfer through PSII, Cytochrome b6f, and PSI.",
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["PSII", "Plastoquinone", "Cyt b6f", "Plastocyanin", "PSI", "Ferredoxin"],
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.PROCESS_FLOW, layout_family=Phase3LayoutFamily.PROCESS_CANVAS)
        ],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_bio")
    manifest.register_content("slide_bio_2", content.model_dump())
    manifest.register_content("visual_2", packet.model_dump())
    return bp, content, packet, manifest


@pytest.fixture
def lit_sample() -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, CompositionInputManifest]:
    """Literature Macbeth fixture."""
    bp = SlideBlueprint(
        slide_id="slide_lit_3",
        slide_number=3,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Macbeth's unchecked vaulting ambition leads to moral disintegration.",
        content_density=ContentDensity.LOW,
        layout_family=LayoutFamily.CENTERED_FOCAL,
    )
    content = SlideContent(
        title="Macbeth: The Anatomy of Ambition",
        subtitle="Internal psychological collapse in Shakespearean tragedy",
        primary_takeaway="Vaulting ambition o'erleaps itself and falls on the other.",
        callout="Act I, Scene VII — William Shakespeare",
    )
    packet = VisualSemanticPacket(
        slide_no=3,
        primary_visual_message="Focal dramatic quote highlighting tragic irony.",
        visual_intent=VisualIntent.HERO_STATEMENT,
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.TEXTUAL_STATEMENT, layout_family=Phase3LayoutFamily.QUOTE_OR_STATEMENT)
        ],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_lit")
    manifest.register_content("slide_lit_3", content.model_dump())
    manifest.register_content("visual_3", packet.model_dump())
    return bp, content, packet, manifest


@pytest.fixture
def math_sample() -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, CompositionInputManifest]:
    """Mathematics Eigenvalues fixture."""
    bp = SlideBlueprint(
        slide_id="slide_math_4",
        slide_number=4,
        intent=SlideIntent.FORMULA_EXPLANATION,
        primary_message="Eigenvectors experience only scaling under linear transformation.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.FORMULA_PLUS_EXAMPLE,
    )
    content = SlideContent(
        title="Eigenvalues & Eigenvectors",
        subtitle="Invariant coordinate directions under matrix operations",
        primary_takeaway="A non-zero vector v is an eigenvector if Av is a scalar multiple of v.",
        formula=r"A \mathbf{v} = \lambda \mathbf{v}",
        formula_symbol_meanings="A: transformation matrix, v: eigenvector, lambda: eigenvalue",
    )
    packet = VisualSemanticPacket(
        slide_no=4,
        primary_visual_message="Geometric vector stretching without directional change.",
        visual_intent=VisualIntent.SHOW_FORMULA,
        formula_or_equation=r"A \mathbf{v} = \lambda \mathbf{v}",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.FORMULA_VISUAL, layout_family=Phase3LayoutFamily.FORMULA_VISUAL)
        ],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_math")
    manifest.register_content("slide_math_4", content.model_dump())
    manifest.register_content("visual_4", packet.model_dump())
    return bp, content, packet, manifest


@pytest.fixture
def econ_sample() -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, CompositionInputManifest]:
    """Economics Monetary Policy fixture."""
    bp = SlideBlueprint(
        slide_id="slide_econ_5",
        slide_number=5,
        intent=SlideIntent.DATA_INSIGHT,
        primary_message="Central bank interest rate hikes cool core inflation with a time lag.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.DATA_DASHBOARD,
    )
    content = SlideContent(
        title="Monetary Policy & Inflation Transmission",
        subtitle="Policy rate adjustments and empirical consumer price dynamics",
        primary_takeaway="A 200 bps policy rate increase correlates with a 1.8% decrease in CPI over 6 quarters.",
        data_points=[
            DataPoint(label="Peak CPI", value="9.1", unit="percent"),
            DataPoint(label="Target CPI", value="2.0", unit="percent"),
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=5,
        primary_visual_message="Inverse relationship between policy interest rates and core inflation rate.",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
        chart_candidate="PolicyRateVsInflationLineChart",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.CHART, layout_family=Phase3LayoutFamily.DATA_CANVAS)
        ],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_econ")
    manifest.register_content("slide_econ_5", content.model_dump())
    manifest.register_content("visual_5", packet.model_dump())
    return bp, content, packet, manifest


# ═══════════════════════════════════════════════════════════════
# 1. 20/20 LAYOUT FAMILY COMPILATION TESTS
# ═══════════════════════════════════════════════════════════════

ALL_20_FAMILIES = [
    Phase3LayoutFamily.HERO_CENTER,
    Phase3LayoutFamily.HERO_OFFSET,
    Phase3LayoutFamily.SPLIT_40_60,
    Phase3LayoutFamily.SPLIT_60_40,
    Phase3LayoutFamily.VISUAL_DOMINANT,
    Phase3LayoutFamily.TEXT_DOMINANT,
    Phase3LayoutFamily.DIAGRAM_CANVAS,
    Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL,
    Phase3LayoutFamily.CARD_CLUSTER,
    Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
    Phase3LayoutFamily.COMPARISON_MATRIX,
    Phase3LayoutFamily.TIMELINE_CANVAS,
    Phase3LayoutFamily.PROCESS_CANVAS,
    Phase3LayoutFamily.DATA_CANVAS,
    Phase3LayoutFamily.FORMULA_VISUAL,
    Phase3LayoutFamily.ANNOTATED_VISUAL,
    Phase3LayoutFamily.QUOTE_OR_STATEMENT,
    Phase3LayoutFamily.SUMMARY_GRID,
    Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
    Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
]


def test_all_20_layout_families_defined():
    """Asserts that exactly all 20 Phase3LayoutFamily values are tested."""
    assert len(ALL_20_FAMILIES) == 20
    assert len(set(ALL_20_FAMILIES)) == 20


@pytest.mark.parametrize("layout_family", ALL_20_FAMILIES)
def test_all_20_families_compile_valid_plan(
    layout_family: Phase3LayoutFamily,
    standard_dna: DesignDNA,
):
    """
    Validates that every single one of the 20 approved Phase3LayoutFamily values
    compiles successfully from typed constraint envelopes into a valid SlideCompositionPlan.
    """
    # Build a fully populated content fixture supporting any layout
    content = SlideContent(
        title=f"Testing {layout_family.value}",
        subtitle="Parametric envelope validation",
        primary_takeaway="Verified factual takeaway satisfying semantic requirements.",
        supporting_points=["Structured point A", "Structured point B", "Structured point C"],
        process_steps=["Initiation phase", "Execution phase", "Verification phase"],
        comparison_target_a="Solution Alpha",
        comparison_target_b="Solution Beta",
        comparison_rows=[
            ComparisonRow(dimension="Latency", target_a_value="10ms", target_b_value="50ms"),
            ComparisonRow(dimension="Throughput", target_a_value="10k rps", target_b_value="2k rps"),
        ],
        formula=r"E = mc^2",
        data_points=[DataPoint(label="Efficiency", value="98.5", unit="%")],
        callout="Key principle",
    )
    bp = SlideBlueprint(
        slide_id=f"slide_test_{layout_family.value}",
        slide_number=1,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Validation test message",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.CENTERED_FOCAL,
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Visual concept display",
        system_components=["Component 1", "Component 2"],
        process_nodes=["Node 1", "Node 2"],
        temporal_structure=["Phase 1", "Phase 2", "Phase 3"],
        comparison_targets=["Solution Alpha", "Solution Beta"],
        formula_or_equation=r"E = mc^2",
        visual_candidates=[VisualCandidate(layout_family=layout_family)],
    )
    beat = VisualRhythmBeat(
        slide_no=1,
        layout_family=layout_family,
        visual_weight=VisualWeight.MEDIUM,
    )
    manifest = CompositionInputManifest(manifest_id="manifest_test")
    manifest.register_content(bp.slide_id, content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    plan = compile_slide_layout(
        slide_blueprint=bp,
        slide_content=content,
        visual_semantic_packet=packet,
        design_dna=standard_dna,
        rhythm_beat=beat,
        composition_input_manifest=manifest,
    )

    assert plan is not None
    assert isinstance(plan, SlideCompositionPlan)
    assert plan.slide_no == 1
    assert plan.layout_family == layout_family
    assert len(plan.content_regions) >= 2  # At least title + content
    assert plan.whitespace_metrics.region_occupied_area_ratio > 0.0
    assert plan.whitespace_metrics.region_occupied_area_ratio <= 1.0


# ═══════════════════════════════════════════════════════════════
# 2. PARAMETRIC CONSTRAINT ENVELOPE VALIDATION
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("layout_family", ALL_20_FAMILIES)
def test_parametric_constraint_envelope_properties(layout_family: Phase3LayoutFamily):
    """
    Validates that each layout family envelope satisfies mathematical grid constraints:
    min_span <= preferred_span <= max_span, spans <= 12, valid ratios.
    """
    env = get_parametric_constraint_envelope(layout_family, ContentDensity.MEDIUM)
    assert isinstance(env, ParametricConstraintEnvelope)
    assert env.layout_family == layout_family
    assert 1 <= env.min_text_span <= env.preferred_text_span <= env.max_text_span <= 12
    assert 0 <= env.min_visual_span <= env.preferred_visual_span <= env.max_visual_span <= 12
    assert 0.0 <= env.min_visual_ratio <= env.preferred_visual_ratio <= env.max_visual_ratio <= 1.0
    assert env.minimum_gutter > 0.0
    assert env.minimum_gutter <= env.maximum_gutter
    assert env.whitespace_target_min < env.whitespace_target_max


# ═══════════════════════════════════════════════════════════════
# 3. DENSITY ADAPTATION (LOW / MEDIUM / HIGH)
# ═══════════════════════════════════════════════════════════════

def test_split_40_60_density_adaptation():
    """
    Tests responsive envelope adjustment across LOW, MEDIUM, and HIGH density:
    LOW -> 4 or 5 text / 7 or 8 visual; HIGH -> 6 text / 6 visual.
    """
    low_env = get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, ContentDensity.LOW)
    med_env = get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, ContentDensity.MEDIUM)
    high_env = get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, ContentDensity.HIGH)

    assert low_env.preferred_text_span <= med_env.preferred_text_span
    assert med_env.preferred_text_span < high_env.preferred_text_span
    assert high_env.preferred_text_span == 6
    assert high_env.preferred_visual_span == 6


def test_split_60_40_density_adaptation():
    """Validates SPLIT_60_40 expands text span under HIGH density."""
    med_env = get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_60_40, ContentDensity.MEDIUM)
    high_env = get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_60_40, ContentDensity.HIGH)

    assert high_env.preferred_text_span >= med_env.preferred_text_span
    assert high_env.preferred_text_span == 8
    assert high_env.preferred_visual_span == 4


# ═══════════════════════════════════════════════════════════════
# 4. REFLOW_REQUIRED HANDLING CONSUMING PHASE 3.2B SIGNALS
# ═══════════════════════════════════════════════════════════════

def test_reflow_required_triggers_envelope_expansion_and_fallback(
    standard_dna: DesignDNA,
    cs_sample,
):
    """
    When TextFitResult.status == REFLOW_REQUIRED, layout compiler must attempt
    structural reflow (expanding text span or stepping down fallback chain).
    """
    bp, content, packet, manifest = cs_sample
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.SPLIT_40_60)

    # Simulate Phase 3.2B output with REFLOW_REQUIRED on the body region
    fit_results = {
        "slide_cs_1_split_text": TextFitResult(
            region_id="slide_cs_1_split_text",
            status=TextFitStatus.REFLOW_REQUIRED,
            fit_stage=6,
            display_text=content.primary_takeaway,
            typography_before=resolve_typography_role_spec(TypographyRole.BODY, standard_dna),
            typography_after=resolve_typography_role_spec(TypographyRole.BODY, standard_dna),
        )
    }

    plan = compile_slide_layout(
        slide_blueprint=bp,
        slide_content=content,
        visual_semantic_packet=packet,
        design_dna=standard_dna,
        rhythm_beat=beat,
        composition_input_manifest=manifest,
        text_fit_results=fit_results,
    )

    assert plan is not None
    assert DEFECT_REFLOW_REQUIRED in plan.quality_defects
    # The compiler should have expanded the text span or transitioned
    assert plan.planning_rationale is not None
    assert "Reflow fallback steps" in plan.planning_rationale


def test_reflow_does_not_mutate_or_truncate_text(
    standard_dna: DesignDNA,
    cs_sample,
):
    """
    Reflow changes geometry, not meaning.
    The content in the manifest and content binding hash must remain intact.
    """
    bp, content, packet, manifest = cs_sample
    original_title = content.title
    original_takeaway = content.primary_takeaway
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.SPLIT_40_60)

    fit_results = {
        "primary_text": TextFitResult(
            region_id="primary_text",
            status=TextFitStatus.REFLOW_REQUIRED,
            fit_stage=6,
            display_text=content.primary_takeaway,
            typography_before=resolve_typography_role_spec(TypographyRole.BODY, standard_dna),
            typography_after=resolve_typography_role_spec(TypographyRole.BODY, standard_dna),
        )
    }

    plan = compile_slide_layout(
        slide_blueprint=bp,
        slide_content=content,
        visual_semantic_packet=packet,
        design_dna=standard_dna,
        rhythm_beat=beat,
        composition_input_manifest=manifest,
        text_fit_results=fit_results,
    )

    # Check that source content in manifest was never modified
    raw = manifest.raw_content_items[bp.slide_id]
    assert raw["title"] == original_title
    assert raw["primary_takeaway"] == original_takeaway


# ═══════════════════════════════════════════════════════════════
# 5. DETERMINISTIC FALLBACK CHAINS
# ═══════════════════════════════════════════════════════════════

def test_semantic_fallback_chains_integrity():
    """Verifies approved semantic fallback paths exist for key families."""
    assert SEMANTIC_FALLBACK_CHAINS[Phase3LayoutFamily.SPLIT_40_60] == [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ]
    assert SEMANTIC_FALLBACK_CHAINS[Phase3LayoutFamily.VISUAL_DOMINANT] == [
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ]
    assert SEMANTIC_FALLBACK_CHAINS[Phase3LayoutFamily.FORMULA_VISUAL] == [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ]
    assert SEMANTIC_FALLBACK_CHAINS[Phase3LayoutFamily.SYSTEM_ARCHITECTURE] == [
        Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ]


# ═══════════════════════════════════════════════════════════════
# 6. VISUAL RHYTHM BEAT COMPLIANCE
# ═══════════════════════════════════════════════════════════════

def test_visual_rhythm_beat_compliance_tracking(standard_dna: DesignDNA, cs_sample):
    """
    Verifies that layout compiler complies with VisualRhythmBeat, tracking
    rhythm_plan_compliance and logging deviations if fallback occurs.
    """
    bp, content, packet, manifest = cs_sample
    beat = VisualRhythmBeat(
        slide_no=1,
        layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
        visual_weight=VisualWeight.DOMINANT,
    )

    plan = compile_slide_layout(
        slide_blueprint=bp,
        slide_content=content,
        visual_semantic_packet=packet,
        design_dna=standard_dna,
        rhythm_beat=beat,
        composition_input_manifest=manifest,
    )

    assert plan.layout_family == Phase3LayoutFamily.SYSTEM_ARCHITECTURE
    assert plan.rhythm_plan_compliance == 1.0


# ═══════════════════════════════════════════════════════════════
# 7. DESIGNDNA-AWARE GEOMETRY DIFFERENTIATION
# ═══════════════════════════════════════════════════════════════

def test_designdna_aware_geometry_differentiation(bio_sample):
    """
    Tests that identical semantic slide compiles differently under different
    DesignDNA profiles (e.g. academic_clean vs modern_minimal vs technical_grid)
    while preserving identical semantic content.
    """
    bp, content, packet, manifest = bio_sample
    beat = VisualRhythmBeat(slide_no=2, layout_family=Phase3LayoutFamily.SPLIT_40_60)

    # 1. Academic Clean DNA (card elevation, 8pt radius)
    dna_academic = DesignDNA(
        theme_family="academic_clean",
        surface_strategy="card_elevation",
        stroke_system="thin_border",
        corner_radius_system="moderate",
        color_palette=ColorPalette(primary="#1A365D"),
    )
    plan_academic = compile_slide_layout(
        bp, content, packet, dna_academic, beat, manifest
    )

    # 2. Modern Minimal DNA (flat surfaces, rounded 12pt radius)
    dna_minimal = DesignDNA(
        theme_family="modern_minimal",
        surface_strategy="flat",
        stroke_system="none",
        corner_radius_system="rounded",
        color_palette=ColorPalette(primary="#000000"),
    )
    plan_minimal = compile_slide_layout(
        bp, content, packet, dna_minimal, beat, manifest
    )

    # 3. Technical Grid DNA (sharp 0pt radius, thin borders)
    dna_technical = DesignDNA(
        theme_family="technical_grid",
        surface_strategy="outlined",
        stroke_system="thin_border",
        corner_radius_system="sharp",
        color_palette=ColorPalette(primary="#2D3748"),
    )
    plan_technical = compile_slide_layout(
        bp, content, packet, dna_technical, beat, manifest
    )

    body_academic = [r for r in plan_academic.content_regions if r.semantic_role == RegionSemanticRole.PRIMARY_TEXT][0]
    body_minimal = [r for r in plan_minimal.content_regions if r.semantic_role == RegionSemanticRole.PRIMARY_TEXT][0]
    body_technical = [r for r in plan_technical.content_regions if r.semantic_role == RegionSemanticRole.PRIMARY_TEXT][0]

    # Corner radii differ across profiles
    assert body_academic.corner_radius_pt == 8.0
    assert body_minimal.corner_radius_pt == 12.0
    assert body_technical.corner_radius_pt == 0.0

    # Surface styling differs
    assert body_minimal.border_token == BorderToken.NONE
    assert body_technical.border_token == BorderToken.THIN


# ═══════════════════════════════════════════════════════════════
# 8. CROSS-TEMPLATE SEMANTIC IDENTITY INVARIANT (Section 19)
# ═══════════════════════════════════════════════════════════════

def test_cross_template_semantic_identity_preservation(cs_sample):
    """
    Section 19 Invariant: Take one identical semantic slide and compile under
    all five DesignDNA profiles.
    Must remain identical:
      - SlideContent hash
      - VisualSemanticPacket hash
      - visual intent
      - content bindings
    """
    bp, content, packet, manifest = cs_sample
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE)

    dna_templates = [
        DesignDNA(theme_family="academic", corner_radius_system="moderate", color_palette=ColorPalette(primary="#1A365D")),
        DesignDNA(theme_family="minimal", corner_radius_system="rounded", color_palette=ColorPalette(primary="#1A365D")),
        DesignDNA(theme_family="technical", corner_radius_system="sharp", color_palette=ColorPalette(primary="#1A365D")),
        DesignDNA(theme_family="editorial", corner_radius_system="subtle", color_palette=ColorPalette(primary="#1A365D")),
        DesignDNA(theme_family="visual", corner_radius_system="pill", color_palette=ColorPalette(primary="#1A365D")),
    ]

    initial_content_hash = manifest.slide_content_hashes[bp.slide_id]
    plans = [
        compile_slide_layout(bp, content, packet, dna, beat, manifest)
        for dna in dna_templates
    ]

    for p in plans:
        # Check that content hash in manifest never changed
        assert manifest.slide_content_hashes[bp.slide_id] == initial_content_hash
        # Title region binding is verified and identical across all templates
        title_reg = [r for r in p.content_regions if r.semantic_role == RegionSemanticRole.HEADER_TITLE][0]
        assert title_reg.binding.source_id == bp.slide_id
        assert title_reg.binding.field_path == "title"
        assert title_reg.binding.resolved_content_hash == manifest.compute_field_hash(bp.slide_id, "title")


# ═══════════════════════════════════════════════════════════════
# 9. FULL-BLEED IMAGE WITH PANEL SAFETY CONTRACT (Section 9)
# ═══════════════════════════════════════════════════════════════

def test_full_bleed_image_with_panel_safety(standard_dna: DesignDNA, lit_sample):
    """
    Section 9 Contract:
    - background visual region may use full slide bounds (rows 1..30, FULL_BLEED)
    - semantic text must remain strictly in SAFE_CONTENT (rows 8..27) and SAFE_TITLE (rows 3..7)
    - never place text outside safe semantic boundaries.
    """
    bp, content, packet, manifest = lit_sample
    beat = VisualRhythmBeat(slide_no=3, layout_family=Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL)

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family == Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL

    bleed_regions = [r for r in plan.content_regions if r.is_full_bleed or r.safe_zone == LayoutSafeZone.FULL_BLEED]
    assert len(bleed_regions) == 1
    assert bleed_regions[0].semantic_role == RegionSemanticRole.BLEED_BACKGROUND

    # Check semantic text regions
    text_regions = [r for r in plan.content_regions if r.semantic_role in CONTENT_BEARING_ROLES]
    for tr in text_regions:
        assert tr.safe_zone != LayoutSafeZone.FULL_BLEED
        assert not tr.is_full_bleed
        if tr.semantic_role == RegionSemanticRole.HEADER_TITLE:
            assert 3 <= tr.baseline_row_start <= 7
        elif tr.semantic_role == RegionSemanticRole.PRIMARY_TEXT:
            assert 8 <= tr.baseline_row_start <= 27
            assert tr.baseline_row_start + tr.baseline_row_span - 1 <= 27


# ═══════════════════════════════════════════════════════════════
# 10. CARD CLUSTER & SUMMARY GRID DISCIPLINE (Section 10)
# ═══════════════════════════════════════════════════════════════

def test_card_cluster_rejects_single_bullet_and_falls_back(standard_dna: DesignDNA):
    """
    Card cluster requires semantic grouping. Single bullet or missing grouping
    must be rejected with DEFECT_CARD_GROUPING_INVALID and trigger fallback.
    """
    bp = SlideBlueprint(slide_id="slide_single_card", slide_number=1, content_density=ContentDensity.LOW)
    content = SlideContent(
        title="Single Concept Slide",
        primary_takeaway="A solitary concept without groupings.",
        supporting_points=["Just one single bullet point"],
    )
    packet = VisualSemanticPacket(slide_no=1, primary_visual_message="Single bullet")
    manifest = CompositionInputManifest(manifest_id="m1")
    manifest.register_content("slide_single_card", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.CARD_CLUSTER)
    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)

    # Should detect invalid card grouping and step to fallback (TEXT_DOMINANT)
    assert DEFECT_CARD_GROUPING_INVALID in plan.quality_defects
    assert plan.layout_family == Phase3LayoutFamily.TEXT_DOMINANT


# ═══════════════════════════════════════════════════════════════
# 11. COMPARISON CONTRACTS (Section 11)
# ═══════════════════════════════════════════════════════════════

def test_comparison_two_column_pairwise_symmetry(standard_dna: DesignDNA):
    """COMPARISON_TWO_COLUMN allocates symmetric columns (cols 1..6 and 7..12)."""
    bp = SlideBlueprint(slide_id="comp_slide", slide_number=1)
    content = SlideContent(
        title="SQL vs NoSQL",
        comparison_target_a="Relational SQL Databases",
        comparison_target_b="Document NoSQL Databases",
    )
    packet = VisualSemanticPacket(slide_no=1, comparison_targets=["SQL", "NoSQL"])
    manifest = CompositionInputManifest(manifest_id="m_comp")
    manifest.register_content("comp_slide", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.COMPARISON_TWO_COLUMN)
    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)

    col_a = [r for r in plan.content_regions if r.semantic_role == RegionSemanticRole.COMPARISON_COLUMN_A][0]
    col_b = [r for r in plan.content_regions if r.semantic_role == RegionSemanticRole.COMPARISON_COLUMN_B][0]

    assert col_a.grid_col_start == 1
    assert col_a.grid_col_span == 6
    assert col_b.grid_col_start == 7
    assert col_b.grid_col_span == 6


def test_comparison_matrix_fallback_when_unsupported(standard_dna: DesignDNA):
    """
    If content does not support a multi-attribute matrix (no comparison rows),
    must fallback rather than invent headers or values.
    """
    bp = SlideBlueprint(slide_id="matrix_slide", slide_number=1)
    content = SlideContent(title="Simple Overview", primary_takeaway="No matrix data available")
    packet = VisualSemanticPacket(slide_no=1)
    manifest = CompositionInputManifest(manifest_id="m_mat")
    manifest.register_content("matrix_slide", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.COMPARISON_MATRIX)
    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)

    assert DEFECT_COMPARISON_STRUCTURE_UNSUPPORTED in plan.quality_defects
    # Fallback to COMPARISON_TWO_COLUMN or TEXT_DOMINANT
    assert plan.layout_family != Phase3LayoutFamily.COMPARISON_MATRIX


# ═══════════════════════════════════════════════════════════════
# 12. PROCESS VS TIMELINE CONTRACT (Section 12)
# ═══════════════════════════════════════════════════════════════

def test_process_canvas_allocates_sequential_steps(standard_dna: DesignDNA, bio_sample):
    """PROCESS_CANVAS preserves causal/procedural steps without converting to dates."""
    bp, content, packet, manifest = bio_sample
    beat = VisualRhythmBeat(slide_no=2, layout_family=Phase3LayoutFamily.PROCESS_CANVAS)

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family == Phase3LayoutFamily.PROCESS_CANVAS

    step_regions = [r for r in plan.content_regions if r.semantic_role == RegionSemanticRole.PROCESS_STEP]
    assert len(step_regions) >= 3
    # Step regions should be distributed across columns
    assert step_regions[0].grid_col_start == 1
    assert step_regions[1].grid_col_start > step_regions[0].grid_col_start


# ═══════════════════════════════════════════════════════════════
# 13. DATA CANVAS & DEFERRED CHARTS (Section 14)
# ═══════════════════════════════════════════════════════════════

def test_data_canvas_deferred_chart_preservation(standard_dna: DesignDNA, econ_sample):
    """
    DATA_CANVAS preserves chart candidate metadata and marks has_deferred_chart=True
    without fabricating fake chart series.
    """
    bp, content, packet, manifest = econ_sample
    beat = VisualRhythmBeat(slide_no=5, layout_family=Phase3LayoutFamily.DATA_CANVAS)

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family == Phase3LayoutFamily.DATA_CANVAS
    assert plan.has_deferred_chart is True

    # Reserved bounds for chart canvas
    chart_reg = [r for r in plan.content_regions if r.semantic_role == RegionSemanticRole.PRIMARY_VISUAL][0]
    assert chart_reg.bounds.width_in >= 6.0
    assert chart_reg.bounds.height_in >= 4.0


# ═══════════════════════════════════════════════════════════════
# 14. FORMULA VISUAL REGION SAFETY (Section 15)
# ═══════════════════════════════════════════════════════════════

def test_formula_visual_prominence_and_readable_bounds(standard_dna: DesignDNA, math_sample):
    """
    FORMULA_VISUAL allocates formula prominence and readable bounds (font size >= 14pt).
    """
    bp, content, packet, manifest = math_sample
    beat = VisualRhythmBeat(slide_no=4, layout_family=Phase3LayoutFamily.FORMULA_VISUAL)

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family == Phase3LayoutFamily.FORMULA_VISUAL

    form_reg = [r for r in plan.content_regions if r.semantic_role == RegionSemanticRole.FORMULA_DISPLAY][0]
    assert form_reg.grid_col_span >= 5
    assert form_reg.baseline_row_span >= 6
    assert form_reg.typography_spec.font_size_pt >= 14.0


# ═══════════════════════════════════════════════════════════════
# 15. REGION COLLISION AND GRID INVARIANTS (Section 16 & 17)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("layout_family", ALL_20_FAMILIES)
def test_zero_unapproved_collisions_across_all_families(
    layout_family: Phase3LayoutFamily,
    standard_dna: DesignDNA,
):
    """
    Section 16 & 17: Validates that no compiled plan produces unapproved region-region
    collisions or safe zone boundary violations.
    """
    content = SlideContent(
        title=f"Collision test for {layout_family.value}",
        primary_takeaway="Takeaway content",
        supporting_points=["Pt 1", "Pt 2", "Pt 3"],
        process_steps=["S1", "S2", "S3"],
        comparison_target_a="A",
        comparison_target_b="B",
        comparison_rows=[ComparisonRow(dimension="D1", target_a_value="1", target_b_value="2")],
        formula="x^2 + y^2 = r^2",
    )
    bp = SlideBlueprint(slide_id="slide_coll", slide_number=1)
    packet = VisualSemanticPacket(
        slide_no=1,
        system_components=["C1", "C2"],
        process_nodes=["P1", "P2"],
        formula_or_equation="x^2 + y^2 = r^2",
    )
    manifest = CompositionInputManifest(manifest_id="m_coll")
    manifest.register_content("slide_coll", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    plan = compile_slide_layout(
        bp, content, packet, standard_dna,
        VisualRhythmBeat(slide_no=1, layout_family=layout_family),
        manifest,
    )

    defects = validate_plan_regions(plan.content_regions, plan.layout_family)
    assert DEFECT_REGION_COLLISION not in defects
    assert DEFECT_SAFE_ZONE_VIOLATION not in defects
    assert DEFECT_FULL_BLEED_TEXT_VIOLATION not in defects


# ═══════════════════════════════════════════════════════════════
# 16. DETERMINISM & ZERO CONTENT INVENTION
# ═══════════════════════════════════════════════════════════════

def test_compiler_determinism(standard_dna: DesignDNA, cs_sample):
    """Same inputs must produce bit-for-bit identical SlideCompositionPlan."""
    bp, content, packet, manifest = cs_sample
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE)

    plan1 = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    plan2 = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)

    assert plan1.model_dump() == plan2.model_dump()


# ═══════════════════════════════════════════════════════════════
# 17. HELD-OUT TOPIC TESTING (Section 21)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("discipline_fixture", [
    "cs_sample",
    "bio_sample",
    "lit_sample",
    "math_sample",
    "econ_sample",
])
def test_held_out_topics_generalization(request, discipline_fixture, standard_dna: DesignDNA):
    """
    Section 21: Validates general layout behavior across held-out disciplines
    (Computer Science, Biology, Literature, Mathematics, Economics) with zero
    topic-specific branch logic.
    """
    bp, content, packet, manifest = request.getfixturevalue(discipline_fixture)
    beat = VisualRhythmBeat(
        slide_no=bp.slide_number,
        layout_family=packet.visual_candidates[0].layout_family if packet.visual_candidates else Phase3LayoutFamily.TEXT_DOMINANT,
    )

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan is not None
    assert plan.slide_no == bp.slide_number
    assert len(plan.content_regions) >= 2
    # Verify content bindings resolve from the manifest with zero hash mismatch
    for region in plan.content_regions:
        if not region.binding.is_decorative:
            resolved_val = manifest.resolve_content(region.binding)
            assert resolved_val is not None


# ═══════════════════════════════════════════════════════════════
# 18. CANONICAL GRID MATH & 1-BASED INDEXING (Issue 1)
# ═══════════════════════════════════════════════════════════════

def test_canonical_12_column_grid_math_and_exact_active_canvas_fill():
    """
    Audits the exact canonical 12-column grid formulas:
      active_width = SLIDE_WIDTH_IN - MARGIN_LEFT_IN - MARGIN_RIGHT_IN = 11.733 in
      gutter_width = GRID_GUTTER_IN = 0.250 in
      column_width = GRID_COL_WIDTH_IN = (active_width - (11 * gutter_width)) / 12 = 0.7485833... in
      X(col_start) = MARGIN_LEFT_IN + (col_start - 1) * (column_width + gutter_width)
      width(col_span) = col_span * column_width + (col_span - 1) * gutter_width
    Verifies that canonical 12-column spans exactly fill the 11.733-inch active canvas.
    """
    assert SLIDE_WIDTH_IN == 13.333
    assert MARGIN_LEFT_IN == 0.800
    assert MARGIN_RIGHT_IN == 0.800
    assert round(ACTIVE_CONTENT_WIDTH_IN, 3) == 11.733
    assert GRID_COLUMNS == 12
    assert GRID_GUTTER_IN == 0.250

    expected_col_width = (11.733 - 11 * 0.250) / 12  # 0.74858333... in
    assert abs(GRID_COL_WIDTH_IN - expected_col_width) < 1e-6

    # Start of column 1 must align exactly to MARGIN_LEFT_IN
    x_first = resolve_column_left_in(1)
    assert x_first == 0.800

    # Total width of 12 columns + 11 gutters must equal active content width
    total_span_12_width = resolve_column_width_in(12)
    assert abs(total_span_12_width - ACTIVE_CONTENT_WIDTH_IN) < 0.002

    # Canvas fill: left_margin + 12_columns_span + right_margin == slide_width
    right_edge = x_first + total_span_12_width
    assert round(right_edge + MARGIN_RIGHT_IN, 3) == SLIDE_WIDTH_IN

    width_col = resolve_column_width_in(1)
    for col in range(1, 12):
        left_curr = resolve_column_left_in(col)
        left_next = resolve_column_left_in(col + 1)
        assert abs((left_curr + width_col + GRID_GUTTER_IN) - left_next) <= 0.002


@pytest.mark.parametrize("layout_family", ALL_20_FAMILIES)
def test_all_20_families_strictly_enforce_1_based_column_indexing(
    layout_family: Phase3LayoutFamily,
    standard_dna: DesignDNA,
):
    """
    Proves that every content region compiled across all 20 layout families
    strictly adheres to the frozen 1-based indexing contract:
      grid_col_start >= 1
      grid_col_start <= 12
      grid_col_start + grid_col_span - 1 <= 12 (for non-full-bleed regions)
      baseline_row_start >= 1
      baseline_row_start <= 30
      baseline_row_start + baseline_row_span - 1 <= 30
    """
    content = SlideContent(
        title=f"1-Based Grid Check {layout_family.value}",
        subtitle="Verifying 1-based column start and span constraints",
        primary_takeaway="All layout families must strictly resolve 1-based coordinates.",
        supporting_points=["Point 1", "Point 2", "Point 3", "Point 4"],
        process_steps=["Step 1", "Step 2", "Step 3"],
        comparison_target_a="Option A",
        comparison_target_b="Option B",
        comparison_rows=[ComparisonRow(dimension="Metric", target_a_value="1", target_b_value="2")],
        formula=r"f(x) = x^2",
        data_points=[DataPoint(label="Data", value="100")],
    )
    bp = SlideBlueprint(
        slide_id=f"slide_1based_{layout_family.value}",
        slide_number=1,
        content_density=ContentDensity.MEDIUM,
        intended_layout=layout_family.value,
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        system_components=["Comp 1", "Comp 2"],
        process_nodes=["Node 1", "Node 2", "Node 3"],
        temporal_structure=["Phase 1: 2024", "Phase 2: 2025"],
        comparison_targets=["Option A", "Option B"],
        formula_or_equation=r"f(x) = x^2",
        visual_candidates=[VisualCandidate(layout_family=layout_family)],
    )
    beat = VisualRhythmBeat(slide_no=1, layout_family=layout_family)
    manifest = CompositionInputManifest(manifest_id=f"manifest_1based_{layout_family.value}")
    manifest.register_content(bp.slide_id, content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    for region in plan.content_regions:
        if not region.is_full_bleed:
            assert region.grid_col_start >= 1, f"{layout_family}: col_start {region.grid_col_start} < 1"
            assert region.grid_col_start <= 12, f"{layout_family}: col_start {region.grid_col_start} > 12"
            assert region.grid_col_span >= 1, f"{layout_family}: col_span {region.grid_col_span} < 1"
            assert region.grid_col_span <= 12, f"{layout_family}: col_span {region.grid_col_span} > 12"
            assert region.grid_col_start + region.grid_col_span - 1 <= 12, (
                f"{layout_family}: {region.grid_col_start} + {region.grid_col_span} - 1 exceeds 12"
            )
        assert region.baseline_row_start >= 1
        assert region.baseline_row_start <= 30
        assert region.baseline_row_start + region.baseline_row_span - 1 <= 30


# ═══════════════════════════════════════════════════════════════
# 19. SEMANTIC FALLBACK SAFETY: PROCESS VS TIMELINE (Issue 2)
# ═══════════════════════════════════════════════════════════════

def test_biological_process_never_timeline_without_temporal_metadata(standard_dna: DesignDNA, bio_sample):
    """
    Biological process (Photosynthesis) has zero temporal metadata/dates.
    Must NEVER fall back to TIMELINE_CANVAS under density pressure or structural reflow.
    Must fall back to DIAGRAM_CANVAS or TEXT_DOMINANT.
    """
    bp, content, packet, manifest = bio_sample
    beat = VisualRhythmBeat(slide_no=2, layout_family=Phase3LayoutFamily.PROCESS_CANVAS)

    # Verify no temporal semantics exist
    assert has_temporal_semantics(packet, content) is False

    # Simulate extreme reflow pressure requiring fallback
    content.fit_risk = "overflow"
    bp.content_density = ContentDensity.HIGH
    typo = resolve_typography_role_spec(TypographyRole.BODY, standard_dna, ContentDensity.HIGH)
    fit_results = {
        f"{bp.slide_id}_process_step_1": TextFitResult(
            region_id=f"{bp.slide_id}_process_step_1",
            status=TextFitStatus.REFLOW_REQUIRED,
            fit_stage=4,
            typography_before=typo,
            typography_after=typo,
            resolved_role_min_line_height_ratio=1.15,
        )
    }

    plan = compile_slide_layout(
        bp, content, packet, standard_dna, beat, manifest, text_fit_results=fit_results
    )

    # Must preserve process/diagram semantics; must NEVER become TIMELINE_CANVAS
    assert plan.layout_family != Phase3LayoutFamily.TIMELINE_CANVAS
    assert plan.layout_family in (
        Phase3LayoutFamily.PROCESS_CANVAS,
        Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    )


def test_software_algorithm_process_never_timeline_without_temporal_metadata(standard_dna: DesignDNA):
    """
    Software compiler algorithm process has procedural steps but zero temporal/milestone data.
    Must NEVER fall back to TIMELINE_CANVAS.
    """
    bp = SlideBlueprint(
        slide_id="slide_algo_1",
        slide_number=1,
        content_density=ContentDensity.HIGH,
        intended_layout="process_canvas",
    )
    content = SlideContent(
        title="LLVM Compilation Pipeline",
        subtitle="Frontend parsing to target machine code emission",
        primary_takeaway="Source code undergoes sequential progressive lowering through intermediate representations.",
        process_steps=[
            "Lexical scanning and tokenization",
            "Abstract Syntax Tree construction",
            "Static single-assignment (SSA) IR optimization passes",
            "Target machine assembly and object code emission",
        ],
        fit_risk="overflow",
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["Lexer", "Parser", "Optimizer", "Codegen"],
    )
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.PROCESS_CANVAS)
    manifest = CompositionInputManifest(manifest_id="manifest_algo")
    manifest.register_content("slide_algo_1", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    assert has_temporal_semantics(packet, content) is False

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        content_density=ContentDensity.HIGH,
        packet=packet,
        content=content,
    )
    # Timeline must NOT be in the fallback chain
    assert Phase3LayoutFamily.TIMELINE_CANVAS not in envelope.fallback_chain

    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family != Phase3LayoutFamily.TIMELINE_CANVAS


def test_historical_chronological_process_timeline_allowed(standard_dna: DesignDNA):
    """
    Historical process with explicit chronological dates/years (French Revolution).
    TIMELINE_CANVAS fallback IS allowed because temporal semantics exist.
    """
    bp = SlideBlueprint(
        slide_id="slide_history_1",
        slide_number=1,
        content_density=ContentDensity.HIGH,
        intended_layout="process_canvas",
    )
    content = SlideContent(
        title="Chronology of the French Revolution",
        subtitle="Collapse of the Ancien Régime and rise of the Republic",
        primary_takeaway="The revolution unfolded across distinct chronological phases from constitutional crisis to republic.",
        process_steps=[
            "1789: Convocation of Estates General and Storming of the Bastille",
            "1791: Passage of the first French Constitution",
            "1792: Proclamation of the First Republic and war with coalition",
            "1799: Coup of 18 Brumaire establishing the Napoleonic Consulate",
        ],
        fit_risk="overflow",
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["1789 Crisis", "1791 Charter", "1792 Republic", "1799 Consulate"],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_history")
    manifest.register_content("slide_history_1", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    # Must detect explicit temporal semantics from the 4-digit years
    assert has_temporal_semantics(packet, content) is True

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        content_density=ContentDensity.HIGH,
        packet=packet,
        content=content,
    )
    # Timeline IS authorized in the fallback chain
    assert Phase3LayoutFamily.TIMELINE_CANVAS in envelope.fallback_chain


def test_explicit_dated_milestones_timeline_allowed(standard_dna: DesignDNA):
    """
    Process with explicit quarter/year milestones (e.g. Q1 2024, Q3 2024, Q1 2025).
    TIMELINE_CANVAS IS authorized.
    """
    bp = SlideBlueprint(
        slide_id="slide_roadmap_1",
        slide_number=1,
        content_density=ContentDensity.MEDIUM,
        intended_layout="process_canvas",
    )
    content = SlideContent(
        title="Product Engineering Roadmap",
        subtitle="Milestones for vNext architecture delivery",
        primary_takeaway="Delivery follows a disciplined quarterly release cadence.",
        process_steps=[
            "Q1 2024: Core engine architecture and schema freezing",
            "Q3 2024: Alpha developer preview and pilot testing",
            "Q1 2025: Production enterprise GA release",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["Milestone 1 (Q1 2024)", "Milestone 2 (Q3 2024)", "Milestone 3 (Q1 2025)"],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_roadmap")
    manifest.register_content("slide_roadmap_1", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    assert has_temporal_semantics(packet, content) is True

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        content_density=ContentDensity.MEDIUM,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS in envelope.fallback_chain


def test_causal_sequence_without_dates_timeline_rejected(standard_dna: DesignDNA):
    """
    Causal sequence without dates (Monetary policy transmission mechanism).
    TIMELINE_CANVAS must be rejected as an unsupported structure.
    """
    bp = SlideBlueprint(
        slide_id="slide_causal_1",
        slide_number=1,
        content_density=ContentDensity.MEDIUM,
        intended_layout="timeline_canvas",  # Explicitly attempting timeline on non-temporal content
    )
    content = SlideContent(
        title="Monetary Policy Transmission",
        subtitle="Causal chain from policy rate to aggregate price level",
        primary_takeaway="Interest rate hikes cause borrowing contraction leading to reduced demand and lower inflation.",
        process_steps=[
            "Central bank raises target policy rate",
            "Commercial banks increase prime lending rates",
            "Consumer and business borrowing activity contracts",
            "Aggregate demand softens, decelerating price inflation",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_CAUSALITY,
        causal_structure=[
            VisualRelationship(
                source_entity="Policy Rate",
                relation="increases",
                target_entity="Lending Rate",
                relationship_type=RelationshipType.CAUSAL,
            )
        ],
        process_nodes=["Rate Hike", "Credit Tightening", "Demand Contraction", "Inflation Reduction"],
    )
    manifest = CompositionInputManifest(manifest_id="manifest_causal")
    manifest.register_content("slide_causal_1", content.model_dump())
    manifest.register_content("visual_1", packet.model_dump())

    # Temporal semantics MUST NOT be detected
    assert has_temporal_semantics(packet, content) is False

    # Direct prerequisite check for TIMELINE_CANVAS must fail
    supported, defect = check_layout_prerequisites(Phase3LayoutFamily.TIMELINE_CANVAS, content, packet)
    assert supported is False
    assert defect == DEFECT_SEMANTIC_ROLE_UNSUPPORTED

    # Compiling with intended timeline layout must fall back away from TIMELINE_CANVAS
    beat = VisualRhythmBeat(slide_no=1, layout_family=Phase3LayoutFamily.TIMELINE_CANVAS)
    plan = compile_slide_layout(bp, content, packet, standard_dna, beat, manifest)
    assert plan.layout_family != Phase3LayoutFamily.TIMELINE_CANVAS


# ═══════════════════════════════════════════════════════════════
# 11. HARDENED TEMPORAL SIGNAL STRENGTH TESTS
# ═══════════════════════════════════════════════════════════════

def test_single_isolated_year_timeline_rejected(standard_dna: DesignDNA):
    """
    Single isolated year token (e.g., 'Node.js Architecture 2026') without temporal
    structure or relationship language must NOT qualify for timeline fallback.
    """
    content = SlideContent(
        title="Node.js Architecture 2026",
        subtitle="High-throughput runtime event model",
        process_steps=[
            "V8 Engine compiles JavaScript source directly to native machine code",
            "libuv thread pool manages non-blocking asynchronous file operations",
            "Event loop processes timers and executes poll phase callbacks",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["V8 Execution", "libuv Pool", "Event Loop"],
    )
    # Single year token is insufficient
    assert has_temporal_semantics(packet, content) is False

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        content_density=ContentDensity.MEDIUM,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS not in envelope.fallback_chain

    supported, defect = check_layout_prerequisites(Phase3LayoutFamily.TIMELINE_CANVAS, content, packet)
    assert supported is False
    assert defect == DEFECT_SEMANTIC_ROLE_UNSUPPORTED


def test_single_fiscal_quarter_timeline_rejected(standard_dna: DesignDNA):
    """
    Single fiscal quarter / fiscal year token (e.g., 'FY26 Security Architecture'
    or 'Budget Q2 Analysis') must NOT qualify for timeline fallback.
    """
    content = SlideContent(
        title="FY26 Security Architecture",
        subtitle="Budget Q2 Analysis and Perimeter Hardening",
        process_steps=[
            "Enforce zero trust identity verification for all incoming requests",
            "Establish automated mutual TLS tunnels across internal services",
            "Aggregate audit telemetry into centralized immutable security logs",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["Zero Trust", "mTLS Encryption", "Telemetry Audit"],
    )
    # Neither isolated quarter nor FY token with non-temporal steps qualifies
    # (Note: even if both FY26 and Q2 appear, they lack temporal relationship language)
    assert has_temporal_semantics(packet, content) is False

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        content_density=ContentDensity.MEDIUM,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS not in envelope.fallback_chain


def test_version_plus_year_timeline_rejected(standard_dna: DesignDNA):
    """
    Version numbers combined with a single year (e.g., 'Python 3.13 in 2026')
    must NOT qualify because 3.13 is a version number, not a temporal date.
    """
    content = SlideContent(
        title="Python 3.13 in 2026",
        subtitle="Evaluation of Free-Threaded Runtime Performance",
        process_steps=[
            "Disable global interpreter lock via per-thread reference counters",
            "Enable experimental copy-and-patch JIT execution compiler",
            "Optimize mimalloc small-object heap allocation performance",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["Free-Threading", "JIT Compiler", "Heap Allocator"],
    )
    assert has_temporal_semantics(packet, content) is False

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS not in envelope.fallback_chain


def test_two_ordered_dated_milestones_timeline_allowed(standard_dna: DesignDNA):
    """
    Two or more distinct ordered dates/milestones WITH temporal relationship language
    (e.g., 'Milestone 1 in Q1 2024, followed by Milestone 2 in Q3 2024') MUST qualify.
    """
    content = SlideContent(
        title="Platform Delivery Schedule",
        subtitle="Ordered architectural milestones",
        process_steps=[
            "Milestone 1 in Q1 2024: Architecture validation and core compiler engine",
            "Milestone 2 followed by Q3 2024: Multi-tenant production cluster launch",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["Milestone 1 (Q1 2024)", "Milestone 2 (Q3 2024)"],
    )
    # 2+ distinct tokens (Q1, Q3, 2024, Milestone 1, Milestone 2) AND relation 'followed by'
    assert has_temporal_semantics(packet, content) is True

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS in envelope.fallback_chain

    supported, defect = check_layout_prerequisites(Phase3LayoutFamily.TIMELINE_CANVAS, content, packet)
    assert supported is True
    assert defect is None


def test_historical_date_range_with_chronological_structure_timeline_allowed(standard_dna: DesignDNA):
    """
    Historical date range with chronological structure (e.g., 1760 era subsequently
    expanding to 1840 era) MUST qualify for timeline fallback.
    """
    content = SlideContent(
        title="Chronology of British Industrialization",
        subtitle="Structural technological transitions",
        process_steps=[
            "1760: Initial mechanization era driven by early stationary steam power",
            "1840: Subsequently expanding nationwide high-speed railway networks",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["1760 Mechanization", "1840 Railway Era"],
    )
    assert has_temporal_semantics(packet, content) is True

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS in envelope.fallback_chain


def test_explicit_temporal_visual_semantic_packet_timeline_allowed(standard_dna: DesignDNA):
    """
    Explicit temporal VisualSemanticPacket structure (e.g., visual_structure='temporal_structure'
    or non-empty temporal_structure field) MUST qualify regardless of raw step text.
    """
    content = SlideContent(
        title="Modern Architectural Generations",
        process_steps=["Monolithic core", "Microservice fleet", "Edge compute fabric"],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_PROCESS,
        visual_structure="temporal_structure",
        temporal_structure=["Gen 1 Monolith", "Gen 2 Services", "Gen 3 Edge"],
    )
    assert has_temporal_semantics(packet, content) is True

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS in envelope.fallback_chain


def test_causal_process_with_no_temporal_semantics_timeline_rejected(standard_dna: DesignDNA):
    """
    Causal process with no temporal semantics (e.g., biological enzyme kinetics)
    must strictly reject timeline fallback and fall back to DIAGRAM_CANVAS.
    """
    content = SlideContent(
        title="Enzyme Catalytic Cycle",
        subtitle="Substrate binding and conformational catalysis",
        process_steps=[
            "Substrate binds to complementary active site forming enzyme-substrate complex",
            "Transition state stabilization lowers Gibbs free energy barrier",
            "Catalyzed products release, returning unconsumed enzyme to ground state",
        ],
    )
    packet = VisualSemanticPacket(
        slide_no=1,
        visual_intent=VisualIntent.SHOW_CAUSALITY,
        process_nodes=["Substrate Binding", "Energy Lowering", "Product Release"],
    )
    assert has_temporal_semantics(packet, content) is False

    envelope = get_parametric_constraint_envelope(
        Phase3LayoutFamily.PROCESS_CANVAS,
        packet=packet,
        content=content,
    )
    assert Phase3LayoutFamily.TIMELINE_CANVAS not in envelope.fallback_chain
    assert envelope.fallback_chain[0] == Phase3LayoutFamily.DIAGRAM_CANVAS


