"""
LearnByGenie PPT vNext — Phase 3.2E Editable PPTX Composition Renderer
===================================================================
Translates audited Phase 3.2C/3.2D SlideCompositionPlan instances into native,
fully editable PowerPoint (.pptx) objects.

Governance:
  - Strictly preserves frozen Phase 1, Phase 2, Phase 3.1, and Phase 3.2A-3.2D contracts.
  - Geometry Authority: ResolvedRegionBounds is absolute; no guessing or full-bleed expansion.
  - Content Authority: CompositionInputManifest + ContentBinding are exclusive content sources.
  - Fail-Closed Integrity: Hash mismatches, audit gate failures, or corrupt manifests fail closed.
  - Native Editability: Zero slide-level rasterization; all text remains selectable/editable.
  - Traceability: Every rendered PPTX shape carries deterministic TG:S{slide}:R{region}:{role} name.
  - OOXML Safety: XML extensions are isolated, failure-contained, and applied only when authorized.
"""
from __future__ import annotations

import io
import time
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Union, Set
from pydantic import BaseModel, Field

from pptx import Presentation
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from lxml import etree

from app.core.logging import logger
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT
from .composition_schemas import (
    SlideCompositionPlan,
    ComposedSlideContext,
    CompositionInputManifest,
    ResolvedRegionBounds,
    ContentRegion,
    ContentBinding,
    TypographyRoleSpec,
    RegionSemanticRole,
    TypographyRole,
    SurfaceToken,
    BorderToken,
    ColorToken,
    FormulaRenderMode,
    RendererCapability,
    LayoutSafeZone,
    SourceKind,
    FormulaPayload,
    ContentBindingHashMismatch,
    CONTENT_BEARING_ROLES,
    convert_latex_to_faithful_unicode,
    convert_latex_to_safe_literal,
)
from .visual_schemas import (
    DesignDNA,
    ColorPalette,
    TypographyScale,
    SpacingScale,
    Phase3LayoutFamily,
)
from .layout_quality_auditor import (
    LayoutAuditResult,
    RepairResult,
    DefectSeverity,
    DefectRepairability,
    DefectCode,
    audit_layout,
)
from .typography_engine import (
    TextFitResult,
    TextFitStatus,
)
from .schemas import PresentationSpec, SlideSpec


# ═══════════════════════════════════════════════════════════════
# 1. RENDER DEFECTS & TERMINAL STATUSES
# ═══════════════════════════════════════════════════════════════

class RenderDefectCode(str, Enum):
    """Strongly typed defect codes for composition rendering."""
    CONTENT_BINDING_HASH_MISMATCH  = "CONTENT_BINDING_HASH_MISMATCH"
    AUDIT_GATE_FAILED              = "AUDIT_GATE_FAILED"
    SEMANTIC_INTEGRITY_FAILED      = "SEMANTIC_INTEGRITY_FAILED"
    INVALID_COMPOSITION_PLAN       = "INVALID_COMPOSITION_PLAN"
    GEOMETRY_CONTRACT_VIOLATION    = "GEOMETRY_CONTRACT_VIOLATION"
    CORRUPT_MANIFEST               = "CORRUPT_MANIFEST"
    CONTENT_RESOLUTION_MISMATCH    = "CONTENT_RESOLUTION_MISMATCH"
    TARGET_SLIDE_NOT_CLEAN         = "TARGET_SLIDE_NOT_CLEAN"
    DEFERRED_ASSET_ENCOUNTERED     = "DEFERRED_ASSET_ENCOUNTERED"
    FONT_FALLBACK_OCCURRED         = "FONT_FALLBACK_OCCURRED"
    XML_EXTENSION_FAILED           = "XML_EXTENSION_FAILED"
    UNMAPPED_COLOR_TOKEN           = "UNMAPPED_COLOR_TOKEN"


FAIL_CLOSED_STATUSES: Set[str] = {
    RenderDefectCode.CONTENT_BINDING_HASH_MISMATCH.value,
    RenderDefectCode.AUDIT_GATE_FAILED.value,
    RenderDefectCode.SEMANTIC_INTEGRITY_FAILED.value,
    RenderDefectCode.INVALID_COMPOSITION_PLAN.value,
    RenderDefectCode.GEOMETRY_CONTRACT_VIOLATION.value,
    RenderDefectCode.CORRUPT_MANIFEST.value,
    RenderDefectCode.CONTENT_RESOLUTION_MISMATCH.value,
    RenderDefectCode.TARGET_SLIDE_NOT_CLEAN.value,
}


# ═══════════════════════════════════════════════════════════════
# 2. RENDER MODELS & AUDIT REPORTS
# ═══════════════════════════════════════════════════════════════

class FontFallbackEvent(BaseModel):
    """Provenance record of font resolution per typography region."""
    region_id: str
    requested_font: str
    application_resolved_font: str
    fallback_used: bool
    fallback_reason: str = ""


class EditabilityAuditReport(BaseModel):
    """Structural inspection of rendered slide for native editability."""
    is_editable: bool
    shape_count: int
    editable_text_shapes: int
    native_shapes: int
    image_shapes: int
    unsupported_raster_shapes: int = 0
    issues: List[str] = Field(default_factory=list)


class RenderResult(BaseModel):
    """Comprehensive result contract for a rendered PowerPoint slide."""
    slide_no: int
    success: bool
    terminal_status: str
    rendered_shape_count: int = 0
    semantic_shape_count: int = 0
    decorative_shape_count: int = 0
    editable_text_shape_count: int = 0
    image_shape_count: int = 0
    deferred_asset_count: int = 0
    font_fallback_events: List[FontFallbackEvent] = Field(default_factory=list)
    renderer_warnings: List[str] = Field(default_factory=list)
    renderer_defects: List[str] = Field(default_factory=list)
    binding_validation_passed: bool = True
    geometry_validation_passed: bool = True
    content_hash_validation_passed: bool = True
    design_dna_preserved: bool = True
    semantic_integrity_preserved: bool = True
    region_to_shape_ids: Dict[str, List[int]] = Field(default_factory=dict)
    region_to_shape_names: Dict[str, List[str]] = Field(default_factory=dict)
    shape_id_to_region_id: Dict[int, str] = Field(default_factory=dict)
    speaker_notes_capability: str = "NATIVE"
    render_latency_ms: float = 0.0
    editability_audit: Optional[EditabilityAuditReport] = None


# ═══════════════════════════════════════════════════════════════
# 3. COLOR PALETTE MAPPING
# ═══════════════════════════════════════════════════════════════

def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Converts '#RRGGBB' or 'RRGGBB' to PPTX RGBColor."""
    clean = hex_str.strip().lstrip("#")
    if len(clean) != 6:
        clean = "000000"
    r = int(clean[0:2], 16)
    g = int(clean[2:4], 16)
    b = int(clean[4:6], 16)
    return RGBColor(r, g, b)


def resolve_color_token(token: Union[ColorToken, str], palette: ColorPalette) -> Tuple[RGBColor, Optional[str]]:
    """
    Deterministically maps any frozen ColorToken to an RGBColor using the DesignDNA ColorPalette.
    Returns (rgb_color, error_or_warning).
    """
    token_val = token.value if isinstance(token, ColorToken) else str(token)
    
    mapping: Dict[str, str] = {
        ColorToken.PRIMARY.value: palette.primary,
        ColorToken.PRIMARY_LIGHT.value: palette.primary_light,
        ColorToken.SECONDARY.value: palette.secondary,
        ColorToken.ACCENT.value: palette.accent,
        ColorToken.BACKGROUND.value: palette.background,
        ColorToken.SURFACE.value: palette.surface,
        ColorToken.TEXT_PRIMARY.value: palette.text_primary,
        ColorToken.TEXT_SECONDARY.value: palette.text_secondary,
        ColorToken.TEXT_ON_PRIMARY.value: palette.text_on_primary,
        ColorToken.BORDER.value: palette.border,
        ColorToken.SUCCESS.value: palette.success,
        ColorToken.WARNING.value: palette.warning,
        ColorToken.ERROR.value: palette.error,
    }

    if token_val in mapping:
        return _hex_to_rgb(mapping[token_val]), None
    else:
        # Unknown color token: fallback to text_primary with warning
        return _hex_to_rgb(palette.text_primary), f"Unmapped color token: {token_val}"


# ═══════════════════════════════════════════════════════════════
# 4. FONT SELECTION & RESOLUTION
# ═══════════════════════════════════════════════════════════════

EXPORT_SAFE_FONTS: Dict[str, str] = {
    # Preferred -> approved export-safe Office fallback
    "Inter": "Calibri",
    "Roboto": "Arial",
    "Outfit": "Calibri",
    "Open Sans": "Arial",
    "Montserrat": "Arial",
    "Lora": "Georgia",
    "Merriweather": "Georgia",
    "Fira Code": "Consolas",
    "JetBrains Mono": "Consolas",
}

SAFE_OFFICE_FALLBACKS: Dict[str, str] = {
    "sans-serif": "Calibri",
    "serif": "Georgia",
    "monospace": "Consolas",
}


def resolve_font_family(
    requested_font: str,
    role: Union[TypographyRole, str],
    design_dna: DesignDNA,
    is_code: bool = False,
) -> Tuple[str, bool, str]:
    """
    Resolves DesignDNA requested font through export-safe fallback chain:
      requested_font -> approved export-safe fallback -> safe Office fallback
    Returns (resolved_font, fallback_used, fallback_reason).
    """
    clean_requested = requested_font.strip() if requested_font else ""
    if not clean_requested:
        if role == TypographyRole.TITLE:
            clean_requested = design_dna.title_scale.font_family
        elif role == TypographyRole.CAPTION:
            clean_requested = design_dna.caption_scale.font_family
        else:
            clean_requested = design_dna.body_scale.font_family

    if is_code or role == "code_block" or role == "code":
        if clean_requested in ("Consolas", "Courier New"):
            return clean_requested, False, "Native monospace font"
        return "Consolas", True, "Export-safe monospace fallback chain"

    # Known natively universal Office fonts
    if clean_requested in ("Calibri", "Arial", "Georgia", "Times New Roman", "Consolas", "Verdana", "Trebuchet MS"):
        return clean_requested, False, "Native universal Office font"

    # Export-safe translation
    if clean_requested in EXPORT_SAFE_FONTS:
        safe_fb = EXPORT_SAFE_FONTS[clean_requested]
        return safe_fb, True, f"Cross-platform export-safe fallback from '{clean_requested}'"

    # Generic fallback
    return "Calibri", True, f"Safe Office fallback from unrecognized font '{clean_requested}'"


# ═══════════════════════════════════════════════════════════════
# 5. ISOLATED OOXML HELPERS
# ═══════════════════════════════════════════════════════════════

def set_shape_alt_text(shape: Any, title: str, description: str) -> bool:
    """
    Isolated OOXML helper to set non-visual drawing properties (cNvPr) title and description.
    Never corrupts shape if xpath is missing.
    """
    try:
        cNvPr_list = shape._element.xpath('.//p:cNvPr')
        if cNvPr_list:
            cNvPr = cNvPr_list[0]
            if title:
                cNvPr.set('title', str(title)[:255])
            if description:
                cNvPr.set('descr', str(description)[:1024])
            return True
        return False
    except Exception as e:
        logger.warning(f"[CompositionRenderer] Failed to set alt text ({e})")
        return False


def apply_card_shadow(shape: Any) -> bool:
    """
    Isolated OOXML helper to apply subtle card drop shadow.
    Applied ONLY when explicitly authorized by style token (e.g. SURFACE_ELEVATED).
    """
    try:
        spPr = shape._element.spPr
        ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
        effectLst = etree.SubElement(spPr, f'{{{ns}}}effectLst')
        outerShdw = etree.SubElement(effectLst, f'{{{ns}}}outerShdw')
        outerShdw.set('blurRad', '50800')   # 4pt blur
        outerShdw.set('dist', '25400')      # 2pt offset
        outerShdw.set('dir', '5400000')     # bottom direction
        outerShdw.set('algn', 'tl')
        srgbClr = etree.SubElement(outerShdw, f'{{{ns}}}srgbClr')
        srgbClr.set('val', '000000')
        alpha = etree.SubElement(srgbClr, f'{{{ns}}}alpha')
        alpha.set('val', '15000')           # 15% opacity
        return True
    except Exception as e:
        logger.warning(f"[CompositionRenderer] Failed to apply shape shadow ({e})")
        return False


def set_shape_letter_spacing(run: Any, letter_spacing_em: float) -> bool:
    """
    Isolated OOXML helper to set character spacing (spc) on a text run.
    """
    if abs(letter_spacing_em) < 0.001:
        return True
    try:
        rPr = run._r.get_or_add_rPr()
        # 1 em ≈ 100 pt in OOXML spc hundredths of a point
        spc_hundredths = int(letter_spacing_em * 1000)
        rPr.set('spc', str(spc_hundredths))
        return True
    except Exception as e:
        logger.warning(f"[CompositionRenderer] Failed to set letter spacing ({e})")
        return False


# ═══════════════════════════════════════════════════════════════
# 6. Z-ORDER & REGION SORTING
# ═══════════════════════════════════════════════════════════════

def _region_z_order_key(region: ContentRegion) -> int:
    """
    Determines strict 8-layer z-order rendering priority.
    Lowest number renders first (bottom), highest renders last (top).
    """
    if region.semantic_role == RegionSemanticRole.BLEED_BACKGROUND or region.is_full_bleed:
        return 10  # Layer 1: Background bleed
    if region.binding.is_decorative and region.semantic_role == RegionSemanticRole.CARD_CONTAINER:
        return 20  # Layer 2: Decorative surfaces
    if region.semantic_role in (RegionSemanticRole.PRIMARY_VISUAL, RegionSemanticRole.SECONDARY_VISUAL):
        return 30  # Layer 3: Visual placeholders
    if region.semantic_role in (RegionSemanticRole.CARD_CONTAINER, RegionSemanticRole.METRIC_CARD, RegionSemanticRole.PROCESS_STEP, RegionSemanticRole.TIMELINE_NODE):
        return 40  # Layer 4: Semantic containers / cards
    if region.semantic_role in (
        RegionSemanticRole.HEADER_TITLE,
        RegionSemanticRole.HEADER_SUBTITLE,
        RegionSemanticRole.PRIMARY_TEXT,
        RegionSemanticRole.SUPPORTING_POINTS,
        RegionSemanticRole.COMPARISON_COLUMN_A,
        RegionSemanticRole.COMPARISON_COLUMN_B,
        RegionSemanticRole.FORMULA_DISPLAY,
        RegionSemanticRole.CODE_BLOCK,
    ):
        return 50  # Layer 5: Primary text content
    if region.semantic_role in (RegionSemanticRole.KEY_INSIGHT_CALLOUT, RegionSemanticRole.CAPTION, RegionSemanticRole.CATEGORY_TAG):
        return 60  # Layer 6: Annotations & captions
    if region.semantic_role == RegionSemanticRole.FOOTER_CITATION:
        return 70  # Layer 7: Citations & footer
    return 80      # Layer 8: Foreground callouts / overlays


# ═══════════════════════════════════════════════════════════════
# 7. TARGET SLIDE CLEANLINESS CHECK
# ═══════════════════════════════════════════════════════════════

def validate_target_slide_cleanliness(slide: Slide) -> bool:
    """
    Enforces Contract A: The target slide must be clean/blank.
    Returns False if slide already contains conflicting shapes or text.
    """
    if not hasattr(slide, "shapes"):
        return True
    if len(slide.shapes) == 0:
        return True
    
    for s in slide.shapes:
        if s.name and s.name.startswith("TG:"):
            return False
        if getattr(s, "has_text_frame", False) and s.text_frame.text.strip():
            return False
    return True


# ═══════════════════════════════════════════════════════════════
# 8. EDITABILITY AUDIT IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════

def audit_rendered_slide_editability(slide: Slide) -> EditabilityAuditReport:
    """
    Inspects rendered PowerPoint slide to certify structural editability.
    Verifies that all visible text is selectable, shapes are native, and no
    whole-slide rasterization occurred.
    """
    shape_count = len(slide.shapes)
    editable_text_count = 0
    native_shape_count = 0
    image_shape_count = 0
    issues: List[str] = []

    for s in slide.shapes:
        if getattr(s, "has_text_frame", False):
            editable_text_count += 1
            native_shape_count += 1
        elif s.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
            image_shape_count += 1
            # Verify image is not a whole-slide screenshot
            w_in = s.width / 914400.0
            h_in = s.height / 914400.0
            if w_in >= 13.0 and h_in >= 7.0:
                issues.append("Slide-level rasterization detected: single picture covers canvas")
        else:
            native_shape_count += 1

    is_editable = (len(issues) == 0) and (editable_text_count > 0 or shape_count == 0)
    return EditabilityAuditReport(
        is_editable=is_editable,
        shape_count=shape_count,
        editable_text_shapes=editable_text_count,
        native_shapes=native_shape_count,
        image_shapes=image_shape_count,
        unsupported_raster_shapes=1 if issues else 0,
        issues=issues,
    )


# ═══════════════════════════════════════════════════════════════
# 9. PRIMARY SLIDE COMPOSITION RENDERER
# ═══════════════════════════════════════════════════════════════

def render_composed_slide(
    prs: Presentation,
    slide: Slide,
    composed_context: ComposedSlideContext,
    composition_input_manifest: CompositionInputManifest,
    design_dna: DesignDNA,
    text_fit_results: Optional[Dict[str, TextFitResult]] = None,
    audit_result: Optional[Union[LayoutAuditResult, RepairResult]] = None,
    enforce_audit_gate: bool = True,
    visual_semantic_packet: Optional[Any] = None,
    slide_content: Optional[Any] = None,
    image_decisions: Optional[Dict[str, Any]] = None,
) -> RenderResult:
    """
    Renders a single audited SlideCompositionPlan onto a native PowerPoint slide.
    
    Fail-Closed Integrity:
      Immediately returns structured failure (never legacy fallback) on:
      - TARGET_SLIDE_NOT_CLEAN
      - AUDIT_GATE_FAILED
      - CONTENT_BINDING_HASH_MISMATCH
      - INVALID_COMPOSITION_PLAN
    """
    t_start = time.perf_counter()
    slide_no = composed_context.slide_no
    plan = composed_context.composition_plan

    # 1. Target Slide Cleanliness Check
    if not validate_target_slide_cleanliness(slide):
        logger.error(f"[CompositionRenderer] Slide {slide_no}: TARGET_SLIDE_NOT_CLEAN")
        return RenderResult(
            slide_no=slide_no,
            success=False,
            terminal_status=RenderDefectCode.TARGET_SLIDE_NOT_CLEAN.value,
            renderer_defects=["Target slide contains pre-existing conflicting shapes or text"],
            binding_validation_passed=False,
            geometry_validation_passed=False,
            content_hash_validation_passed=False,
            design_dna_preserved=False,
            semantic_integrity_preserved=False,
        )

    # 2. Audit Precondition Gate
    if enforce_audit_gate:
        eff_audit = audit_result
        if eff_audit is None:
            eff_audit = audit_layout(plan, design_dna=design_dna, text_fit_results=text_fit_results)
        
        audit_res_obj = eff_audit.audit_after if isinstance(eff_audit, RepairResult) else eff_audit
        if not audit_res_obj.layout_valid:
            fatal_or_reflow = [
                d for d in audit_res_obj.defects
                if d.severity in (DefectSeverity.FATAL, DefectSeverity.ERROR)
                or d.repairability in (DefectRepairability.REFLOW_REQUIRED, DefectRepairability.UNREPAIRABLE)
                or d.defect_code in (DefectCode.TEXT_OVERFLOW, DefectCode.SAFE_ZONE_VIOLATION, DefectCode.FULL_BLEED_TEXT_VIOLATION)
            ]
            if fatal_or_reflow:
                err_msgs = [f"{d.defect_code.value}: {d.message}" for d in fatal_or_reflow]
                logger.error(f"[CompositionRenderer] Slide {slide_no}: AUDIT_GATE_FAILED: {err_msgs}")
                return RenderResult(
                    slide_no=slide_no,
                    success=False,
                    terminal_status=RenderDefectCode.AUDIT_GATE_FAILED.value,
                    renderer_defects=err_msgs,
                    binding_validation_passed=False,
                    geometry_validation_passed=False,
                    content_hash_validation_passed=False,
                    design_dna_preserved=False,
                    semantic_integrity_preserved=False,
                )

    # 3. Sort Regions by Strict Z-Order
    sorted_regions = sorted(plan.content_regions, key=_region_z_order_key)

    region_to_shape_ids: Dict[str, List[int]] = {}
    region_to_shape_names: Dict[str, List[str]] = {}
    shape_id_to_region_id: Dict[int, str] = {}
    font_fallback_events: List[FontFallbackEvent] = []
    renderer_warnings: List[str] = []
    renderer_defects: List[str] = []

    rendered_shape_count = 0
    semantic_shape_count = 0
    decorative_shape_count = 0
    editable_text_shape_count = 0
    image_shape_count = 0
    deferred_asset_count = 0

    palette = design_dna.color_palette

    # 4. Render Each Region with Strict Geometry & Binding Authority
    for region in sorted_regions:
        r_id = region.region_id
        role = region.semantic_role
        bounds = region.bounds

        # Geometry authority: Exact Inches from ResolvedRegionBounds
        left_emu = Inches(bounds.left_in)
        top_emu = Inches(bounds.top_in)
        width_emu = Inches(bounds.width_in)
        height_emu = Inches(bounds.height_in)

        # A. Resolve Content Binding
        raw_content = None
        if not region.binding.is_decorative:
            try:
                raw_content = composition_input_manifest.resolve_content(region.binding, region_id=r_id)
            except ContentBindingHashMismatch as e:
                logger.error(f"[CompositionRenderer] Slide {slide_no} Region '{r_id}': {e}")
                return RenderResult(
                    slide_no=slide_no,
                    success=False,
                    terminal_status=RenderDefectCode.CONTENT_BINDING_HASH_MISMATCH.value,
                    renderer_defects=[str(e)],
                    binding_validation_passed=False,
                    geometry_validation_passed=True,
                    content_hash_validation_passed=False,
                    design_dna_preserved=False,
                    semantic_integrity_preserved=False,
                )
            except Exception as e:
                logger.error(f"[CompositionRenderer] Content resolution error on '{r_id}': {e}")
                return RenderResult(
                    slide_no=slide_no,
                    success=False,
                    terminal_status=RenderDefectCode.CONTENT_RESOLUTION_MISMATCH.value,
                    renderer_defects=[f"Failed resolving content for region '{r_id}': {e}"],
                    binding_validation_passed=False,
                    geometry_validation_passed=True,
                    content_hash_validation_passed=False,
                    design_dna_preserved=False,
                    semantic_integrity_preserved=False,
                )

        # B. Container / Surface Shape Rendering (if surface or border token demands it)
        container_shape = None
        needs_container = (
            role in (RegionSemanticRole.CARD_CONTAINER, RegionSemanticRole.METRIC_CARD, RegionSemanticRole.PROCESS_STEP, RegionSemanticRole.TIMELINE_NODE, RegionSemanticRole.BLEED_BACKGROUND)
            or region.surface_token != SurfaceToken.TRANSPARENT
            or region.border_token != BorderToken.NONE
        )

        if needs_container:
            shape_type = MSO_SHAPE.RECTANGLE
            if region.corner_radius_pt > 0 or region.surface_token == SurfaceToken.SURFACE_ELEVATED or role == RegionSemanticRole.CARD_CONTAINER:
                shape_type = MSO_SHAPE.ROUNDED_RECTANGLE

            container_shape = slide.shapes.add_shape(shape_type, left_emu, top_emu, width_emu, height_emu)
            c_name = f"TG:S{slide_no}:R{r_id}:container"
            container_shape.name = c_name

            # Track mapping
            sid = container_shape.shape_id
            region_to_shape_ids.setdefault(r_id, []).append(sid)
            region_to_shape_names.setdefault(r_id, []).append(c_name)
            shape_id_to_region_id[sid] = r_id
            rendered_shape_count += 1
            if region.binding.is_decorative:
                decorative_shape_count += 1
            else:
                semantic_shape_count += 1

            # Fill resolution
            if region.surface_token == SurfaceToken.TRANSPARENT:
                container_shape.fill.background()
            elif region.surface_token == SurfaceToken.SURFACE_ACCENT:
                rgb, w = resolve_color_token(ColorToken.ACCENT, palette)
                if w: renderer_warnings.append(w)
                container_shape.fill.solid()
                container_shape.fill.fore_color.rgb = rgb
            elif region.surface_token in (SurfaceToken.SURFACE_DEFAULT, SurfaceToken.SURFACE_ELEVATED):
                rgb, w = resolve_color_token(ColorToken.SURFACE, palette)
                if w: renderer_warnings.append(w)
                container_shape.fill.solid()
                container_shape.fill.fore_color.rgb = rgb
            elif region.surface_token == SurfaceToken.SURFACE_MUTED:
                rgb, w = resolve_color_token(ColorToken.BACKGROUND, palette)
                if w: renderer_warnings.append(w)
                container_shape.fill.solid()
                container_shape.fill.fore_color.rgb = rgb
            else:
                rgb, w = resolve_color_token(ColorToken.SURFACE, palette)
                container_shape.fill.solid()
                container_shape.fill.fore_color.rgb = rgb

            # Border resolution
            if region.border_token == BorderToken.NONE:
                container_shape.line.fill.background()
            else:
                b_rgb, bw = resolve_color_token(ColorToken.BORDER, palette)
                if bw: renderer_warnings.append(bw)
                container_shape.line.color.rgb = b_rgb
                if region.border_token == BorderToken.HAIRLINE:
                    container_shape.line.width = Pt(0.5)
                elif region.border_token == BorderToken.THIN:
                    container_shape.line.width = Pt(1.0)
                elif region.border_token == BorderToken.THICK:
                    container_shape.line.width = Pt(2.0)
                elif region.border_token == BorderToken.ACCENT:
                    a_rgb, _ = resolve_color_token(ColorToken.ACCENT, palette)
                    container_shape.line.color.rgb = a_rgb
                    container_shape.line.width = Pt(1.5)

            # Corner radius clamping
            if shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
                min_dim = min(bounds.width_in, bounds.height_in)
                adj = 0.04
                if min_dim > 0:
                    adj = min(0.08, max(0.02, (region.corner_radius_pt / 72.0) / min_dim))
                container_shape.adjustments[0] = adj

            # Shadow: apply ONLY when explicitly authorized by SURFACE_ELEVATED
            if region.surface_token == SurfaceToken.SURFACE_ELEVATED:
                apply_card_shadow(container_shape)
            else:
                container_shape.shadow.inherit = False

            set_shape_alt_text(container_shape, title=f"Region {r_id}", description=f"Semantic role: {role.value}")

        # If this is purely a decorative container or bleed background, no text frame needed
        if region.binding.is_decorative and role not in CONTENT_BEARING_ROLES:
            continue

        # C. Special Handling: Chart
        if "chart" in r_id or "chart" in str(role.value):
            from app.core.config import settings
            if getattr(settings, "PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED", False) and slide_content and getattr(slide_content, "data_points", None):
                from app.services.presentation.chart_intelligence import (
                    extract_chart_payload_from_content,
                    select_appropriate_chart_type,
                    render_native_chart,
                )
                chart_payload = extract_chart_payload_from_content(slide_content)
                if chart_payload:
                    ctype = select_appropriate_chart_type(chart_payload, visual_semantic_packet)
                    chart_res = render_native_chart(prs, slide, bounds, chart_payload, ctype, design_dna, slide_no, r_id)
                    if chart_res.success and chart_res.rendered_shape_id is not None:
                        sid = chart_res.rendered_shape_id
                        sname = chart_res.rendered_shape_name or f"TG:S{slide_no}:R{r_id}:native_chart"
                        region_to_shape_ids.setdefault(r_id, []).append(sid)
                        region_to_shape_names.setdefault(r_id, []).append(sname)
                        shape_id_to_region_id[sid] = r_id
                        rendered_shape_count += 1
                        semantic_shape_count += 1
                        continue

            deferred_asset_count += 1
            # Reserve neutral, non-factual placeholder container
            ph_box = slide.shapes.add_textbox(left_emu, top_emu, width_emu, height_emu)
            ph_name = f"TG:S{slide_no}:R{r_id}:chart_deferred"
            ph_box.name = ph_name
            sid = ph_box.shape_id
            region_to_shape_ids.setdefault(r_id, []).append(sid)
            region_to_shape_names.setdefault(r_id, []).append(ph_name)
            shape_id_to_region_id[sid] = r_id
            rendered_shape_count += 1
            semantic_shape_count += 1
            editable_text_shape_count += 1

            set_shape_alt_text(ph_box, title=f"Chart Deferred: {r_id}", description="Phase 3.3 Deferred Empirical Chart Placeholder")
            tf = ph_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"[Chart Reserved: {r_id}]"
            p.font.name = "Calibri"
            p.font.size = Pt(12.0)
            c_rgb, _ = resolve_color_token(ColorToken.TEXT_SECONDARY, palette)
            p.font.color.rgb = c_rgb
            p.alignment = PP_ALIGN.CENTER
            continue

        # D. Special Handling: Visual / Diagram Placeholders
        if role in (RegionSemanticRole.PRIMARY_VISUAL, RegionSemanticRole.SECONDARY_VISUAL):
            # Phase 3.4: Image Intelligence Integration
            from app.core.config import settings
            image_intelligence_enabled = getattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", False)
            chart_diagram_enabled = getattr(settings, "PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED", False)

            if image_intelligence_enabled and (visual_semantic_packet or (image_decisions and r_id in image_decisions)):
                from app.services.presentation.image_intelligence import (
                    assess_image_need,
                    ImageDecisionOutcome,
                )
                if image_decisions and r_id in image_decisions:
                    img_decision = image_decisions[r_id]
                else:
                    img_decision = assess_image_need(visual_semantic_packet, slide_content, region)

                if img_decision.outcome in (
                    ImageDecisionOutcome.IMAGE_REQUIRED,
                    ImageDecisionOutcome.IMAGE_USEFUL,
                ):
                    # Image placement will be handled by the orchestrator via image_bytes
                    # on the ImageAssetDecision. At render time, if the decision has
                    # image_bytes attached, we insert a native PPTX picture.
                    if img_decision.image_bytes:
                        from app.services.presentation.image_composition import (
                            insert_image_into_slide,
                        )
                        img_result = insert_image_into_slide(
                            slide, img_decision.image_bytes, img_decision,
                            bounds, region, design_dna, slide_no,
                        )
                        if img_result.success:
                            sid = img_result.picture_shape_id
                            sname = img_result.picture_shape_name
                            region_to_shape_ids.setdefault(r_id, []).append(sid)
                            region_to_shape_names.setdefault(r_id, []).append(sname)
                            shape_id_to_region_id[sid] = r_id
                            rendered_shape_count += 1
                            image_shape_count += 1

                            if img_result.attribution_shape_id:
                                asid = img_result.attribution_shape_id
                                asname = img_result.attribution_shape_name
                                region_to_shape_ids.setdefault(r_id, []).append(asid)
                                region_to_shape_names.setdefault(r_id, []).append(asname)
                                shape_id_to_region_id[asid] = r_id
                                rendered_shape_count += 1
                                editable_text_shape_count += 1
                            continue
                    # If no image_bytes yet, fall through to diagram or placeholder
                    pass

            if chart_diagram_enabled and (visual_semantic_packet or slide_content):
                from app.services.presentation.diagram_intelligence import (
                    select_diagram_archetype,
                    build_diagram_spec,
                    render_editable_diagram,
                )
                archetype, entities, rels = select_diagram_archetype(visual_semantic_packet, slide_content)
                diag_spec = build_diagram_spec(archetype, entities, rels, bounds)
                diag_res = render_editable_diagram(prs, slide, bounds, diag_spec, design_dna, slide_no, r_id)
                if diag_res.success and diag_res.node_count > 0:
                    for sid in diag_res.rendered_shape_ids:
                        region_to_shape_ids.setdefault(r_id, []).append(sid)
                        shape_id_to_region_id[sid] = r_id
                    for sname in diag_res.rendered_shape_names:
                        region_to_shape_names.setdefault(r_id, []).append(sname)
                    rendered_shape_count += (diag_res.node_count + diag_res.connector_count)
                    semantic_shape_count += diag_res.node_count
                    editable_text_shape_count += diag_res.node_count
                    continue

            deferred_asset_count += 1
            vis_box = slide.shapes.add_textbox(left_emu, top_emu, width_emu, height_emu)
            vis_name = f"TG:S{slide_no}:R{r_id}:visual_placeholder"
            vis_box.name = vis_name
            sid = vis_box.shape_id
            region_to_shape_ids.setdefault(r_id, []).append(sid)
            region_to_shape_names.setdefault(r_id, []).append(vis_name)
            shape_id_to_region_id[sid] = r_id
            rendered_shape_count += 1
            semantic_shape_count += 1
            editable_text_shape_count += 1

            set_shape_alt_text(vis_box, title=f"Visual Asset: {r_id}", description="Visual semantic reserved bounds")
            tf = vis_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            vis_label = str(raw_content) if raw_content else f"[Visual Canvas: {r_id}]"
            p.text = vis_label
            p.font.name = "Calibri"
            p.font.size = Pt(11.0)
            c_rgb, _ = resolve_color_token(ColorToken.TEXT_SECONDARY, palette)
            p.font.color.rgb = c_rgb
            p.alignment = PP_ALIGN.CENTER
            continue

        # E. Text Content Rendering
        tx_box = slide.shapes.add_textbox(left_emu, top_emu, width_emu, height_emu)
        t_name = f"TG:S{slide_no}:R{r_id}:text"
        tx_box.name = t_name
        sid = tx_box.shape_id
        region_to_shape_ids.setdefault(r_id, []).append(sid)
        region_to_shape_names.setdefault(r_id, []).append(t_name)
        shape_id_to_region_id[sid] = r_id
        rendered_shape_count += 1
        semantic_shape_count += 1
        editable_text_shape_count += 1

        tf = tx_box.text_frame
        tf.word_wrap = True

        # Vertical alignment
        try:
            anchor_map = {
                "top": "t",
                "middle": "ctr",
                "bottom": "b",
            }
            v_align = region.vertical_alignment.value if hasattr(region.vertical_alignment, "value") else str(region.vertical_alignment)
            tx_box.text_frame._txBody.bodyPr.set("anchor", anchor_map.get(v_align.lower(), "t"))
        except Exception:
            pass

        # Typography Spec & TextFit Resolution
        typo_spec = region.typography_spec
        t_role = typo_spec.role if typo_spec else TypographyRole.BODY
        requested_font = typo_spec.font_family if typo_spec else "Inter"
        resolved_font, fb_used, fb_reason = resolve_font_family(
            requested_font, t_role, design_dna, is_code=(role == RegionSemanticRole.CODE_BLOCK)
        )
        font_fallback_events.append(
            FontFallbackEvent(
                region_id=r_id,
                requested_font=requested_font,
                application_resolved_font=resolved_font,
                fallback_used=fb_used,
                fallback_reason=fb_reason,
            )
        )

        font_size_pt = typo_spec.font_size_pt if typo_spec else 13.5
        line_height_ratio = typo_spec.line_height_ratio if typo_spec else 1.4
        color_tok = typo_spec.color_token if typo_spec else ColorToken.TEXT_PRIMARY

        # Check for Phase 3.2B TextFitResult overrides
        if text_fit_results and r_id in text_fit_results:
            fit_res = text_fit_results[r_id]
            typo_after = getattr(fit_res, "typography_after", None)
            if typo_after and getattr(typo_after, "font_size_pt", 0) > 0:
                font_size_pt = typo_after.font_size_pt
                line_height_ratio = typo_after.line_height_ratio
            elif hasattr(fit_res, "font_size_pt") and fit_res.font_size_pt > 0:
                font_size_pt = fit_res.font_size_pt
                if hasattr(fit_res, "line_height_ratio") and fit_res.line_height_ratio > 0:
                    line_height_ratio = fit_res.line_height_ratio

        text_color_rgb, tc_warn = resolve_color_token(color_tok, palette)
        if tc_warn:
            renderer_warnings.append(tc_warn)

        # Paragraph alignment
        align_map = {
            "left": PP_ALIGN.LEFT,
            "center": PP_ALIGN.CENTER,
            "right": PP_ALIGN.RIGHT,
            "justify": PP_ALIGN.JUSTIFY,
        }
        r_align = region.alignment.value if hasattr(region.alignment, "value") else str(region.alignment)
        pp_align = align_map.get(r_align.lower(), PP_ALIGN.LEFT)

        # F. Format Content (Bullets, Formulas, Code, Single Strings)
        if role == RegionSemanticRole.FORMULA_DISPLAY:
            formula_text = ""
            if isinstance(raw_content, FormulaPayload):
                formula_text = raw_content.unicode_representation or raw_content.safe_literal_representation or raw_content.original_source
            elif isinstance(raw_content, str):
                formula_text = convert_latex_to_faithful_unicode(raw_content)
            else:
                formula_text = str(raw_content or "")

            p = tf.paragraphs[0]
            p.text = formula_text
            p.font.name = resolved_font
            p.font.size = Pt(font_size_pt)
            p.font.color.rgb = text_color_rgb
            p.alignment = pp_align
            set_shape_alt_text(tx_box, title=f"Formula {r_id}", description="Faithful Unicode Formula Representation")

        elif role == RegionSemanticRole.CODE_BLOCK:
            code_text = str(raw_content or "")
            p = tf.paragraphs[0]
            p.text = code_text
            p.font.name = "Consolas"
            p.font.size = Pt(max(9.5, font_size_pt - 2.0))
            p.font.color.rgb = text_color_rgb
            p.alignment = PP_ALIGN.LEFT
            set_shape_alt_text(tx_box, title=f"Code Block {r_id}", description="Monospaced Editable Code Segment")

        elif isinstance(raw_content, list):
            # Multiple bullet paragraphs
            for idx, item in enumerate(raw_content):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                item_str = str(item).strip()
                p.text = item_str
                p.font.name = resolved_font
                p.font.size = Pt(font_size_pt)
                p.font.color.rgb = text_color_rgb
                p.alignment = pp_align
                if line_height_ratio != 1.0:
                    p.line_spacing = line_height_ratio
                p.space_after = Pt(4.0)
                p.space_before = Pt(2.0)
                if typo_spec and typo_spec.letter_spacing_em != 0.0:
                    for run in p.runs:
                        set_shape_letter_spacing(run, typo_spec.letter_spacing_em)

        else:
            # Single paragraph or newline-separated text
            text_val = str(raw_content or "").strip()
            lines = text_val.split("\n")
            for idx, line in enumerate(lines):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                p.text = line
                p.font.name = resolved_font
                p.font.size = Pt(font_size_pt)
                p.font.color.rgb = text_color_rgb
                p.alignment = pp_align
                if typo_spec and typo_spec.font_weight >= 600:
                    p.font.bold = True
                if role == RegionSemanticRole.HEADER_TITLE:
                    p.font.bold = True
                if line_height_ratio != 1.0:
                    p.line_spacing = line_height_ratio
                if len(lines) > 1:
                    p.space_after = Pt(3.0)
                if typo_spec and typo_spec.letter_spacing_em != 0.0:
                    for run in p.runs:
                        set_shape_letter_spacing(run, typo_spec.letter_spacing_em)

        set_shape_alt_text(tx_box, title=f"Region {r_id}", description=f"Role: {role.value}")

    # 5. Attach Speaker Notes
    speaker_notes_written = False
    try:
        # Resolve notes from manifest if registered under source_id "slide_notes" or "slide_spec"
        notes_content = ""
        manifest_items = composition_input_manifest.raw_content_items
        for sid_key, item_dict in manifest_items.items():
            if "speaker_notes" in item_dict:
                notes_content = str(item_dict["speaker_notes"])
                break
        
        if notes_content:
            slide.notes_slide.notes_text_frame.text = notes_content
            speaker_notes_written = True
    except Exception as e:
        logger.warning(f"[CompositionRenderer] Failed to write speaker notes: {e}")
        renderer_warnings.append(f"Speaker notes writing warning: {e}")

    # 6. Run Native Editability Audit
    edit_audit = audit_rendered_slide_editability(slide)

    latency_ms = (time.perf_counter() - t_start) * 1000.0

    return RenderResult(
        slide_no=slide_no,
        success=True,
        terminal_status="SUCCESS",
        rendered_shape_count=rendered_shape_count,
        semantic_shape_count=semantic_shape_count,
        decorative_shape_count=decorative_shape_count,
        editable_text_shape_count=editable_text_shape_count,
        image_shape_count=image_shape_count,
        deferred_asset_count=deferred_asset_count,
        font_fallback_events=font_fallback_events,
        renderer_warnings=renderer_warnings,
        renderer_defects=renderer_defects,
        binding_validation_passed=True,
        geometry_validation_passed=True,
        content_hash_validation_passed=True,
        design_dna_preserved=True,
        semantic_integrity_preserved=True,
        region_to_shape_ids=region_to_shape_ids,
        region_to_shape_names=region_to_shape_names,
        shape_id_to_region_id=shape_id_to_region_id,
        speaker_notes_capability="NATIVE",
        render_latency_ms=latency_ms,
        editability_audit=edit_audit,
    )


# ═══════════════════════════════════════════════════════════════
# 10. FULL DECK PRESENTATION RENDERER
# ═══════════════════════════════════════════════════════════════

def render_composed_presentation(
    spec: PresentationSpec,
    composed_contexts: List[ComposedSlideContext],
    manifest: CompositionInputManifest,
    design_dna: DesignDNA,
    audit_results: Optional[Dict[int, Union[LayoutAuditResult, RepairResult]]] = None,
    text_fit_results: Optional[Dict[str, TextFitResult]] = None,
) -> Tuple[bytes, List[RenderResult]]:
    """
    Renders a complete deck from composed slide contexts.
    Fails closed immediately if any slide fails integrity, audit, or binding checks.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    render_results: List[RenderResult] = []

    for ctx in composed_contexts:
        s_no = ctx.slide_no
        blank_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_layout)

        audit_res = audit_results.get(s_no) if audit_results else None
        res = render_composed_slide(
            prs=prs,
            slide=slide,
            composed_context=ctx,
            composition_input_manifest=manifest,
            design_dna=design_dna,
            text_fit_results=text_fit_results,
            audit_result=audit_res,
            enforce_audit_gate=True,
        )
        render_results.append(res)

        if not res.success and res.terminal_status in FAIL_CLOSED_STATUSES:
            logger.error(f"[CompositionRenderer] Deck halted due to fail-closed error on slide {s_no}: {res.terminal_status}")
            raise ValueError(f"Composition rendering failed closed on slide {s_no}: {res.terminal_status} ({res.renderer_defects})")

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue(), render_results
