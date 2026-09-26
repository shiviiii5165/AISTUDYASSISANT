"""
LearnByGenie PPT vNext — Phase 3.2A Composition Engine Test Suite
===============================================================
Validates Phase 3.2A contracts:
  1. Vertical grid consistency (30 modules * 0.25 in = 7.50 in)
  2. 12-column horizontal grid geometry and safe margins
  3. Stable ContentBinding resolution & immutable manifest
  4. Zero unbound semantic regions
  5. Content hash preservation & tamper detection
  6. Role-specific font size minimums (TypographyRole floors)
  7. Formula non-lossy Unicode fallback & delimiter leak prevention
  8. Accurate RendererCapability classification (NATIVE vs APPLICATION_RESOLVED vs XML_EXTENSION)
  9. Cross-template semantic identity & palette anchor preservation
  10. Whitespace metrics (planned region occupancy)
  11. Parametric constraint envelopes & density adaptation
  12. Zero circular dependencies with frozen schemas.py
"""
import pytest
import hashlib
from typing import Dict, Any

from app.services.presentation.composition_schemas import (
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    VERTICAL_MODULE_HEIGHT_IN,
    CompositionMode,
    RegionSemanticRole,
    CONTENT_BEARING_ROLES,
    RegionAlignment,
    VerticalAlignment,
    RegionOverflowBehavior,
    SpacingToken,
    TypographyRole,
    FormulaRenderMode,
    RendererCapability,
    RENDERER_OPERATION_CAPABILITIES,
    SurfaceToken,
    BorderToken,
    ColorToken,
    QuadrantId,
    SourceKind,
    ROLE_MINIMUM_FONT_SIZES,
    LayoutSafeZone,
    ContentBindingHashMismatch,
    ZONE_TITLE_START,
    ZONE_TITLE_END,
    ZONE_CONTENT_START,
    ZONE_CONTENT_END,
    ZONE_FOOTER_START,
    ZONE_FOOTER_END,
    convert_latex_to_faithful_unicode,
    convert_latex_to_safe_literal,
    FormulaPayload,
    ContentBinding,
    CompositionInputManifest,
    ResolvedRegionBounds,
    TypographyRoleSpec,
    ContentRegion,
    WhitespaceMetrics,
    ResponsiveConstraints,
    SlideCompositionPlan,
    ComposedSlideContext,
    DeckCompositionPlan,
)

from app.services.presentation.grid_engine import (
    MARGIN_LEFT_IN,
    MARGIN_RIGHT_IN,
    MARGIN_TOP_IN,
    MARGIN_BOTTOM_IN,
    ACTIVE_CONTENT_WIDTH_IN,
    ACTIVE_CONTENT_HEIGHT_IN,
    GRID_COLUMNS,
    GRID_GUTTER_IN,
    GRID_COL_WIDTH_IN,
    resolve_column_left_in,
    resolve_column_width_in,
    resolve_row_top_in,
    resolve_row_height_in,
    resolve_region_bounds,
    get_safe_zone_module_bounds,
    snap_to_safe_zone_baseline,
    resolve_region_bounds_in_zone,
    validate_grid_spans,
    detect_region_collision,
    calculate_whitespace_metrics,
    get_layout_constraint_envelope,
    LayoutConstraintEnvelope,
)

from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    ContentDensity,
    VisualIntent,
)


# ═══════════════════════════════════════════════════════════════
# 1. VERTICAL GRID CONSISTENCY & GEOMETRY
# ═══════════════════════════════════════════════════════════════

def test_vertical_grid_mathematical_consistency():
    """Validates that 30 modules * 0.25 in equals exactly 7.50 in slide height."""
    assert VERTICAL_MODULE_COUNT == 30
    assert VERTICAL_MODULE_HEIGHT_IN == 0.250
    total_height = VERTICAL_MODULE_COUNT * VERTICAL_MODULE_HEIGHT_IN
    assert total_height == 7.500
    assert SLIDE_HEIGHT_IN == 7.500


def test_vertical_baseline_coordinate_resolution():
    """Validates row top and height resolution across the 30-module grid."""
    # Row 1 begins at top of slide Y = 0.0"
    assert resolve_row_top_in(1) == 0.000
    assert resolve_row_height_in(1) == 0.250
    
    # Title zone: rows 3..7 (starts at Y=0.50", height=1.25")
    assert resolve_row_top_in(3) == 0.500
    assert resolve_row_height_in(5) == 1.250

    # Last module: row 30 (starts at Y=7.25", height=0.25", ends at Y=7.50")
    assert resolve_row_top_in(30) == 7.250
    assert resolve_row_top_in(30) + resolve_row_height_in(1) == 7.500


def test_vertical_module_span_cross_field_validation():
    """Validates that row_start + row_span - 1 <= 30 is strictly enforced."""
    # Valid: rows 8..27 (active content, span 20) -> 8 + 20 - 1 = 27 <= 30
    valid_bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=8, row_span=20)
    region = ContentRegion(
        region_id="region_valid",
        semantic_role=RegionSemanticRole.PRIMARY_TEXT,
        binding=ContentBinding(
            source_id="slide-1",
            field_path="text",
            resolved_content_hash="mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        ),
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=20,
        bounds=valid_bounds,
    )
    assert region.baseline_row_start == 8
    assert region.baseline_row_span == 20

    # Invalid: row_start 28, span 4 -> 28 + 4 - 1 = 31 > 30 (exceeds total modules)
    with pytest.raises(ValueError, match="exceeds total 30 vertical baseline modules"):
        ContentRegion(
            region_id="region_invalid",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            binding=ContentBinding(
                source_id="slide-1",
                field_path="text",
                resolved_content_hash="mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            ),
            grid_col_start=1,
            grid_col_span=6,
            baseline_row_start=28,
            baseline_row_span=4,
            bounds=ResolvedRegionBounds(left_in=0.8, top_in=6.0, width_in=5.0, height_in=1.0),
        )


# ═══════════════════════════════════════════════════════════════
# 2. 12-COLUMN HORIZONTAL GRID GEOMETRY & BOUNDS
# ═══════════════════════════════════════════════════════════════

def test_12_column_grid_geometry():
    """Validates horizontal 12-column grid metrics and margin preservation."""
    assert GRID_COLUMNS == 12
    assert HORIZONTAL_COLUMN_COUNT == 12
    assert MARGIN_LEFT_IN == 0.800
    assert MARGIN_RIGHT_IN == 0.800
    assert GRID_GUTTER_IN == 0.250

    # First column starts at left margin
    assert resolve_column_left_in(1) == 0.800
    
    # 12 columns + 11 gutters + 2 margins span slide width within rounding
    full_width = resolve_column_width_in(12)
    assert abs((MARGIN_LEFT_IN + full_width + MARGIN_RIGHT_IN) - SLIDE_WIDTH_IN) < 0.010


def test_horizontal_col_span_validation():
    """Validates that col_start + col_span - 1 <= 12 is strictly enforced."""
    # col 10 with span 4 -> 13 > 12 -> must fail
    with pytest.raises(ValueError, match="exceeds 12 columns"):
        ContentRegion(
            region_id="reg_overflow_col",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            binding=ContentBinding(
                source_id="slide-1",
                field_path="text",
                resolved_content_hash="mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            ),
            grid_col_start=10,
            grid_col_span=4,
            baseline_row_start=8,
            baseline_row_span=10,
            bounds=ResolvedRegionBounds(left_in=9.0, top_in=1.75, width_in=3.0, height_in=2.5),
        )


def test_resolved_region_bounds_canvas_containment():
    """Validates that ResolvedRegionBounds enforces full slide boundary containment."""
    # Valid bounds
    b = ResolvedRegionBounds(left_in=1.0, top_in=1.0, width_in=10.0, height_in=5.0)
    assert b.left_in + b.width_in <= SLIDE_WIDTH_IN
    assert b.top_in + b.height_in <= SLIDE_HEIGHT_IN

    # Exceeding width: 10.0 + 4.0 = 14.0 > 13.333
    with pytest.raises(ValueError, match="exceeds slide width"):
        ResolvedRegionBounds(left_in=10.0, top_in=1.0, width_in=4.0, height_in=2.0)

    # Exceeding height: 5.0 + 3.0 = 8.0 > 7.500
    with pytest.raises(ValueError, match="exceeds slide height"):
        ResolvedRegionBounds(left_in=1.0, top_in=5.0, width_in=4.0, height_in=3.0)


# ═══════════════════════════════════════════════════════════════
# 3. STABLE CONTENT BINDING CONTRACT & MANIFEST
# ═══════════════════════════════════════════════════════════════

def test_content_binding_resolution_from_manifest():
    """
    Validates that the renderer resolves displayed content deterministically
    from ContentBinding and CompositionInputManifest without copying or regenerating text.
    """
    manifest = CompositionInputManifest(manifest_id="manifest-photosynthesis-01")
    
    slide_content_raw = {
        "title": "Light-Dependent Reactions in Thylakoids",
        "subtitle": "Conversion of Solar Energy to Chemical Energy",
        "bullets": [
            "Photons excite electrons within Photosystem II reaction centers",
            "Photolysis splits water molecules releasing O₂ and H⁺ protons",
            "ATP synthase harnesses transmembrane electrochemical proton gradient",
        ],
        "metrics": {"atp_yield": "18 ATP", "nadph_yield": "12 NADPH"},
    }
    manifest.register_content("slide_02", slide_content_raw)

    # 1. Resolve title
    hash_title = manifest.compute_field_hash("slide_02", "title")
    b_title = ContentBinding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id="slide_02",
        field_path="title",
        resolved_content_hash=hash_title,
    )
    assert manifest.resolve_content(b_title) == "Light-Dependent Reactions in Thylakoids"

    # 2. Resolve indexed list element
    hash_bullet_1 = manifest.compute_field_hash("slide_02", "bullets[1]")
    b_bullet_1 = ContentBinding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id="slide_02",
        field_path="bullets[1]",
        resolved_content_hash=hash_bullet_1,
    )
    assert manifest.resolve_content(b_bullet_1) == "Photolysis splits water molecules releasing O₂ and H⁺ protons"

    # 3. Resolve nested dictionary element
    hash_metric = manifest.compute_field_hash("slide_02", "metrics.atp_yield")
    b_metric = ContentBinding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id="slide_02",
        field_path="metrics.atp_yield",
        resolved_content_hash=hash_metric,
    )
    assert manifest.resolve_content(b_metric) == "18 ATP"

    # 4. Decorative binding resolves to None
    b_dec = ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE)
    assert manifest.resolve_content(b_dec) is None


def test_zero_unbound_semantic_regions():
    """
    Ensures that content-bearing regions must carry a valid, non-decorative ContentBinding.
    Zero unbound semantic regions are permitted.
    """
    bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=3, row_span=4)

    # Attempting to mark a HEADER_TITLE as decorative must raise ValueError
    with pytest.raises(ValueError, match="cannot carry decorative binding"):
        ContentRegion(
            region_id="reg_title_fake",
            semantic_role=RegionSemanticRole.HEADER_TITLE,
            binding=ContentBinding(is_decorative=True),
            grid_col_start=1,
            grid_col_span=6,
            baseline_row_start=3,
            baseline_row_span=4,
            bounds=bounds,
        )

    # Missing source_id
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty source_id"):
        ContentBinding(source_id="", field_path="text", resolved_content_hash="mock_hash", is_decorative=False)

    # Missing field_path
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty field_path"):
        ContentBinding(source_id="s1", field_path="", resolved_content_hash="mock_hash", is_decorative=False)

    # Missing resolved_content_hash
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty resolved_content_hash"):
        ContentBinding(source_id="s1", field_path="text", resolved_content_hash="", is_decorative=False)

    # Decorative region (BLEED_BACKGROUND or CARD_CONTAINER) succeeds with decorative binding
    card_bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=8, row_span=18)
    card_region = ContentRegion(
        region_id="card_bg_container",
        semantic_role=RegionSemanticRole.CARD_CONTAINER,
        binding=ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE),
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=card_bounds,
    )
    assert card_region.semantic_role == RegionSemanticRole.CARD_CONTAINER
    assert card_region.binding.is_decorative is True


def test_content_hash_preservation():
    """Validates that content hashes are deterministically generated and preserved."""
    manifest = CompositionInputManifest(manifest_id="manifest-hash-test")
    payload_a = {"title": "Quantum Entanglement", "key": "Bell Inequality"}
    payload_b = {"title": "Quantum Entanglement", "key": "Bell Inequality"}
    payload_diff = {"title": "Quantum Superposition", "key": "Schrodinger Cat"}

    hash_a = manifest.register_content("item_a", payload_a)
    hash_b = manifest.register_content("item_b", payload_b)
    hash_diff = manifest.register_content("item_diff", payload_diff)

    # Same content -> identical deterministic hash
    assert hash_a == hash_b
    assert len(hash_a) == 64  # Full SHA-256
    # Different content -> different hash
    assert hash_a != hash_diff



# ═══════════════════════════════════════════════════════════════
# 4. ROLE-AWARE TYPOGRAPHY FLOORS
# ═══════════════════════════════════════════════════════════════

def test_role_specific_font_minimums():
    """
    Validates that minimum readable sizes are enforced per TypographyRole.
    BODY and BODY_EMPHASIS must not collapse to caption-sized typography (8.5pt).
    """
    # BODY floor is 11.0pt
    assert ROLE_MINIMUM_FONT_SIZES[TypographyRole.BODY] == 11.0
    spec_valid_body = TypographyRoleSpec(role=TypographyRole.BODY, font_size_pt=11.0)
    assert spec_valid_body.font_size_pt == 11.0

    # Attempting to shrink BODY to 10.0pt or 8.5pt must raise ValueError
    with pytest.raises(ValueError, match="below role minimum readable floor 11.0pt"):
        TypographyRoleSpec(role=TypographyRole.BODY, font_size_pt=10.0)

    # TITLE floor is 20.0pt
    assert ROLE_MINIMUM_FONT_SIZES[TypographyRole.TITLE] == 20.0
    with pytest.raises(ValueError, match="below role minimum readable floor 20.0pt"):
        TypographyRoleSpec(role=TypographyRole.TITLE, font_size_pt=18.0)

    # CAPTION and ANNOTATION allow smaller role-specific floor (8.5pt)
    assert ROLE_MINIMUM_FONT_SIZES[TypographyRole.CAPTION] == 8.5
    spec_caption = TypographyRoleSpec(role=TypographyRole.CAPTION, font_size_pt=8.5)
    assert spec_caption.font_size_pt == 8.5

    # TABLE_BODY floor is 9.0pt
    assert ROLE_MINIMUM_FONT_SIZES[TypographyRole.TABLE_BODY] == 9.0
    spec_table = TypographyRoleSpec(role=TypographyRole.TABLE_BODY, font_size_pt=9.0)
    assert spec_table.font_size_pt == 9.0


# ═══════════════════════════════════════════════════════════════
# 5. FORMULA FIDELITY & NON-LOSSY FALLBACK
# ═══════════════════════════════════════════════════════════════

def test_formula_non_lossy_unicode_fallback():
    """
    Validates faithful Unicode conversion:
    - E_k -> Eₖ (never lossy Ek)
    - x^2 + y^2 = z^2 -> x² + y² = z²
    - Zero raw LaTeX delimiters ($) leak into user-visible output.
    """
    # 1. Kinetic energy equation: E_k = \frac{1}{2}mv^2
    latex_ek = r"E_k = \frac{1}{2}mv^2"
    unicode_ek = convert_latex_to_faithful_unicode(latex_ek)
    assert "Eₖ" in unicode_ek, f"Expected 'Eₖ' with subscript k, got '{unicode_ek}'"
    assert "Ek" not in unicode_ek, "Must not collapse E_k to lossy 'Ek'"
    assert "½" in unicode_ek
    assert "v²" in unicode_ek

    # 2. Delimiter leak prevention: $$ raw delimiters must never leak
    latex_delimited = r"$$\lambda_{max} \approx 2.898 \times 10^{-3} \text{ m}\cdot\text{K}$$"
    unicode_clean = convert_latex_to_faithful_unicode(latex_delimited)
    assert "$" not in unicode_clean, "Raw LaTeX $ delimiter leaked into output"
    assert "λ" in unicode_clean
    assert "×" in unicode_clean


def test_formula_payload_preserves_source_and_typed_modes():
    """Validates that FormulaPayload preserves raw LaTeX and supports typed modes."""
    raw = r"$$H\psi = E\psi$$"
    payload = FormulaPayload(
        original_source=raw,
        render_mode=FormulaRenderMode.UNICODE_TEXT,
    )
    # Original source preserved
    assert payload.original_source == raw
    # Faithful unicode populated without $
    assert "$" not in payload.unicode_representation
    assert "ψ" in payload.unicode_representation
    assert payload.render_mode == FormulaRenderMode.UNICODE_TEXT


# ═══════════════════════════════════════════════════════════════
# 6. RENDERER CAPABILITY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

def test_renderer_capability_classification():
    """
    Accurately classifies python-pptx rendering capabilities.
    Does not claim automatic font fallback chains are natively guaranteed by python-pptx.
    """
    # Primary font assignment is NATIVE
    assert RENDERER_OPERATION_CAPABILITIES["primary_font_assignment"] == RendererCapability.NATIVE
    assert RENDERER_OPERATION_CAPABILITIES["font_size_assignment"] == RendererCapability.NATIVE
    assert RENDERER_OPERATION_CAPABILITIES["font_color_assignment"] == RendererCapability.NATIVE

    # Font fallback selection is APPLICATION_RESOLVED by LearnByGenie
    assert RENDERER_OPERATION_CAPABILITIES["fallback_font_selection"] == RendererCapability.APPLICATION_RESOLVED

    # Shape alt text and description manipulation is XML_EXTENSION
    assert RENDERER_OPERATION_CAPABILITIES["shape_alt_text"] == RendererCapability.XML_EXTENSION
    assert RENDERER_OPERATION_CAPABILITIES["shape_description"] == RendererCapability.XML_EXTENSION

    # Equations and native charts are DEFERRED to Phase 3.3
    assert RENDERER_OPERATION_CAPABILITIES["omml_native_equation"] == RendererCapability.DEFERRED
    assert RENDERER_OPERATION_CAPABILITIES["chart_native_rendering"] == RendererCapability.DEFERRED


# ═══════════════════════════════════════════════════════════════
# 7. CROSS-TEMPLATE IDENTITY PROOF & PALETTE PRESERVATION
# ═══════════════════════════════════════════════════════════════

def test_cross_template_semantic_identity():
    """
    For the same Photosynthesis semantic slide across all five templates:
    1. Same SlideContent identifier / hash
    2. Same VisualSemanticPacket identifier / hash
    3. Same visual intent (PROCESS_FLOW)
    4. Same user palette anchor
    Only geometry, typography hierarchy, spacing, surface treatment, and whitespace differ.
    """
    raw_content = {
        "title": "Photosynthesis: Light-Dependent Reactions",
        "steps": ["Photosystem II", "Plastoquinone", "Cytochrome b6f", "Photosystem I", "ATP Synthase"],
        "formula": r"2H_2O + 2NADP^+ \to O_2 + 2NADPH + 2H^+",
    }
    content_hash = hashlib.sha256(str(raw_content).encode()).hexdigest()  # Full 64-char SHA-256
    packet_hash = hashlib.sha256(b"packet_photo_chem_001").hexdigest()    # Full 64-char SHA-256
    user_palette_anchor = "emerald_botany"
    visual_intent = VisualIntent.SHOW_PROCESS

    templates = [
        ("academic_clean", Phase3LayoutFamily.SPLIT_40_60),
        ("modern_minimal", Phase3LayoutFamily.HERO_CENTER),
        ("technical_grid", Phase3LayoutFamily.PROCESS_CANVAS),
        ("editorial", Phase3LayoutFamily.ASYMMETRIC_EDITORIAL),
        ("visual_learning", Phase3LayoutFamily.SYSTEM_ARCHITECTURE),
    ]

    plans: Dict[str, SlideCompositionPlan] = {}
    contexts: Dict[str, ComposedSlideContext] = {}

    for tname, lfam in templates:
        # Build layout-specific bounds based on envelope
        envelope = get_layout_constraint_envelope(lfam, ContentDensity.MEDIUM)
        pref_text = envelope.preferred_text_col_span
        pref_vis = envelope.preferred_visual_col_span or max(1, 12 - pref_text)

        if pref_text + pref_vis <= 12:
            # Side-by-side split layout
            text_bounds = resolve_region_bounds(col_start=1, col_span=pref_text, row_start=8, row_span=18)
            vis_bounds = resolve_region_bounds(col_start=pref_text + 1, col_span=pref_vis, row_start=8, row_span=18)
            t_col_start, t_col_span = 1, pref_text
            t_row_start, t_row_span = 8, 18
            v_col_start, v_col_span = pref_text + 1, pref_vis
            v_row_start, v_row_span = 8, 18
        else:
            # Vertically stacked layout (e.g. process flow or hero canvas)
            t_col_start, t_col_span = 1, 12
            t_row_start, t_row_span = 8, 6
            v_col_start, v_col_span = 1, 12
            v_row_start, v_row_span = 15, 12
            text_bounds = resolve_region_bounds(col_start=t_col_start, col_span=t_col_span, row_start=t_row_start, row_span=t_row_span)
            vis_bounds = resolve_region_bounds(col_start=v_col_start, col_span=v_col_span, row_start=v_row_start, row_span=v_row_span)

        r_text = ContentRegion(
            region_id=f"text_{tname}",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            binding=ContentBinding(
                source_id="photo_01",
                field_path="steps",
                resolved_content_hash=content_hash,
                source_object_hash=content_hash,
            ),
            grid_col_start=t_col_start,
            grid_col_span=t_col_span,
            baseline_row_start=t_row_start,
            baseline_row_span=t_row_span,
            bounds=text_bounds,
        )
        r_vis = ContentRegion(
            region_id=f"vis_{tname}",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            binding=ContentBinding(
                source_id="photo_01",
                field_path="formula",
                resolved_content_hash=content_hash,
                source_object_hash=content_hash,
            ),
            grid_col_start=v_col_start,
            grid_col_span=v_col_span,
            baseline_row_start=v_row_start,
            baseline_row_span=v_row_span,
            bounds=vis_bounds,
        )

        ws = calculate_whitespace_metrics([r_text, r_vis])

        plan = SlideCompositionPlan(
            slide_no=2,
            layout_family=lfam,
            composition_mode=CompositionMode.SPLIT_COLUMNS,
            content_regions=[r_text, r_vis],
            whitespace_metrics=ws,
            template_name=tname,
            palette_name=user_palette_anchor,
        )
        ctx = ComposedSlideContext(
            slide_no=2,
            composition_plan=plan,
            composition_input_manifest_id="manifest-photosynthesis-proof",
            slide_content_id="photo_01",
            slide_content_hash=content_hash,
            visual_packet_id="packet_photo_chem_001",
            visual_packet_hash=packet_hash,
        )
        plans[tname] = plan
        contexts[tname] = ctx

    # Assert invariant semantic identity across all 5 templates
    hashes_seen = {ctx.slide_content_hash for ctx in contexts.values()}
    packet_hashes_seen = {ctx.visual_packet_hash for ctx in contexts.values()}
    palettes_seen = {p.palette_name for p in plans.values()}

    assert len(hashes_seen) == 1, "Slide content hash must be identical across all 5 templates"
    assert len(packet_hashes_seen) == 1, "Visual packet hash must be identical across all 5 templates"
    assert len(palettes_seen) == 1, "User palette anchor must be preserved across all 5 templates"
    assert list(palettes_seen)[0] == user_palette_anchor

    # Assert geometry differs appropriately
    col_spans = [p.content_regions[0].grid_col_span for p in plans.values()]
    assert len(set(col_spans)) > 1, "Geometry column spans must adapt per template constraint envelope"


# ═══════════════════════════════════════════════════════════════
# 8. WHITESPACE METRICS (PLANNED REGION OCCUPANCY)
# ═══════════════════════════════════════════════════════════════

def test_whitespace_metrics_planned_occupancy():
    """
    Validates that WhitespaceMetrics measures planned geometric REGION OCCUPANCY
    (not rendered ink/pixels) and calculates quadrant balance.
    """
    mock_hash = "mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    # Title region: cols 1..12, rows 3..6 (height 1.0", width ~11.733", area ~11.73 sq in)
    r_title = ContentRegion(
        region_id="ws_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        binding=ContentBinding(source_id="s1", field_path="title", resolved_content_hash=mock_hash),
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=resolve_region_bounds(1, 12, 3, 4),
    )
    # Left content: cols 1..6, rows 8..24 (height 4.25", width ~5.74", area ~24.4 sq in)
    r_body = ContentRegion(
        region_id="ws_body",
        semantic_role=RegionSemanticRole.PRIMARY_TEXT,
        binding=ContentBinding(source_id="s1", field_path="body", resolved_content_hash=mock_hash),
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=17,
        bounds=resolve_region_bounds(1, 6, 8, 17),
    )

    metrics = calculate_whitespace_metrics([r_title, r_body], target_band_min=0.20, target_band_max=0.65)
    
    # Occupied area ratio + planned whitespace ratio == 1.0
    assert abs((metrics.region_occupied_area_ratio + metrics.planned_whitespace_ratio) - 1.0) < 0.005
    assert metrics.region_occupied_area_ratio > 0.20
    assert metrics.planned_whitespace_ratio < 0.80
    assert metrics.is_within_role_band is True
    # Quadrant weights sum to 1.0
    assert abs(sum(metrics.quadrant_weights.values()) - 1.0) < 0.010



# ═══════════════════════════════════════════════════════════════
# 9. PARAMETRIC CONSTRAINT ENVELOPES & DENSITY ADAPTATION
# ═══════════════════════════════════════════════════════════════

def test_layout_constraint_envelope_density_adaptation():
    """
    Validates that layout families act as flexible parametric constraint envelopes,
    dynamically adjusting spans according to content density.
    """
    # SPLIT_40_60 on MEDIUM density prefers 5 text / 7 visual
    env_med = get_layout_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, ContentDensity.MEDIUM)
    assert env_med.preferred_text_col_span == 5
    assert env_med.preferred_visual_col_span == 7

    # Under HIGH density, adapts to 6 text / 6 visual to accommodate text length
    env_high = get_layout_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, ContentDensity.HIGH)
    assert env_high.preferred_text_col_span == 6
    assert env_high.preferred_visual_col_span == 6


# ═══════════════════════════════════════════════════════════════
# 10. DEPENDENCY SAFETY & ZERO CIRCULAR IMPORTS
# ═══════════════════════════════════════════════════════════════

def test_zero_circular_dependencies():
    """
    Ensures that composition_schemas and grid_engine do not import from frozen schemas.py,
    maintaining strict unidirectional dependency layering.
    """
    import sys
    import app.services.presentation.composition_schemas as cs
    import app.services.presentation.grid_engine as ge

    # Check module attributes to ensure SlideSpec is NOT imported or defined here
    assert not hasattr(cs, "SlideSpec"), "composition_schemas must not depend on frozen SlideSpec"
    assert not hasattr(ge, "SlideSpec"), "grid_engine must not depend on frozen SlideSpec"


# ═══════════════════════════════════════════════════════════════
# 11. SAFE ZONE + BASELINE GRID CONTRACT
# ═══════════════════════════════════════════════════════════════

def test_safe_zone_containment_and_baseline_snapping():
    """
    Validates safe zones as containment authority and baseline grid as alignment authority:
    - Title regions remain inside title-safe bounds (rows 3..7)
    - Content regions remain inside content-safe bounds (rows 8..27)
    - Footer regions remain inside footer-safe bounds (rows 28..30)
    - Snap function snaps coordinates to nearest valid baseline inside permitted zone.
    """
    mock_hash = "mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    # 1. Title region within title-safe zone [3..7] succeeds
    title_bounds = resolve_region_bounds(col_start=1, col_span=12, row_start=3, row_span=4)
    r_title = ContentRegion(
        region_id="safe_title_reg",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        safe_zone=LayoutSafeZone.SAFE_TITLE,
        binding=ContentBinding(source_id="s1", field_path="title", resolved_content_hash=mock_hash),
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=title_bounds,
    )
    assert r_title.safe_zone == LayoutSafeZone.SAFE_TITLE
    assert r_title.baseline_row_start == 3
    assert r_title.baseline_row_start + r_title.baseline_row_span - 1 <= ZONE_TITLE_END

    # Title placed outside title zone (e.g. at row 8) must fail containment check
    with pytest.raises(ValueError, match="exceed title-safe zone"):
        ContentRegion(
            region_id="title_out_of_zone",
            semantic_role=RegionSemanticRole.HEADER_TITLE,
            safe_zone=LayoutSafeZone.SAFE_TITLE,
            binding=ContentBinding(source_id="s1", field_path="title", resolved_content_hash=mock_hash),
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=8,
            baseline_row_span=4,
            bounds=resolve_region_bounds(col_start=1, col_span=12, row_start=8, row_span=4),
        )

    # 2. Content region within content-safe zone [8..27] succeeds
    content_bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=8, row_span=18)
    r_content = ContentRegion(
        region_id="safe_content_reg",
        semantic_role=RegionSemanticRole.PRIMARY_TEXT,
        safe_zone=LayoutSafeZone.SAFE_CONTENT,
        binding=ContentBinding(source_id="s1", field_path="text", resolved_content_hash=mock_hash),
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=content_bounds,
    )
    assert r_content.safe_zone == LayoutSafeZone.SAFE_CONTENT
    assert r_content.baseline_row_start == 8
    assert r_content.baseline_row_start + r_content.baseline_row_span - 1 <= ZONE_CONTENT_END

    # Content placed outside content zone (e.g. starting at row 3 or extending to row 28) must fail
    with pytest.raises(ValueError, match="exceed content-safe zone"):
        ContentRegion(
            region_id="content_in_title_zone",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=ContentBinding(source_id="s1", field_path="text", resolved_content_hash=mock_hash),
            grid_col_start=1,
            grid_col_span=6,
            baseline_row_start=3,
            baseline_row_span=4,
            bounds=resolve_region_bounds(col_start=1, col_span=6, row_start=3, row_span=4),
        )

    # 3. Footer region within footer-safe zone [28..30] succeeds
    footer_bounds = resolve_region_bounds(col_start=1, col_span=12, row_start=28, row_span=2)
    r_footer = ContentRegion(
        region_id="safe_footer_reg",
        semantic_role=RegionSemanticRole.FOOTER_CITATION,
        safe_zone=LayoutSafeZone.SAFE_FOOTER,
        binding=ContentBinding(source_id="s1", field_path="footer", resolved_content_hash=mock_hash),
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=28,
        baseline_row_span=2,
        bounds=footer_bounds,
    )
    assert r_footer.safe_zone == LayoutSafeZone.SAFE_FOOTER
    assert r_footer.baseline_row_start == 28

    # Footer placed at row 25 must fail
    with pytest.raises(ValueError, match="exceed footer-safe zone"):
        ContentRegion(
            region_id="footer_out_of_zone",
            semantic_role=RegionSemanticRole.FOOTER_CITATION,
            safe_zone=LayoutSafeZone.SAFE_FOOTER,
            binding=ContentBinding(source_id="s1", field_path="footer", resolved_content_hash=mock_hash),
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=25,
            baseline_row_span=2,
            bounds=resolve_region_bounds(col_start=1, col_span=12, row_start=25, row_span=2),
        )

    # 4. Baseline grid snapping to permitted safe zone
    # Target row_start=1 for CONTENT zone snaps to row 8
    snapped_start, snapped_span = snap_to_safe_zone_baseline(target_row_start=1, target_row_span=4, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    assert snapped_start == ZONE_CONTENT_START  # 8
    assert snapped_span == 4

    # Target row_start=25, span=6 for CONTENT zone (would reach 30) clamps inside 27
    snapped_start_end, snapped_span_end = snap_to_safe_zone_baseline(target_row_start=25, target_row_span=6, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    assert snapped_start_end + snapped_span_end - 1 <= ZONE_CONTENT_END  # <= 27

    # Snapping for TITLE zone
    t_start, t_span = snap_to_safe_zone_baseline(target_row_start=1, target_row_span=3, safe_zone=LayoutSafeZone.SAFE_TITLE)
    assert t_start == ZONE_TITLE_START  # 3
    assert t_start + t_span - 1 <= ZONE_TITLE_END

    # Snapping for FOOTER zone
    f_start, f_span = snap_to_safe_zone_baseline(target_row_start=15, target_row_span=2, safe_zone=LayoutSafeZone.SAFE_FOOTER)
    assert f_start == ZONE_FOOTER_START  # 28
    assert f_start + f_span - 1 <= ZONE_FOOTER_END

    # resolve_region_bounds_in_zone returns valid bounds strictly within safe zone
    bounds, r_start, r_span = resolve_region_bounds_in_zone(col_start=1, col_span=6, row_start=2, row_span=5, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    assert r_start == 8
    assert bounds.top_in >= 1.750  # row 8 starts at 7 * 0.25 = 1.75"


# ═══════════════════════════════════════════════════════════════
# 12. FULL BLEED VS ORDINARY SEMANTIC BOUNDARIES
# ═══════════════════════════════════════════════════════════════

def test_full_bleed_and_ordinary_semantic_text_boundaries():
    """
    Validates boundary rules:
    - Full-bleed decorative visuals may reach slide edges.
    - Ordinary semantic text regions may never use FULL_BLEED or is_full_bleed=True.
    """
    # Full-bleed decorative visual may reach slide edges
    bleed_bounds = resolve_region_bounds(col_start=1, col_span=12, row_start=1, row_span=30, is_full_bleed=True)
    assert bleed_bounds.left_in == 0.0
    assert bleed_bounds.top_in == 0.0
    assert bleed_bounds.width_in == SLIDE_WIDTH_IN
    assert bleed_bounds.height_in == SLIDE_HEIGHT_IN

    bleed_region = ContentRegion(
        region_id="decorative_bleed_bg",
        semantic_role=RegionSemanticRole.BLEED_BACKGROUND,
        safe_zone=LayoutSafeZone.FULL_BLEED,
        binding=ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE),
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=1,
        baseline_row_span=30,
        bounds=bleed_bounds,
        is_full_bleed=True,
    )
    assert bleed_region.is_full_bleed is True
    assert bleed_region.safe_zone == LayoutSafeZone.FULL_BLEED

    # Ordinary semantic text must never use FULL_BLEED or is_full_bleed=True
    mock_hash = "mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    
    with pytest.raises(ValueError, match="Ordinary semantic text/content region .* cannot use FULL_BLEED"):
        ContentRegion(
            region_id="illegal_bleed_title",
            semantic_role=RegionSemanticRole.HEADER_TITLE,
            safe_zone=LayoutSafeZone.FULL_BLEED,
            binding=ContentBinding(source_id="s1", field_path="title", resolved_content_hash=mock_hash),
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=1,
            baseline_row_span=4,
            bounds=bleed_bounds,
            is_full_bleed=True,
        )

    with pytest.raises(ValueError, match="Ordinary semantic text/content region .* cannot use FULL_BLEED"):
        ContentRegion(
            region_id="illegal_bleed_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.FULL_BLEED,
            binding=ContentBinding(source_id="s1", field_path="text", resolved_content_hash=mock_hash),
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=8,
            baseline_row_span=10,
            bounds=bleed_bounds,
            is_full_bleed=True,
        )


# ═══════════════════════════════════════════════════════════════
# 13. CONTENT HASH INTEGRITY & NEGATIVE MUTATION DEFECT
# ═══════════════════════════════════════════════════════════════

def test_content_hash_integrity_and_mutation_defect():
    """
    Validates content hash integrity:
    - Distinction between source_object_hash and resolved_content_hash.
    - Full SHA-256 (64 hex characters) stored internally.
    - Short hash prefix (16 chars) available via short_hash() for debug/logs only.
    - resolve_content verifies payload hash before returning.
    - Negative mutation test: tampering with content raises structured ContentBindingHashMismatch.
    """
    manifest = CompositionInputManifest(manifest_id="manifest-hash-integrity")
    raw_slide = {
        "title": "Quantum Teleportation Protocols",
        "key_takeaway": "Entangled Bell pairs enable instantaneous state transfer without superluminal signaling.",
        "author": "Alice & Bob",
    }
    source_id = "slide_teleport_01"
    manifest.register_content(source_id, raw_slide)

    source_obj_hash = manifest.slide_content_hashes[source_id]
    assert len(source_obj_hash) == 64, "source_object_hash must be full 64-char SHA-256"

    resolved_hash = manifest.compute_field_hash(source_id, "key_takeaway")
    assert len(resolved_hash) == 64, "resolved_content_hash must be full 64-char SHA-256"
    assert source_obj_hash != resolved_hash, "source_object_hash and resolved_content_hash must be distinct"

    binding = ContentBinding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id=source_id,
        field_path="key_takeaway",
        source_object_hash=source_obj_hash,
        resolved_content_hash=resolved_hash,
    )
    assert len(binding.resolved_content_hash) == 64
    assert binding.short_hash() == resolved_hash[:16]

    # Valid resolution succeeds
    resolved_text = manifest.resolve_content(binding, region_id="region_teleport_takeaway")
    assert resolved_text == raw_slide["key_takeaway"]

    # NEGATIVE MUTATION TEST: Tampering with raw payload raises ContentBindingHashMismatch
    manifest.raw_content_items[source_id]["key_takeaway"] = "Tampered unauthorized content modification."
    
    with pytest.raises(ContentBindingHashMismatch) as exc_info:
        manifest.resolve_content(binding, region_id="region_teleport_takeaway")

    defect = exc_info.value
    assert isinstance(defect, ValueError)
    assert defect.region_id == "region_teleport_takeaway"
    assert defect.field_path == "key_takeaway"
    assert defect.expected_hash == resolved_hash
    assert len(defect.actual_hash) == 64
    assert defect.actual_hash != resolved_hash
    assert "CONTENT_BINDING_HASH_MISMATCH" in str(defect)


# ═══════════════════════════════════════════════════════════════
# 14. STRICT COMPLETE BINDINGS ENFORCEMENT
# ═══════════════════════════════════════════════════════════════

def test_strict_complete_binding_enforcement():
    """
    Validates complete bindings requirement:
    - Every non-decorative content-bearing region requires:
      source_kind != DECORATIVE, source_id non-empty, field_path non-empty, resolved_content_hash non-empty.
    - Evidence refs are preserved when grounded.
    - Decorative regions may omit semantic bindings ONLY when is_decorative=True and semantic role is non-content-bearing.
    - Regions cannot pass using source_id OR field_path alone; both are strictly required.
    """
    mock_hash = "mock_hash_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=8, row_span=10)

    # 1. Valid complete binding succeeds
    complete_binding = ContentBinding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id="slide_ev_01",
        field_path="supporting_evidence[0]",
        resolved_content_hash=mock_hash,
        evidence_refs=["cite_nature_2024", "cite_arxiv_quantum"],
    )
    region = ContentRegion(
        region_id="ev_region",
        semantic_role=RegionSemanticRole.PRIMARY_TEXT,
        binding=complete_binding,
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=10,
        bounds=bounds,
    )
    assert region.binding.source_id == "slide_ev_01"
    assert region.binding.field_path == "supporting_evidence[0]"
    assert region.binding.evidence_refs == ["cite_nature_2024", "cite_arxiv_quantum"]

    # 2. Rejects missing source_id (even if field_path is present)
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty source_id"):
        ContentBinding(source_id="", field_path="supporting_evidence[0]", resolved_content_hash=mock_hash)

    # 3. Rejects missing field_path (even if source_id is present)
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty field_path"):
        ContentBinding(source_id="slide_ev_01", field_path="", resolved_content_hash=mock_hash)

    # 4. Rejects missing resolved_content_hash
    with pytest.raises(ValueError, match="Non-decorative ContentBinding requires a non-empty resolved_content_hash"):
        ContentBinding(source_id="slide_ev_01", field_path="supporting_evidence[0]", resolved_content_hash="")

    # 5. Rejects source_kind = DECORATIVE on non-decorative binding
    with pytest.raises(ValueError, match="Non-decorative ContentBinding cannot have source_kind=DECORATIVE"):
        ContentBinding(
            source_kind=SourceKind.DECORATIVE,
            source_id="slide_ev_01",
            field_path="supporting_evidence[0]",
            resolved_content_hash=mock_hash,
            is_decorative=False,
        )

    # 6. Rejects decorative binding on content-bearing role
    with pytest.raises(ValueError, match="cannot carry decorative binding"):
        ContentRegion(
            region_id="illegal_dec_role",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            binding=ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE),
            grid_col_start=1,
            grid_col_span=6,
            baseline_row_start=8,
            baseline_row_span=10,
            bounds=bounds,
        )

    # 7. Decorative region (non-content-bearing) succeeds with decorative binding
    card_bounds = resolve_region_bounds(col_start=1, col_span=6, row_start=8, row_span=10)
    card_region = ContentRegion(
        region_id="card_divider",
        semantic_role=RegionSemanticRole.CARD_CONTAINER,
        binding=ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE),
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=10,
        bounds=card_bounds,
    )
    assert card_region.semantic_role == RegionSemanticRole.CARD_CONTAINER
    assert card_region.binding.is_decorative is True

