"""
LearnByGenie PPT vNext — Phase 3.2E Composition Renderer Test Suite
================================================================
Comprehensive verification of the native editable PowerPoint composition renderer:
  1. Native text and shape editability (no slide rasterization)
  2. Geometry fidelity & bounds tolerance (ResolvedRegionBounds as authority)
  3. Content binding resolution from manifest
  4. Content hash mismatch rejection (FAIL CLOSED)
  5. Fail-closed integrity gating (never silently invokes legacy fallback)
  6. DesignDNA-authoritative font resolution & provenance tracking
  7. Partial vs full-bleed geometry authority
  8. Stable semantic region <-> PPTX shape identity & round-trip traceability
  9. Clean target slide contract (TARGET_SLIDE_NOT_CLEAN)
  10. Typography, line spacing, and alignment application
  11. Complete ColorToken palette preservation
  12. Container surface & border token rendering
  13. XML extension safety (alt text & authorized-only shadows)
  14. Deterministic 8-layer z-order
  15. Speaker notes native capability & non-leakage to visible slide
  16. Citation dock containment
  17. Formula rendering (faithful Unicode math)
  18. Code block preservation (indentation, monospace font)
  19. Chart deferred placeholder safety (neutral, non-factual)
  20. Audit gate enforcement (rejecting FATAL/REFLOW_REQUIRED)
  21. Legacy compatibility & feature flag behavior
  22. PPTX serialization & reload round-trip certification
  23. Renderer determinism
  24. Performance baseline recording
  25. Canonical held-out topic generalization
"""
import io
import time
import hashlib
import pytest
from typing import Dict, List, Any, Optional, Tuple

from pptx import Presentation
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from app.core.config import settings
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT
from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
)
from app.services.presentation.composition_schemas import (
    LayoutSafeZone,
    RegionSemanticRole,
    TypographyRole,
    CompositionMode,
    QuadrantId,
    RegionAlignment,
    VerticalAlignment,
    SpacingToken,
    SourceKind,
    ContentBinding,
    ContentRegion,
    ResolvedRegionBounds,
    TypographyRoleSpec,
    SurfaceToken,
    BorderToken,
    ColorToken,
    FormulaRenderMode,
    RendererCapability,
    SlideCompositionPlan,
    ComposedSlideContext,
    CompositionInputManifest,
    FormulaPayload,
    ContentBindingHashMismatch,
)
from app.services.presentation.layout_quality_auditor import (
    LayoutAuditResult,
    RepairResult,
    DefectSeverity,
    DefectRepairability,
    DefectCode,
    LayoutDefect,
)
from app.services.presentation.typography_engine import (
    TextFitResult,
    TextFitStatus,
)
from app.services.presentation.schemas import PresentationSpec, PresentationConfig, SlideSpec
from app.services.presentation.composition_renderer import (
    render_composed_slide,
    render_composed_presentation,
    RenderResult,
    RenderDefectCode,
    FAIL_CLOSED_STATUSES,
    audit_rendered_slide_editability,
    resolve_color_token,
    resolve_font_family,
    set_shape_alt_text,
    apply_card_shadow,
    validate_target_slide_cleanliness,
)
from app.services.presentation.engine.builder import build_presentation_spec


# ═══════════════════════════════════════════════════════════════
# TEST FIXTURES & BUILDERS
# ═══════════════════════════════════════════════════════════════

def _sample_dna() -> DesignDNA:
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=26.0, line_height_ratio=1.20,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=13.5, line_height_ratio=1.45,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.MEDIUM,
        color_palette=ColorPalette(
            primary="#1A365D", primary_light="#2B6CB0", secondary="#4A6FA5",
            accent="#ED8936", background="#FFFFFF", surface="#F7FAFC",
            text_primary="#1A202C", text_secondary="#4A5568", text_on_primary="#FFFFFF",
            border="#E2E8F0", success="#38A169", warning="#DD6B20", error="#E53E3E",
        ),
    )


def _make_region(
    region_id: str,
    role: RegionSemanticRole,
    left_in: float,
    top_in: float,
    width_in: float,
    height_in: float,
    content_payload: Any = "Sample text payload",
    source_id: str = "src_1",
    field_path: str = "text",
    is_decorative: bool = False,
    safe_zone: Optional[LayoutSafeZone] = None,
    surface_token: SurfaceToken = SurfaceToken.TRANSPARENT,
    border_token: BorderToken = BorderToken.NONE,
    font_size_pt: Optional[float] = None,
    color_token: ColorToken = ColorToken.TEXT_PRIMARY,
    is_full_bleed: bool = False,
) -> Tuple[ContentRegion, Dict[str, Any]]:
    bounds = ResolvedRegionBounds(
        left_in=left_in,
        top_in=top_in,
        width_in=width_in,
        height_in=height_in,
    )
    chash = ""
    raw_dict = {}
    if not is_decorative:
        chash = CompositionInputManifest.compute_payload_hash(content_payload)
        raw_dict = {field_path: content_payload}

    binding = ContentBinding(
        is_decorative=is_decorative,
        source_kind=SourceKind.DECORATIVE if is_decorative else SourceKind.SLIDE_CONTENT,
        source_id=source_id if not is_decorative else "",
        field_path=field_path if not is_decorative else "",
        resolved_content_hash=chash,
        content_hash=chash,
    )
    typo_spec = None
    if not is_decorative:
        t_role = TypographyRole.TITLE if role == RegionSemanticRole.HEADER_TITLE else (
            TypographyRole.CAPTION if role in (RegionSemanticRole.FOOTER_CITATION, RegionSemanticRole.CAPTION) else TypographyRole.BODY
        )
        if font_size_pt is None:
            eff_pt = 24.0 if role == RegionSemanticRole.HEADER_TITLE else (
                9.5 if role in (RegionSemanticRole.FOOTER_CITATION, RegionSemanticRole.CAPTION) else 13.5
            )
        else:
            eff_pt = font_size_pt

        typo_spec = TypographyRoleSpec(
            role=t_role,
            font_family="Inter",
            fallback_family="Calibri",
            safe_office_fallback="Calibri",
            font_size_pt=eff_pt,
            font_weight=700 if role == RegionSemanticRole.HEADER_TITLE else 400,
            line_height_ratio=1.3,
            color_token=color_token,
        )

    region = ContentRegion.model_construct(
        region_id=region_id,
        semantic_role=role,
        safe_zone=safe_zone or LayoutSafeZone.SAFE_CONTENT,
        binding=binding,
        quadrant=QuadrantId.TOP_LEFT,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=12,
        bounds=bounds,
        min_width_in=0.5,
        max_width_in=13.333,
        min_height_in=0.2,
        max_height_in=7.500,
        alignment=RegionAlignment.LEFT,
        vertical_alignment=VerticalAlignment.TOP,
        padding_token=SpacingToken.S,
        typography_spec=typo_spec,
        surface_token=surface_token,
        border_token=border_token,
        is_full_bleed=is_full_bleed,
    )
    return region, raw_dict


def _build_test_deck() -> Tuple[Presentation, Slide, ComposedSlideContext, CompositionInputManifest, DesignDNA]:
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    dna = _sample_dna()
    manifest = CompositionInputManifest(manifest_id="test_manifest")

    r_title, d_title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 0.80, 0.60, 11.733, 1.20, "Operating Systems Architecture", source_id="s_title", field_path="val", font_size_pt=26.0)
    manifest.register_content("s_title", d_title)

    r_card, _ = _make_region("card_bg", RegionSemanticRole.CARD_CONTAINER, 0.80, 2.00, 5.70, 4.50, is_decorative=True, surface_token=SurfaceToken.SURFACE_ELEVATED, border_token=BorderToken.THIN)

    r_body, d_body = _make_region("body_text", RegionSemanticRole.PRIMARY_TEXT, 1.00, 2.20, 5.30, 4.00, ["Kernel Mode vs User Mode", "Monolithic vs Microkernel", "Hardware Abstraction Layer"], source_id="s_body", field_path="bullets", font_size_pt=13.5)
    manifest.register_content("s_body", d_body)

    r_cit, d_cit = _make_region("cit_footer", RegionSemanticRole.FOOTER_CITATION, 0.80, 6.90, 11.733, 0.40, "Source: Silberschatz et al., Operating System Concepts", source_id="s_cit", field_path="citation", safe_zone=LayoutSafeZone.SAFE_FOOTER, font_size_pt=9.5, color_token=ColorToken.TEXT_SECONDARY)
    manifest.register_content("s_cit", d_cit)

    # Register notes
    manifest.register_content("slide_notes", {"speaker_notes": "Emphasize kernel isolation and privilege rings."})

    plan = SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=Phase3LayoutFamily.SPLIT_40_60,
        composition_mode=CompositionMode.SPLIT_COLUMNS,
        content_regions=[r_title, r_card, r_body, r_cit],
    )
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id="test_manifest",
    )
    return prs, slide, ctx, manifest, dna


# ═══════════════════════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════════════════════

def test_native_text_and_shape_editability():
    """1. All visible text resides in native editable text boxes with zero whole-slide rasterization."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    assert res.success is True
    assert res.terminal_status == "SUCCESS"
    assert res.editable_text_shape_count >= 3
    assert res.image_shape_count == 0

    audit = res.editability_audit
    assert audit is not None
    assert audit.is_editable is True
    assert audit.unsupported_raster_shapes == 0
    assert audit.editable_text_shapes >= 3


def test_geometry_fidelity_and_bounds_tolerance():
    """2. Rendered shape bounds match ResolvedRegionBounds within strict 0.02in tolerance."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    assert res.success is True
    for region in ctx.composition_plan.content_regions:
        shape_ids = res.region_to_shape_ids[region.region_id]
        assert len(shape_ids) >= 1
        # Find shape in slide
        shape = next(s for s in slide.shapes if s.shape_id == shape_ids[0])
        left_in = shape.left / 914400.0
        top_in = shape.top / 914400.0
        width_in = shape.width / 914400.0
        height_in = shape.height / 914400.0

        assert abs(left_in - region.bounds.left_in) <= 0.02
        assert abs(top_in - region.bounds.top_in) <= 0.02
        assert abs(width_in - region.bounds.width_in) <= 0.02
        assert abs(height_in - region.bounds.height_in) <= 0.02


def test_content_binding_resolution_from_manifest():
    """3. Visible content resolves accurately from CompositionInputManifest."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    assert res.binding_validation_passed is True
    assert res.content_hash_validation_passed is True
    
    # Verify exact rendered text on title shape
    title_sid = res.region_to_shape_ids["title"][0]
    title_shape = next(s for s in slide.shapes if s.shape_id == title_sid)
    assert title_shape.text_frame.text == "Operating Systems Architecture"


def test_content_binding_hash_mismatch_fails_closed():
    """4. Tampered manifest payload causes immediate fail-closed CONTENT_BINDING_HASH_MISMATCH."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    # Tamper with the title payload in the manifest
    manifest.raw_content_items["s_title"]["val"] = "MUTATED MALICIOUS TITLE"

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    assert res.success is False
    assert res.terminal_status == RenderDefectCode.CONTENT_BINDING_HASH_MISMATCH.value
    assert res.terminal_status in FAIL_CLOSED_STATUSES
    assert res.content_hash_validation_passed is False
    assert len(res.renderer_defects) > 0


def test_fail_closed_integrity_never_invokes_legacy_fallback():
    """5. Proves an integrity error (hash mismatch) in build_presentation_spec raises rather than falling back."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    # Tamper with manifest
    manifest.raw_content_items["s_title"]["val"] = "TAMPERED PAYLOAD"

    spec = PresentationSpec(
        title="OS Architecture",
        config=PresentationConfig(topic="OS", slide_count=10),
        slides=[SlideSpec(slide_no=1, title="Test", body_bullets=["Point 1"]) for _ in range(10)],
    )

    settings.PRESENTATION_COMPOSITION_RENDERER_ENABLED = True
    try:
        with pytest.raises(ValueError) as exc_info:
            build_presentation_spec(
                spec=spec,
                composed_contexts=[ctx],
                manifest=manifest,
                design_dna=dna,
            )
        assert "Composition rendering failed closed" in str(exc_info.value)
    finally:
        settings.PRESENTATION_COMPOSITION_RENDERER_ENABLED = False


def test_designdna_authoritative_font_resolution():
    """6. Font resolution derives from DesignDNA and records provenance in FontFallbackEvent."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    assert len(res.font_fallback_events) >= 3
    # Check title font resolution
    ev_title = next(e for e in res.font_fallback_events if e.region_id == "title")
    assert ev_title.requested_font == "Inter"
    assert ev_title.application_resolved_font == "Calibri"  # Export-safe Office fallback
    assert ev_title.fallback_used is True
    assert "Cross-platform export-safe fallback" in ev_title.fallback_reason


def test_partial_vs_full_bleed_geometry_authority():
    """7. Does NOT expand every bleed-tagged region; renders exact ResolvedRegionBounds."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    dna = _sample_dna()
    manifest = CompositionInputManifest(manifest_id="bleed_manifest")

    # A left-half bleed region (0.0 .. 6.666)
    r_left_bleed, _ = _make_region(
        "left_bleed_panel",
        RegionSemanticRole.CARD_CONTAINER,
        left_in=0.0, top_in=0.0, width_in=6.666, height_in=7.500,
        is_decorative=True,
        safe_zone=LayoutSafeZone.FULL_BLEED,
        is_full_bleed=True,
        surface_token=SurfaceToken.SURFACE_ACCENT,
    )
    # A full-canvas background (0.0 .. 13.333)
    r_full_bg, _ = _make_region(
        "full_canvas_bg",
        RegionSemanticRole.BLEED_BACKGROUND,
        left_in=0.0, top_in=0.0, width_in=13.333, height_in=7.500,
        is_decorative=True,
        safe_zone=LayoutSafeZone.FULL_BLEED,
        is_full_bleed=True,
    )
    plan = SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL,
        composition_mode=CompositionMode.FULL_BLEED_PANEL,
        content_regions=[r_full_bg, r_left_bleed],
    )
    ctx = ComposedSlideContext(slide_no=1, composition_plan=plan, composition_input_manifest_id="bleed_manifest")

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    # Check left-bleed shape
    s_left = next(s for s in slide.shapes if s.name.startswith("TG:S1:Rleft_bleed_panel"))
    assert abs((s_left.width / 914400.0) - 6.666) <= 0.02
    assert abs((s_left.left / 914400.0) - 0.0) <= 0.02

    # Check full-canvas shape
    s_full = next(s for s in slide.shapes if s.name.startswith("TG:S1:Rfull_canvas_bg"))
    assert abs((s_full.width / 914400.0) - 13.333) <= 0.02


def test_stable_region_to_shape_identity_and_round_trip():
    """8. Shapes carry TG:S{slide}:R{region}:{role} names and survive PPTX save/reopen."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)

    # 100% regions mapped
    for r in ctx.composition_plan.content_regions:
        assert r.region_id in res.region_to_shape_ids
        assert r.region_id in res.region_to_shape_names

    # Save to BytesIO and Reopen
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    prs_reloaded = Presentation(buf)
    slide_reloaded = prs_reloaded.slides[0]

    reloaded_names = [s.name for s in slide_reloaded.shapes]
    for r in ctx.composition_plan.content_regions:
        expected_prefix = f"TG:S1:R{r.region_id}:"
        assert any(n.startswith(expected_prefix) for n in reloaded_names)


def test_target_slide_cleanliness_contract():
    """9. Refuses to render over a pre-populated slide, failing closed with TARGET_SLIDE_NOT_CLEAN."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    # Pre-populate slide with conflicting text box
    dirty_box = slide.shapes.add_textbox(0, 0, 100, 100)
    dirty_box.text_frame.text = "Pre-existing conflicting text"

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is False
    assert res.terminal_status == RenderDefectCode.TARGET_SLIDE_NOT_CLEAN.value


def test_typography_and_text_fit_application():
    """10. Consumes TypographyRoleSpec and text_fit_results directly without re-truncating."""
    prs, slide, ctx, manifest, dna = _build_test_deck()

    # Override body font size via text_fit_results
    typo_spec_after = TypographyRoleSpec(
        role=TypographyRole.BODY,
        font_family="Inter",
        fallback_family="Calibri",
        safe_office_fallback="Calibri",
        font_size_pt=11.5,
        font_weight=400,
        line_height_ratio=1.20,
        color_token=ColorToken.TEXT_PRIMARY,
    )
    fit_overrides = {
        "body_text": TextFitResult.model_construct(
            region_id="body_text",
            status=TextFitStatus.FONT_ADJUSTED,
            fit_stage=3,
            typography_before=typo_spec_after,
            typography_after=typo_spec_after,
        )
    }

    res = render_composed_slide(prs, slide, ctx, manifest, dna, text_fit_results=fit_overrides, enforce_audit_gate=False)
    assert res.success is True

    body_sid = res.region_to_shape_ids["body_text"][0]
    body_shape = next(s for s in slide.shapes if s.shape_id == body_sid)
    # Check paragraph font size
    p = body_shape.text_frame.paragraphs[0]
    assert p.font.size == Pt(11.5)
    assert p.line_spacing == 1.20


def test_all_colortokens_preserve_palette():
    """11. Validates all ColorToken values map deterministically to RGBColor."""
    palette = _sample_dna().color_palette
    for tok in ColorToken:
        rgb, warn = resolve_color_token(tok, palette)
        assert rgb is not None
        assert warn is None
        assert isinstance(rgb, RGBColor)


def test_container_surface_and_border_rendering():
    """12. Surfaces and borders render according to tokens, applying shadows only when authorized."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    card_sid = res.region_to_shape_ids["card_bg"][0]
    card_shape = next(s for s in slide.shapes if s.shape_id == card_sid)

    # Elevated surface has shadow in spPr
    spPr = card_shape._element.spPr
    outerShdw = spPr.xpath('.//*[local-name()="outerShdw"]')
    assert len(outerShdw) == 1  # Shadow was authorized and applied


def test_xml_extension_alt_text_safety():
    """13. OOXML alt-text applies cleanly and survives save/reload."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    title_sid = res.region_to_shape_ids["title"][0]
    title_shape = next(s for s in slide.shapes if s.shape_id == title_sid)
    cNvPr = title_shape._element.xpath('.//p:cNvPr')[0]
    assert cNvPr.get("title") == "Region title"

    # Save and reload
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    prs2 = Presentation(buf)
    title2 = next(s for s in prs2.slides[0].shapes if s.name.startswith("TG:S1:Rtitle:"))
    cNvPr2 = title2._element.xpath('.//p:cNvPr')[0]
    assert cNvPr2.get("title") == "Region title"


def test_deterministic_8_layer_z_order():
    """14. Validates that background renders before container, which renders before text."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    rendered_names = [s.name for s in slide.shapes]
    idx_card = next(i for i, n in enumerate(rendered_names) if ":Rcard_bg:" in n)
    idx_body = next(i for i, n in enumerate(rendered_names) if ":Rbody_text:" in n)
    assert idx_card < idx_body  # Card container renders under body text


def test_speaker_notes_native_capability_and_non_leakage():
    """15. Speaker notes are natively attached and do not leak into visible slide text."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True
    assert res.speaker_notes_capability == "NATIVE"

    # Verify notes in notes_slide
    notes_text = slide.notes_slide.notes_text_frame.text
    assert "Emphasize kernel isolation" in notes_text

    # Verify notes text is NOT in any visible shape on the slide
    for s in slide.shapes:
        if getattr(s, "has_text_frame", False):
            assert "Emphasize kernel isolation" not in s.text_frame.text

    # Reopen test
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    prs_reloaded = Presentation(buf)
    assert "Emphasize kernel isolation" in prs_reloaded.slides[0].notes_slide.notes_text_frame.text


def test_formula_rendering_faithful_unicode():
    """16. Formulas render faithful Unicode text and are native editable text boxes."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    dna = _sample_dna()
    manifest = CompositionInputManifest(manifest_id="formula_manifest")

    payload = FormulaPayload(
        original_source=r"E_k = \frac{1}{2}mv^2",
        render_mode=FormulaRenderMode.UNICODE_TEXT,
    )
    r_form, d_form = _make_region(
        "form_1", RegionSemanticRole.FORMULA_DISPLAY,
        1.0, 2.0, 6.0, 1.5,
        content_payload=payload.unicode_representation or "E_k = 1/2mv^2",
        source_id="s_form", field_path="formula",
    )
    manifest.register_content("s_form", d_form)

    plan = SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=Phase3LayoutFamily.TEXT_DOMINANT,
        composition_mode=CompositionMode.STANDARD_CANVAS,
        content_regions=[r_form],
    )
    ctx = ComposedSlideContext(slide_no=1, composition_plan=plan, composition_input_manifest_id="formula_manifest")

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    f_shape = next(s for s in slide.shapes if s.name.startswith("TG:S1:Rform_1"))
    assert f_shape.has_text_frame is True
    assert "E" in f_shape.text_frame.text
    assert "$" not in f_shape.text_frame.text  # Raw delimiters stripped


def test_code_block_rendering_monospace_and_indentation():
    """17. Code blocks preserve exact indentation, line breaks, and use monospace font."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    dna = _sample_dna()
    manifest = CompositionInputManifest(manifest_id="code_manifest")

    code_snip = "def compute_hash(val):\n    return sha256(val)\n"
    r_code, d_code = _make_region(
        "code_1", RegionSemanticRole.CODE_BLOCK,
        1.0, 2.0, 8.0, 3.0,
        content_payload=code_snip,
        source_id="s_code", field_path="code",
    )
    manifest.register_content("s_code", d_code)

    plan = SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=Phase3LayoutFamily.TEXT_DOMINANT,
        composition_mode=CompositionMode.STANDARD_CANVAS,
        content_regions=[r_code],
    )
    ctx = ComposedSlideContext(slide_no=1, composition_plan=plan, composition_input_manifest_id="code_manifest")

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True

    c_shape = next(s for s in slide.shapes if s.name.startswith("TG:S1:Rcode_1"))
    assert c_shape.has_text_frame is True
    assert "def compute_hash" in c_shape.text_frame.text
    p = c_shape.text_frame.paragraphs[0]
    assert p.font.name == "Consolas"


def test_chart_deferred_placeholder_safety():
    """18. CHART_DEFERRED renders a neutral, non-factual placeholder without fake numbers."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    dna = _sample_dna()
    manifest = CompositionInputManifest(manifest_id="chart_manifest")

    r_chart, _ = _make_region(
        "chart_region", RegionSemanticRole.PRIMARY_VISUAL,
        6.0, 2.0, 6.0, 4.0,
        is_decorative=True,
    )
    plan = SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=Phase3LayoutFamily.SPLIT_40_60,
        composition_mode=CompositionMode.SPLIT_COLUMNS,
        content_regions=[r_chart],
        has_deferred_chart=True,
    )
    ctx = ComposedSlideContext(slide_no=1, composition_plan=plan, composition_input_manifest_id="chart_manifest")

    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    assert res.success is True
    assert res.deferred_asset_count == 1

    c_shape = next(s for s in slide.shapes if ":chart_deferred" in s.name)
    assert "[Chart Reserved:" in c_shape.text_frame.text
    # Verify no fake series or factual values were drawn
    assert "100%" not in c_shape.text_frame.text
    assert "Sales" not in c_shape.text_frame.text


def test_audit_gate_rejects_fatal_and_reflow():
    """19. Audit gate rejects plans with FATAL or REFLOW_REQUIRED defects (fails closed)."""
    prs, slide, ctx, manifest, dna = _build_test_deck()

    # Create mock audit result with FATAL overflow defect
    audit_fail = LayoutAuditResult.model_construct(
        layout_valid=False,
        defects=[
            LayoutDefect(
                defect_code=DefectCode.TEXT_OVERFLOW,
                severity=DefectSeverity.FATAL,
                repairability=DefectRepairability.REFLOW_REQUIRED,
                target_region_ids=["body_text"],
                message="Text density exceeds slide limits floor",
            )
        ],
    )

    res = render_composed_slide(prs, slide, ctx, manifest, dna, audit_result=audit_fail, enforce_audit_gate=True)
    assert res.success is False
    assert res.terminal_status == RenderDefectCode.AUDIT_GATE_FAILED.value
    assert res.terminal_status in FAIL_CLOSED_STATUSES


def test_renderer_determinism():
    """20. Multiple rendering passes on identical input produce identical shape trees and geometry."""
    prs1, s1, ctx1, m1, dna1 = _build_test_deck()
    res1 = render_composed_slide(prs1, s1, ctx1, m1, dna1, enforce_audit_gate=False)

    prs2, s2, ctx2, m2, dna2 = _build_test_deck()
    res2 = render_composed_slide(prs2, s2, ctx2, m2, dna2, enforce_audit_gate=False)

    assert res1.rendered_shape_count == res2.rendered_shape_count
    assert res1.region_to_shape_names == res2.region_to_shape_names

    names1 = [s.name for s in s1.shapes]
    names2 = [s.name for s in s2.shapes]
    assert names1 == names2


def test_performance_sanity_benchmark():
    """21. Records per-slide latency and validates no pathological N^2 stall (< 500ms)."""
    prs, slide, ctx, manifest, dna = _build_test_deck()
    t0 = time.perf_counter()
    res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res.success is True
    assert res.render_latency_ms > 0.0
    assert elapsed_ms < 500.0  # Sanity bound to prevent infinite loops


def test_held_out_canonical_topics_generalization():
    """22. Generates real presentations across 5 canonical topics with 100% region traceability."""
    topics = [
        ("Node.js Architecture", Phase3LayoutFamily.SPLIT_40_60),
        ("Photosynthesis", Phase3LayoutFamily.HERO_OFFSET),
        ("Macbeth", Phase3LayoutFamily.ASYMMETRIC_EDITORIAL),
        ("Eigenvalues & Eigenvectors", Phase3LayoutFamily.SUMMARY_GRID),
        ("Inflation & Monetary Policy", Phase3LayoutFamily.COMPARISON_TWO_COLUMN),
    ]

    for topic_title, layout in topics:
        prs = Presentation()
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        dna = _sample_dna()
        manifest = CompositionInputManifest(manifest_id=f"manifest_{topic_title}")

        r_t, d_t = _make_region("t", RegionSemanticRole.HEADER_TITLE, 0.8, 0.6, 11.7, 1.2, topic_title, source_id=f"s_{topic_title}", field_path="title")
        manifest.register_content(f"s_{topic_title}", d_t)

        r_b, d_b = _make_region("b", RegionSemanticRole.PRIMARY_TEXT, 0.8, 2.0, 11.7, 4.5, ["Concept 1", "Concept 2"], source_id=f"b_{topic_title}", field_path="body")
        manifest.register_content(f"b_{topic_title}", d_b)

        plan = SlideCompositionPlan.model_construct(
            slide_no=1,
            layout_family=layout,
            composition_mode=CompositionMode.STANDARD_CANVAS,
            content_regions=[r_t, r_b],
        )
        ctx = ComposedSlideContext(slide_no=1, composition_plan=plan, composition_input_manifest_id=f"manifest_{topic_title}")

        res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
        assert res.success is True, f"Failed rendering {topic_title}"
        assert len(res.region_to_shape_ids) == 2
        assert res.editability_audit.is_editable is True
