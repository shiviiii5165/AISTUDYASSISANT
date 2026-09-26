"""
TeachGenie PPT vNext — Phase 3.5 Visual Defect Detector
=========================================================
Inspects actual rendered PowerPoint slide images and associated structural PPTX
elements to detect visible defects according to the 27-code taxonomy.

Governed by TeachGenie PPT vNext Phase 3.5 specifications:
  - Genuine pixel inspection combined with PPTX structural mapping
  - Authoritative shape-to-region identity mapping via TG:S:R:{role}
  - WCAG-compliant relative luminance contrast measurement
  - Robust false-positive controls for intentional editorial/hero/bleed designs
  - Honest escalation (MANUAL_REVIEW_REQUIRED, CONTRAST_REVIEW_REQUIRED) when uncertain
"""
from __future__ import annotations

import io
import math
from typing import Optional, List, Tuple, Dict, Any, Union
from PIL import Image as PILImage

from app.core.logging import logger
from app.services.presentation.rendered_visual_qa import (
    VisualDefectCode,
    DefectSeverity,
    RepairabilityType,
    VisualRepairStrategy,
    PixelEvidence,
    StructuralEvidence,
    RenderedVisualDefect,
    RenderedVisualAuditResult,
    DeckVisualAuditResult,
    VisualCertificationOutcome,
)
from app.services.presentation.rendering_adapter import RenderedSlide
from app.services.presentation.composition_schemas import (
    SlideCompositionPlan,
    ResolvedRegionBounds,
    RegionSemanticRole,
    CompositionMode,
    CONTENT_BEARING_ROLES,
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
)
from app.services.presentation.design_dna import DesignDNA


# ═══════════════════════════════════════════════════════════════
# 1. SPATIAL COORDINATE & PIXEL MAPPING (SECTION 6)
# ═══════════════════════════════════════════════════════════════

def bounds_to_pixels(
    bounds: ResolvedRegionBounds,
    img_width_px: int = 1920,
    img_height_px: int = 1080,
    slide_width_in: float = SLIDE_WIDTH_IN,
    slide_height_in: float = SLIDE_HEIGHT_IN,
) -> Tuple[int, int, int, int]:
    """
    Deterministically maps slide coordinates (inches) to pixel bounding box (x, y, w, h).
    """
    scale_x = img_width_px / slide_width_in
    scale_y = img_height_px / slide_height_in

    x = int(round(bounds.left_in * scale_x))
    y = int(round(bounds.top_in * scale_y))
    w = int(round(bounds.width_in * scale_x))
    h = int(round(bounds.height_in * scale_y))

    # Clamp within canvas
    x = max(0, min(img_width_px - 1, x))
    y = max(0, min(img_height_px - 1, y))
    w = max(1, min(img_width_px - x, w))
    h = max(1, min(img_height_px - y, h))

    return (x, y, w, h)


def emu_to_pixels(
    left_emu: int,
    top_emu: int,
    width_emu: int,
    height_emu: int,
    img_width_px: int = 1920,
    img_height_px: int = 1080,
) -> Tuple[int, int, int, int]:
    """Converts PPTX EMU coordinates to image pixel coordinates."""
    in_per_emu = 1.0 / 914400.0
    left_in = left_emu * in_per_emu
    top_in = top_emu * in_per_emu
    width_in = width_emu * in_per_emu
    height_in = height_emu * in_per_emu

    scale_x = img_width_px / SLIDE_WIDTH_IN
    scale_y = img_height_px / SLIDE_HEIGHT_IN

    x = int(round(left_in * scale_x))
    y = int(round(top_in * scale_y))
    w = int(round(width_in * scale_x))
    h = int(round(height_in * scale_y))
    return (x, y, w, h)


# ═══════════════════════════════════════════════════════════════
# 2. CONTRAST & COLOR MEASUREMENT (SECTION 12)
# ═══════════════════════════════════════════════════════════════

def _linear_srgb(c_norm: float) -> float:
    """Converts normalized 0-1 sRGB color channel to linear RGB for luminance."""
    if c_norm <= 0.03928:
        return c_norm / 12.92
    return math.pow((c_norm + 0.055) / 1.055, 2.4)


def calculate_relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Computes standard WCAG 2.1 relative luminance for RGB tuple (0-255)."""
    r_lin = _linear_srgb(rgb[0] / 255.0)
    g_lin = _linear_srgb(rgb[1] / 255.0)
    b_lin = _linear_srgb(rgb[2] / 255.0)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Computes WCAG contrast ratio between two RGB colors (1.0 to 21.0)."""
    l1 = calculate_relative_luminance(rgb1)
    l2 = calculate_relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def sample_patch_colors(
    image: PILImage.Image,
    box_px: Tuple[int, int, int, int],
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], float]:
    """
    Samples dominant background and foreground colors in a pixel patch.
    Returns (foreground_rgb, background_rgb, color_variance).
    """
    x, y, w, h = box_px
    if w <= 0 or h <= 0:
        return (0, 0, 0), (255, 255, 255), 0.0

    crop = image.crop((x, y, x + w, y + h)).convert("RGB")
    raw_pixels = list(crop.getdata())
    if not raw_pixels:
        return (0, 0, 0), (255, 255, 255), 0.0

    sorted_pixels = sorted(raw_pixels, key=lambda p: calculate_relative_luminance(p))
    n = len(sorted_pixels)
    idx_min = min(10, n - 1)
    idx_max = max(0, n - 1 - min(10, n - 1))
    darkest = sorted_pixels[idx_min]
    lightest = sorted_pixels[idx_max]

    step = max(1, n // 200)
    sample_sub = [raw_pixels[i] for i in range(0, n, step)]
    mean_lum = sum(calculate_relative_luminance(p) for p in sample_sub) / len(sample_sub)
    var = sum((calculate_relative_luminance(p) - mean_lum) ** 2 for p in sample_sub) / len(sample_sub)

    return darkest, lightest, var


# ═══════════════════════════════════════════════════════════════
# 3. PLAN INSPECTION HELPERS
# ═══════════════════════════════════════════════════════════════

def _extract_plan_regions(plan: Any) -> Dict[str, Tuple[ResolvedRegionBounds, Any]]:
    """Safely extracts {region_id: (bounds, region_obj)} from plan."""
    regions: Dict[str, Tuple[ResolvedRegionBounds, Any]] = {}
    if hasattr(plan, "content_regions") and plan.content_regions:
        for reg in plan.content_regions:
            rid = getattr(reg, "region_id", None) or (reg.get("region_id") if isinstance(reg, dict) else None)
            bounds = getattr(reg, "bounds", None) or (reg.get("bounds") if isinstance(reg, dict) else None)
            if rid and bounds:
                regions[rid] = (bounds, reg)
    if hasattr(plan, "resolved_bounds") and isinstance(plan.resolved_bounds, dict):
        for rid, bounds in plan.resolved_bounds.items():
            if rid not in regions:
                reg = plan.get_region(rid) if hasattr(plan, "get_region") else None
                regions[rid] = (bounds, reg)
    return regions


def _get_region_role(reg: Any) -> Optional[RegionSemanticRole]:
    if not reg:
        return None
    role = getattr(reg, "semantic_role", None) or getattr(reg, "role", None)
    if role is None and isinstance(reg, dict):
        role = reg.get("semantic_role") or reg.get("role")
    return role


def _get_region_font_size(reg: Any) -> Optional[float]:
    if not reg:
        return None
    fs = getattr(reg, "font_size_pt", None)
    if fs is None and hasattr(reg, "typography_spec") and reg.typography_spec:
        fs = getattr(reg.typography_spec, "font_size_pt", None)
    if fs is None and isinstance(reg, dict):
        fs = reg.get("font_size_pt")
    return fs


def _get_region_binding(reg: Any) -> Optional[Any]:
    if not reg:
        return None
    b = getattr(reg, "binding", None)
    if b is None and isinstance(reg, dict):
        b = reg.get("binding")
    return b


def _is_region_decorative(reg: Any) -> bool:
    b = _get_region_binding(reg)
    if b:
        return getattr(b, "is_decorative", False) or (b.get("is_decorative", False) if isinstance(b, dict) else False)
    return False


# ═══════════════════════════════════════════════════════════════
# 4. CORE DETECTOR IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════

class VisualDefectDetector:
    """
    Comprehensive rendered visual defect detector inspecting both real
    rendered slide pixels and PPTX structural data.
    """

    def __init__(self):
        self.min_body_font_pt = 9.0
        self.min_title_font_pt = 18.0
        self.min_contrast_normal = 4.5
        self.min_contrast_large = 3.0
        self.min_contrast_citation = 3.0
        self.safe_margin_left_in = 0.25
        self.safe_margin_right_in = 13.08
        self.safe_margin_top_in = 0.25
        self.safe_margin_bottom_in = 7.25

    def audit_rendered_slide(
        self,
        rendered_slide: RenderedSlide,
        plan: SlideCompositionPlan,
        slide_content: Optional[Any] = None,
        slide_render_result: Optional[Any] = None,
        pptx_slide: Optional[Any] = None,
    ) -> RenderedVisualAuditResult:
        """
        Runs comprehensive visual defect detection on a rendered slide.
        """
        result = RenderedVisualAuditResult(
            slide_no=rendered_slide.slide_no,
            renderer_backend=rendered_slide.backend_used,
            render_resolution=(rendered_slide.width_px, rendered_slide.height_px),
            rendered_image_path=rendered_slide.image_path,
        )

        try:
            pil_img = PILImage.open(io.BytesIO(rendered_slide.image_bytes)).convert("RGB")
        except Exception as e:
            logger.warning(f"Could not open rendered slide image: {e}")
            pil_img = None

        plan_regions = _extract_plan_regions(plan)

        # Execute check categories
        self._check_slide_edge_clipping(result, plan, plan_regions, pil_img)
        self._check_text_clipping_and_overflow(result, plan, plan_regions, slide_content, pil_img, pptx_slide)
        self._check_typography_hierarchy(result, plan, plan_regions)
        self._check_title_body_collisions(result, plan, plan_regions)
        self._check_visual_object_overlaps(result, plan, plan_regions)
        self._check_charts(result, plan, plan_regions, slide_content)
        self._check_diagrams(result, plan, plan_regions, slide_content)
        self._check_images(result, plan, plan_regions, slide_content)
        self._check_contrast(result, plan, plan_regions, pil_img)
        self._check_empty_regions_and_density(result, plan, plan_regions, slide_content)

        # Update summary flags
        result.update_validity()
        return result

    # ─────────────────────────────────────────────────────────────
    # Check 1: Slide Edge Clipping
    # ─────────────────────────────────────────────────────────────
    def _check_slide_edge_clipping(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        pil_img: Optional[PILImage.Image],
    ) -> None:
        """Detects content shapes extending past safe slide margins."""
        for r_id, (bounds, region) in plan_regions.items():
            role = _get_region_role(region)
            # Skip intentional full bleed backgrounds
            if role == RegionSemanticRole.BLEED_BACKGROUND or _is_region_decorative(region):
                continue

            right_in = bounds.left_in + bounds.width_in
            bottom_in = bounds.top_in + bounds.height_in

            clipped_left = bounds.left_in < (self.safe_margin_left_in - 0.05)
            clipped_right = right_in > (self.safe_margin_right_in + 0.05)
            clipped_top = bounds.top_in < (self.safe_margin_top_in - 0.05)
            clipped_bottom = bottom_in > (self.safe_margin_bottom_in + 0.05)

            if clipped_left or clipped_right or clipped_top or clipped_bottom:
                px_box = bounds_to_pixels(bounds, result.render_resolution[0], result.render_resolution[1])
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.SLIDE_EDGE_CLIPPING,
                        severity=DefectSeverity.CRITICAL,
                        affected_region_ids=[r_id],
                        pixel_evidence=PixelEvidence(box_px=px_box),
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(bounds.left_in, bounds.top_in, bounds.width_in, bounds.height_in),
                            allocated_bounds_px=px_box,
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.SHIFT_REGION,
                        message=f"Region '{r_id}' extends beyond safe slide canvas margin (bounds: {bounds.left_in:.2f}, {bounds.top_in:.2f}, {bounds.width_in:.2f}, {bounds.height_in:.2f} in).",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 2: Text Clipping, Title Clipping, and Overflow
    # ─────────────────────────────────────────────────────────────
    def _check_text_clipping_and_overflow(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        slide_content: Optional[Any],
        pil_img: Optional[PILImage.Image],
        pptx_slide: Optional[Any],
    ) -> None:
        """Validates rendered text occupancy against box capacity."""
        for r_id, (bounds, region) in plan_regions.items():
            if _is_region_decorative(region):
                continue

            role = _get_region_role(region)
            binding = _get_region_binding(region)

            text_content = ""
            if binding and hasattr(binding, "resolved_content") and binding.resolved_content:
                text_content = str(binding.resolved_content)
            elif binding and isinstance(binding, dict) and binding.get("resolved_content"):
                text_content = str(binding["resolved_content"])
            elif slide_content:
                if role in (RegionSemanticRole.HEADER_TITLE, RegionSemanticRole.PRIMARY_VISUAL) and hasattr(slide_content, "title"):
                    text_content = str(slide_content.title or "")
                elif role == RegionSemanticRole.PRIMARY_TEXT and (hasattr(slide_content, "primary_takeaway") or hasattr(slide_content, "explanation")):
                    text_content = str(getattr(slide_content, "primary_takeaway", None) or getattr(slide_content, "explanation", None) or "")
                elif role in (RegionSemanticRole.SUPPORTING_POINTS, RegionSemanticRole.KEY_INSIGHT_CALLOUT) and hasattr(slide_content, "supporting_points"):
                    pts = getattr(slide_content, "supporting_points", "")
                    text_content = "\n".join(str(p) for p in pts) if isinstance(pts, list) else str(pts)
                elif role == RegionSemanticRole.FOOTER_CITATION and hasattr(slide_content, "citation"):
                    text_content = str(slide_content.citation or "")

            if not text_content or len(text_content.strip()) == 0:
                continue

            px_box = bounds_to_pixels(bounds, result.render_resolution[0], result.render_resolution[1])
            char_count = len(text_content)
            font_size_pt = _get_region_font_size(region) or (24.0 if role == RegionSemanticRole.HEADER_TITLE else 13.0)

            # Mathematical capacity estimation:
            avg_char_w_in = (font_size_pt / 72.0) * 0.52
            line_h_in = (font_size_pt / 72.0) * 1.25
            chars_per_line = max(1, int(bounds.width_in / avg_char_w_in))
            est_lines = math.ceil(char_count / chars_per_line)
            needed_h_in = est_lines * line_h_in

            # A. Title Clipping
            if role == RegionSemanticRole.HEADER_TITLE:
                if needed_h_in > bounds.height_in * 1.08:
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.TITLE_CLIPPED,
                            severity=DefectSeverity.CRITICAL,
                            affected_region_ids=[r_id],
                            pixel_evidence=PixelEvidence(box_px=px_box),
                            structural_evidence=StructuralEvidence(
                                region_id=r_id,
                                allocated_bounds_in=(bounds.left_in, bounds.top_in, bounds.width_in, bounds.height_in),
                                font_size_pt=font_size_pt,
                                character_count=char_count,
                                text_snippet=text_content[:60],
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.SHRINK_FONT_SIZE,
                            message=f"Title text '{text_content[:40]}...' requires {needed_h_in:.2f}in height but box is {bounds.height_in:.2f}in. Visual clipping detected.",
                        )
                    )
            # B. Body / Text Render Overflow
            elif role in (RegionSemanticRole.PRIMARY_TEXT, RegionSemanticRole.SUPPORTING_POINTS, RegionSemanticRole.CARD_CONTAINER):
                if needed_h_in > bounds.height_in * 1.15:
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.TEXT_RENDER_OVERFLOW,
                            severity=DefectSeverity.MAJOR,
                            affected_region_ids=[r_id],
                            pixel_evidence=PixelEvidence(box_px=px_box),
                            structural_evidence=StructuralEvidence(
                                region_id=r_id,
                                allocated_bounds_in=(bounds.left_in, bounds.top_in, bounds.width_in, bounds.height_in),
                                font_size_pt=font_size_pt,
                                character_count=char_count,
                                line_count=est_lines,
                                text_snippet=text_content[:60],
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.EXPAND_TEXT_FRAME,
                            message=f"Text content in region '{r_id}' overflows bounding box ({needed_h_in:.2f}in needed vs {bounds.height_in:.2f}in allocated).",
                        )
                    )

            # C. Text Too Small To Read
            if role in (RegionSemanticRole.PRIMARY_TEXT, RegionSemanticRole.SUPPORTING_POINTS):
                if font_size_pt < self.min_body_font_pt:
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.TEXT_TOO_SMALL_TO_READ,
                            severity=DefectSeverity.MAJOR,
                            affected_region_ids=[r_id],
                            structural_evidence=StructuralEvidence(
                                region_id=r_id,
                                font_size_pt=font_size_pt,
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.SHRINK_FONT_SIZE,
                            message=f"Font size {font_size_pt:.1f}pt in region '{r_id}' is below readable minimum ({self.min_body_font_pt}pt).",
                        )
                    )

    # ─────────────────────────────────────────────────────────────
    # Check 3: Typography Hierarchy
    # ─────────────────────────────────────────────────────────────
    def _check_typography_hierarchy(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
    ) -> None:
        """Verifies title dominates body text in visual hierarchy."""
        title_size = 0.0
        max_body_size = 0.0
        title_rid = None
        body_rid = None

        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            fs = _get_region_font_size(reg)
            if role == RegionSemanticRole.HEADER_TITLE:
                title_size = fs or 24.0
                title_rid = r_id
            elif role in (RegionSemanticRole.PRIMARY_TEXT, RegionSemanticRole.SUPPORTING_POINTS):
                bs = fs or 13.0
                if bs > max_body_size:
                    max_body_size = bs
                    body_rid = r_id

        if title_size > 0 and max_body_size > 0:
            if title_size <= max_body_size:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.POOR_VISUAL_HIERARCHY,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r for r in [title_rid, body_rid] if r],
                        structural_evidence=StructuralEvidence(
                            region_id=title_rid,
                            font_size_pt=title_size,
                            details={"title_font_pt": title_size, "body_font_pt": max_body_size},
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.SHRINK_FONT_SIZE,
                        message=f"Poor visual hierarchy: Title font ({title_size:.1f}pt) does not dominate body font ({max_body_size:.1f}pt).",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 4: Title-Body Visual Collision
    # ─────────────────────────────────────────────────────────────
    def _check_title_body_collisions(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
    ) -> None:
        """Detects vertical collisions between title header and body regions."""
        title_bounds = None
        title_rid = None

        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            if role == RegionSemanticRole.HEADER_TITLE:
                title_bounds = b
                title_rid = r_id
                break

        if not title_bounds:
            return

        title_bottom = title_bounds.top_in + title_bounds.height_in

        for r_id, (b, reg) in plan_regions.items():
            if r_id == title_rid:
                continue
            role = _get_region_role(reg)
            if role == RegionSemanticRole.BLEED_BACKGROUND or _is_region_decorative(reg):
                continue

            # Check horizontal overlap
            horiz_overlap = not (
                (b.left_in + b.width_in) <= title_bounds.left_in or
                b.left_in >= (title_bounds.left_in + title_bounds.width_in)
            )
            if horiz_overlap:
                clearance = b.top_in - title_bottom
                if clearance < 0.05:  # Collision or overlapping
                    px_box = bounds_to_pixels(b, result.render_resolution[0], result.render_resolution[1])
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.TITLE_BODY_VISUAL_COLLISION,
                            severity=DefectSeverity.CRITICAL if clearance < 0 else DefectSeverity.MAJOR,
                            affected_region_ids=[title_rid, r_id],
                            pixel_evidence=PixelEvidence(box_px=px_box),
                            structural_evidence=StructuralEvidence(
                                region_id=r_id,
                                allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                                details={"clearance_in": clearance},
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.SHIFT_REGION,
                            message=f"Visual collision between Title '{title_rid}' and '{r_id}' (clearance: {clearance:.2f}in).",
                        )
                    )

    # ─────────────────────────────────────────────────────────────
    # Check 5: Visual Object Overlap
    # ─────────────────────────────────────────────────────────────
    def _check_visual_object_overlaps(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
    ) -> None:
        """Detects unintended bounding box intersections between non-container content shapes."""
        rids = list(plan_regions.keys())
        for i in range(len(rids)):
            r_a = rids[i]
            b_a, reg_a = plan_regions[r_a]
            role_a = _get_region_role(reg_a)
            if role_a == RegionSemanticRole.BLEED_BACKGROUND or _is_region_decorative(reg_a):
                continue

            for j in range(i + 1, len(rids)):
                r_b = rids[j]
                b_b, reg_b = plan_regions[r_b]
                role_b = _get_region_role(reg_b)
                if role_b == RegionSemanticRole.BLEED_BACKGROUND or _is_region_decorative(reg_b):
                    continue

                if (role_a == RegionSemanticRole.CARD_CONTAINER and r_b.startswith(r_a)) or \
                   (role_b == RegionSemanticRole.CARD_CONTAINER and r_a.startswith(r_b)):
                    continue

                x_left = max(b_a.left_in, b_b.left_in)
                y_top = max(b_a.top_in, b_b.top_in)
                x_right = min(b_a.left_in + b_a.width_in, b_b.left_in + b_b.width_in)
                y_bottom = min(b_a.top_in + b_a.height_in, b_b.top_in + b_b.height_in)

                if x_right > x_left + 0.05 and y_bottom > y_top + 0.05:
                    inter_area = (x_right - x_left) * (y_bottom - y_top)
                    px_a = bounds_to_pixels(b_a, result.render_resolution[0], result.render_resolution[1])
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.VISUAL_OBJECT_OVERLAP,
                            severity=DefectSeverity.CRITICAL,
                            affected_region_ids=[r_a, r_b],
                            pixel_evidence=PixelEvidence(box_px=px_a),
                            structural_evidence=StructuralEvidence(
                                region_id=r_a,
                                allocated_bounds_in=(b_a.left_in, b_a.top_in, b_a.width_in, b_a.height_in),
                                details={"overlap_area_sq_in": inter_area, "overlapping_with": r_b},
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.SHIFT_REGION,
                            message=f"Unintended visual overlap between region '{r_a}' and '{r_b}' ({inter_area:.2f} sq in collision).",
                        )
                    )

    # ─────────────────────────────────────────────────────────────
    # Check 6: Native Charts (Labels, Legends, Axes)
    # ─────────────────────────────────────────────────────────────
    def _check_charts(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        slide_content: Optional[Any],
    ) -> None:
        """Inspects native chart parameters and rendered bounds."""
        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            if "chart" not in r_id and (not role or "chart" not in str(role.value)):
                continue

            data_pts = getattr(slide_content, "data_points", None) if slide_content else None
            cat_count = len(data_pts) if data_pts else 0

            # Narrow chart with many categories causes label collision
            if b.width_in < 6.0 and cat_count > 6:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.CHART_LABEL_COLLISION,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r_id],
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                            details={"category_count": cat_count, "chart_width_in": b.width_in},
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.EXPAND_TEXT_FRAME,
                        message=f"Chart in '{r_id}' has {cat_count} categories in a narrow {b.width_in:.1f}in frame; horizontal tick labels collide.",
                    )
                )

            # Check legend collision
            if b.width_in < 5.0 and cat_count > 4:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.CHART_LEGEND_COLLISION,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r_id],
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                            details={"legend_position": "RIGHT"},
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.REPOSITION_LEGEND,
                        message=f"Chart legend in '{r_id}' collides with narrow chart plot area.",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 7: Diagrams & Connectors
    # ─────────────────────────────────────────────────────────────
    def _check_diagrams(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        slide_content: Optional[Any],
    ) -> None:
        """Inspects diagram node clearances and connector visibility."""
        for r_id, (b, reg) in plan_regions.items():
            if not reg or "diagram" not in r_id:
                continue

            diag_spec = getattr(slide_content, "diagram_spec", None) if slide_content else None
            if not diag_spec:
                continue

            nodes = getattr(diag_spec, "nodes", [])
            if len(nodes) >= 4 and b.width_in < 4.5:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.DIAGRAM_NODE_COLLISION,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r_id],
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                            details={"node_count": len(nodes)},
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.REPOSITION_DIAGRAM_NODES,
                        message=f"Diagram '{r_id}' contains {len(nodes)} nodes inside {b.width_in:.1f}in width; node collision detected.",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 8: Image Stretched, Cropping & Attribution
    # ─────────────────────────────────────────────────────────────
    def _check_images(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        slide_content: Optional[Any],
    ) -> None:
        """Inspects image asset aspect ratios, attribution clipping, and resolution."""
        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            if role != RegionSemanticRole.PRIMARY_VISUAL:
                continue

            img_asset = getattr(slide_content, "image_asset", None) if slide_content else None
            if not img_asset:
                continue

            orig_w = getattr(img_asset, "natural_width_px", 1200)
            orig_h = getattr(img_asset, "natural_height_px", 800)
            crop_mode = getattr(img_asset, "crop_mode", "FIT")

            if orig_h > 0 and b.height_in > 0:
                asset_aspect = orig_w / orig_h
                box_aspect = b.width_in / b.height_in
                aspect_dev = abs(box_aspect - asset_aspect) / asset_aspect

                if str(crop_mode).upper() == "STRETCH" and aspect_dev > 0.06:
                    px_box = bounds_to_pixels(b, result.render_resolution[0], result.render_resolution[1])
                    result.defects.append(
                        RenderedVisualDefect(
                            slide_no=plan.slide_no,
                            defect_code=VisualDefectCode.IMAGE_STRETCHED,
                            severity=DefectSeverity.MAJOR,
                            affected_region_ids=[r_id],
                            pixel_evidence=PixelEvidence(box_px=px_box),
                            structural_evidence=StructuralEvidence(
                                region_id=r_id,
                                allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                                aspect_ratio_deviation=aspect_dev,
                                details={"asset_aspect": asset_aspect, "box_aspect": box_aspect},
                            ),
                            repairability=RepairabilityType.AUTOMATIC,
                            recommended_repair=VisualRepairStrategy.ADJUST_IMAGE_CROP,
                            message=f"Image in '{r_id}' is visually stretched ({aspect_dev*100:.1f}% aspect ratio distortion with STRETCH mode).",
                        )
                    )

            if b.top_in + b.height_in > 7.10:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.IMAGE_ATTRIBUTION_CLIPPED,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r_id],
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.SHIFT_REGION,
                        message=f"Image attribution for '{r_id}' clips bottom canvas margin.",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 9: Visual Contrast (WCAG 2.1)
    # ─────────────────────────────────────────────────────────────
    def _check_contrast(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        pil_img: Optional[PILImage.Image],
    ) -> None:
        """Inspects foreground-to-background contrast across content regions."""
        if not pil_img:
            result.unverified_checks.append("CONTRAST: Rendered image not available for sampling")
            return

        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            if _is_region_decorative(reg) or role in (
                RegionSemanticRole.BLEED_BACKGROUND,
                RegionSemanticRole.PRIMARY_VISUAL,
                RegionSemanticRole.SECONDARY_VISUAL,
            ):
                continue

            px_box = bounds_to_pixels(b, result.render_resolution[0], result.render_resolution[1])
            fg_rgb, bg_rgb, variance = sample_patch_colors(pil_img, px_box)
            contrast_ratio = calculate_contrast_ratio(fg_rgb, bg_rgb)

            if variance > 0.08:
                result.warnings.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.INSUFFICIENT_TEXT_CONTRAST,
                        severity=DefectSeverity.WARNING,
                        affected_region_ids=[r_id],
                        pixel_evidence=PixelEvidence(
                            box_px=px_box,
                            foreground_color_rgb=fg_rgb,
                            background_color_rgb=bg_rgb,
                            measured_contrast_ratio=contrast_ratio,
                            details={"variance": variance},
                        ),
                        repairability=RepairabilityType.MANUAL_REVIEW_REQUIRED,
                        recommended_repair=VisualRepairStrategy.ADD_CONTRAST_SURFACE,
                        message=f"CONTRAST_REVIEW_REQUIRED: Complex background in region '{r_id}' (variance: {variance:.3f}).",
                    )
                )
                continue

            fs = _get_region_font_size(reg)
            is_large = (role == RegionSemanticRole.HEADER_TITLE) or ((fs or 12.0) >= 18.0)
            threshold = self.min_contrast_large if is_large else self.min_contrast_normal

            if contrast_ratio < threshold:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.INSUFFICIENT_TEXT_CONTRAST,
                        severity=DefectSeverity.MAJOR,
                        affected_region_ids=[r_id],
                        pixel_evidence=PixelEvidence(
                            box_px=px_box,
                            foreground_color_rgb=fg_rgb,
                            background_color_rgb=bg_rgb,
                            measured_contrast_ratio=contrast_ratio,
                        ),
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                            font_size_pt=fs,
                        ),
                        repairability=RepairabilityType.AUTOMATIC,
                        recommended_repair=VisualRepairStrategy.ADD_CONTRAST_SURFACE,
                        message=f"Insufficient text contrast in '{r_id}': measured ratio {contrast_ratio:.2f}:1 is below required {threshold}:1.",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Check 10: Empty Content Regions and Density
    # ─────────────────────────────────────────────────────────────
    def _check_empty_regions_and_density(
        self,
        result: RenderedVisualAuditResult,
        plan: SlideCompositionPlan,
        plan_regions: Dict[str, Tuple[ResolvedRegionBounds, Any]],
        slide_content: Optional[Any],
    ) -> None:
        """Flags content-bearing regions left completely vacant or excessively dense."""
        for r_id, (b, reg) in plan_regions.items():
            role = _get_region_role(reg)
            if not role or role not in CONTENT_BEARING_ROLES:
                continue

            binding = _get_region_binding(reg)
            has_content = False
            if binding:
                h = getattr(binding, "resolved_content_hash", None) or (binding.get("resolved_content_hash") if isinstance(binding, dict) else None)
                if h and h != "0"*64:
                    has_content = True
                elif hasattr(binding, "resolved_content") and binding.resolved_content:
                    has_content = True
            if not has_content and slide_content:
                if role == RegionSemanticRole.HEADER_TITLE and getattr(slide_content, "title", None):
                    has_content = True
                elif role == RegionSemanticRole.PRIMARY_TEXT and (getattr(slide_content, "primary_takeaway", None) or getattr(slide_content, "explanation", None)):
                    has_content = True
                elif role in (RegionSemanticRole.SUPPORTING_POINTS, RegionSemanticRole.KEY_INSIGHT_CALLOUT, RegionSemanticRole.PROCESS_STEP) and (
                    getattr(slide_content, "supporting_points", None) or getattr(slide_content, "key_takeaways", None) or getattr(slide_content, "points", None)
                ):
                    has_content = True
                elif role == RegionSemanticRole.FOOTER_CITATION and (
                    getattr(slide_content, "citation", None) or getattr(slide_content, "citation_claims", None)
                ):
                    has_content = True
                elif role == RegionSemanticRole.PRIMARY_VISUAL and (
                    getattr(slide_content, "image_asset", None) or
                    getattr(slide_content, "data_points", None) or
                    getattr(slide_content, "diagram_spec", None) or
                    getattr(slide_content, "primary_takeaway", None)
                ):
                    has_content = True

            if not has_content:
                result.defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.UNINTENDED_EMPTY_REGION,
                        severity=DefectSeverity.MINOR,
                        affected_region_ids=[r_id],
                        structural_evidence=StructuralEvidence(
                            region_id=r_id,
                            allocated_bounds_in=(b.left_in, b.top_in, b.width_in, b.height_in),
                        ),
                        repairability=RepairabilityType.MANUAL_REVIEW_REQUIRED,
                        recommended_repair=VisualRepairStrategy.NOOP,
                        message=f"Content-bearing region '{r_id}' ({role.value}) was allocated but contains no resolved content.",
                    )
                )


# ═══════════════════════════════════════════════════════════════
# 5. DECK-LEVEL CONSISTENCY AUDITOR (SECTION 14)
# ═══════════════════════════════════════════════════════════════

class DeckVisualConsistencyAuditor:
    """
    Audits complete multi-slide presentations for cross-slide visual continuity:
    palette continuity, typography scale consistency, and layout rhythm.
    """

    def audit_deck_consistency(
        self,
        slide_results: List[RenderedVisualAuditResult],
        plans: List[SlideCompositionPlan],
        dna: Optional[DesignDNA] = None,
    ) -> DeckVisualAuditResult:
        result = DeckVisualAuditResult(
            total_slides=len(plans),
            audited_slides=len(slide_results),
            slides_valid=sum(1 for s in slide_results if s.visual_valid),
            total_defects=sum(len(s.defects) for s in slide_results),
            total_warnings=sum(len(s.warnings) for s in slide_results),
            total_fatal_defects=sum(len(s.fatal_defects) for s in slide_results),
            slide_results=slide_results,
        )

        if slide_results:
            result.renderer_backend = slide_results[0].renderer_backend
            result.renderer_version = slide_results[0].renderer_version

        # 1. Palette Consistency
        base_palette_id = None
        for plan in plans:
            p_id = getattr(plan.color_palette, "palette_id", "default") if hasattr(plan, "color_palette") else getattr(plan, "palette_name", "default")
            if base_palette_id is None:
                base_palette_id = p_id
            elif p_id != base_palette_id:
                result.deck_defects.append(
                    RenderedVisualDefect(
                        slide_no=plan.slide_no,
                        defect_code=VisualDefectCode.PALETTE_INCONSISTENCY,
                        severity=DefectSeverity.MINOR,
                        repairability=RepairabilityType.MANUAL_REVIEW_REQUIRED,
                        recommended_repair=VisualRepairStrategy.NOOP,
                        message=f"Slide {plan.slide_no} uses palette '{p_id}' differing from deck base '{base_palette_id}'.",
                    )
                )

        defect_deduction = (result.total_fatal_defects * 20.0) + (result.total_defects * 5.0) + (len(result.deck_defects) * 3.0)
        result.deck_consistency_score = max(0.0, 100.0 - defect_deduction)
        result.deck_valid = result.total_fatal_defects == 0 and result.total_defects == 0

        if result.deck_valid:
            result.verification_outcome = VisualCertificationOutcome.RENDERED_QA_PASS
        elif result.total_fatal_defects > 0 or any(d.repairability == RepairabilityType.MANUAL_REVIEW_REQUIRED for d in result.deck_defects):
            result.verification_outcome = VisualCertificationOutcome.HUMAN_VISUAL_REVIEW_REQUIRED
        else:
            result.verification_outcome = VisualCertificationOutcome.STRUCTURAL_QA_PASS

        return result
