"""
TeachGenie PPT vNext — Phase 3.4 Image Composition & PPTX Rendering
====================================================================
Implements image-region placement, contain/cover crop decisions, focal-region
preservation, image-to-region mapping, and native PPTX picture insertion.

Governance:
  - Consumes exact approved ResolvedRegionBounds — never recalculates parent layout.
  - Text remains native and editable; diagrams remain native shapes; charts remain native.
  - Images are rendered as native PowerPoint picture objects (not slide-level rasterization).
  - Every picture shape carries deterministic TG:S{slide}:R{region}:img name.
  - region_to_shape_ids and shape_id_to_region_id are updated in RenderResult.
  - DesignDNA image_treatment and corner/border tokens are respected.
"""
from __future__ import annotations

import io
import time
from typing import Optional, List, Dict, Any, Tuple

from pydantic import BaseModel, Field

from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from lxml import etree

from app.core.logging import logger
from app.services.presentation.image_intelligence import (
    ImageAssetDecision,
    ImageDecisionOutcome,
    ImageTypeClassification,
    ImageProvenance,
    ImageRightsMetadata,
    CropMode,
    ImageDefectCode,
    compute_content_hash,
    generate_alt_text,
)
from app.services.presentation.composition_schemas import (
    ResolvedRegionBounds,
    ContentRegion,
    RegionSemanticRole,
)
from app.services.presentation.visual_schemas import DesignDNA


# ═══════════════════════════════════════════════════════════════
# 1. IMAGE PLACEMENT RESULT
# ═══════════════════════════════════════════════════════════════

class ImagePlacementResult(BaseModel):
    """Result of placing an image into a PPTX slide."""
    success: bool = False
    picture_shape_id: int = 0
    picture_shape_name: str = ""
    attribution_shape_id: Optional[int] = None
    attribution_shape_name: Optional[str] = None
    region_id: str = ""
    slide_no: int = 0
    crop_mode_applied: CropMode = CropMode.CONTAIN
    image_left_emu: int = 0
    image_top_emu: int = 0
    image_width_emu: int = 0
    image_height_emu: int = 0
    alt_text: str = ""
    defects: List[str] = Field(default_factory=list)
    provenance: Optional[ImageProvenance] = None


# ═══════════════════════════════════════════════════════════════
# 2. CROP GEOMETRY CALCULATION
# ═══════════════════════════════════════════════════════════════

def calculate_contain_geometry(
    image_width_px: int,
    image_height_px: int,
    region_left_emu: int,
    region_top_emu: int,
    region_width_emu: int,
    region_height_emu: int,
) -> Tuple[int, int, int, int]:
    """
    Calculates CONTAIN placement: scales image to fit entirely within region
    while maintaining aspect ratio. Centers the image in the region.
    """
    if image_width_px <= 0 or image_height_px <= 0:
        return region_left_emu, region_top_emu, region_width_emu, region_height_emu

    img_ar = image_width_px / image_height_px
    region_ar = region_width_emu / max(region_height_emu, 1)

    if img_ar > region_ar:
        # Image is wider: fit to width, center vertically
        fit_width = region_width_emu
        fit_height = int(region_width_emu / img_ar)
        fit_left = region_left_emu
        fit_top = region_top_emu + (region_height_emu - fit_height) // 2
    else:
        # Image is taller: fit to height, center horizontally
        fit_height = region_height_emu
        fit_width = int(region_height_emu * img_ar)
        fit_left = region_left_emu + (region_width_emu - fit_width) // 2
        fit_top = region_top_emu

    return fit_left, fit_top, fit_width, fit_height


def calculate_cover_geometry(
    image_width_px: int,
    image_height_px: int,
    region_left_emu: int,
    region_top_emu: int,
    region_width_emu: int,
    region_height_emu: int,
) -> Tuple[int, int, int, int, Dict[str, float]]:
    """
    Calculates COVER placement: scales image to fill entire region
    while maintaining aspect ratio, with center-weighted cropping.
    Returns (left, top, width, height, crop_offsets_pct).
    """
    if image_width_px <= 0 or image_height_px <= 0:
        return region_left_emu, region_top_emu, region_width_emu, region_height_emu, {}

    img_ar = image_width_px / image_height_px
    region_ar = region_width_emu / max(region_height_emu, 1)

    # For cover: place at region bounds, crop via PPTX crop offsets
    crop = {}
    if img_ar > region_ar:
        # Image is wider than region: crop left/right
        visible_fraction = region_ar / img_ar
        crop_total = 1.0 - visible_fraction
        crop["left"] = crop_total / 2
        crop["right"] = crop_total / 2
        crop["top"] = 0.0
        crop["bottom"] = 0.0
    else:
        # Image is taller than region: crop top/bottom
        visible_fraction = img_ar / region_ar
        crop_total = 1.0 - visible_fraction
        crop["left"] = 0.0
        crop["right"] = 0.0
        crop["top"] = crop_total / 2
        crop["bottom"] = crop_total / 2

    return region_left_emu, region_top_emu, region_width_emu, region_height_emu, crop


# ═══════════════════════════════════════════════════════════════
# 3. NATIVE PPTX IMAGE INSERTION
# ═══════════════════════════════════════════════════════════════

def insert_image_into_slide(
    slide: Slide,
    image_bytes: bytes,
    decision: ImageAssetDecision,
    bounds: ResolvedRegionBounds,
    region: ContentRegion,
    design_dna: DesignDNA,
    slide_no: int,
) -> ImagePlacementResult:
    """
    Inserts a native PowerPoint picture object into the approved region.
    Preserves editability, applies DesignDNA styling, and tracks provenance.
    """
    result = ImagePlacementResult(
        slide_no=slide_no,
        region_id=region.region_id,
        crop_mode_applied=decision.crop_mode,
    )

    if not image_bytes:
        result.defects.append("No image bytes provided")
        return result

    try:
        # Convert region bounds to EMU
        left_in = float(getattr(bounds, "left_in", getattr(bounds, "left", 0.5)))
        top_in = float(getattr(bounds, "top_in", getattr(bounds, "top", 0.5)))
        width_in = float(getattr(bounds, "width_in", getattr(bounds, "width", 7.0)))
        height_in = float(getattr(bounds, "height_in", getattr(bounds, "height", 5.0)))

        region_left = Inches(left_in)
        region_top = Inches(top_in)
        region_width = Inches(width_in)
        region_height = Inches(height_in)

        # Get image dimensions
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(image_bytes))
        img_w, img_h = img.size

        # Apply crop mode
        if decision.crop_mode == CropMode.CONTAIN:
            fit_left, fit_top, fit_width, fit_height = calculate_contain_geometry(
                img_w, img_h,
                region_left, region_top, region_width, region_height,
            )
            # Add picture at calculated position
            pic = slide.shapes.add_picture(
                io.BytesIO(image_bytes),
                fit_left, fit_top, fit_width, fit_height,
            )

        elif decision.crop_mode in {CropMode.COVER, CropMode.BACKGROUND_CROP, CropMode.SMART_CROP}:
            # Place at full region, apply PPTX-level cropping
            pic_left, pic_top, pic_width, pic_height, crop_offsets = calculate_cover_geometry(
                img_w, img_h,
                region_left, region_top, region_width, region_height,
            )
            pic = slide.shapes.add_picture(
                io.BytesIO(image_bytes),
                pic_left, pic_top, pic_width, pic_height,
            )
            # Apply crop offsets via OOXML
            if crop_offsets:
                _apply_pptx_crop(pic, crop_offsets)

        else:  # NO_CROP
            pic = slide.shapes.add_picture(
                io.BytesIO(image_bytes),
                region_left, region_top, region_width, region_height,
            )

        # Set shape name for traceability
        shape_name = f"TG:S{slide_no}:R{region.region_id}:img"
        pic.name = shape_name

        # Set alt text
        alt = decision.alt_text or generate_alt_text(
            decision.image_type, decision.search_query,
            decision.provenance.rights_metadata.creator if decision.provenance else "",
            "",
        )
        if alt and alt != "ALT_TEXT_REVIEW_REQUIRED":
            _set_alt_text(pic, alt)

        # Apply DesignDNA image treatment
        _apply_design_treatment(pic, design_dna)

        result.success = True
        result.picture_shape_id = pic.shape_id
        result.picture_shape_name = shape_name
        result.image_left_emu = int(pic.left)
        result.image_top_emu = int(pic.top)
        result.image_width_emu = int(pic.width)
        result.image_height_emu = int(pic.height)
        result.alt_text = alt

        # Attribution placement where required
        rights = decision.provenance.rights_metadata if decision.provenance else None
        if rights and rights.attribution_requirement and rights.attribution_text:
            cap_h_emu = Inches(0.25)
            cap_top_emu = int(pic.top) + int(pic.height) + Inches(0.04)
            cap_box = slide.shapes.add_textbox(int(pic.left), cap_top_emu, int(pic.width), cap_h_emu)
            cap_name = f"TG:S{slide_no}:R{region.region_id}:caption"
            cap_box.name = cap_name
            tf = cap_box.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = rights.attribution_text
            p.font.size = Pt(8.0)
            p.font.italic = True
            try:
                border_hex = "888888"
                if design_dna and hasattr(design_dna, "color_palette") and hasattr(design_dna.color_palette, "text_secondary"):
                    border_hex = design_dna.color_palette.text_secondary.lstrip("#")
                if len(border_hex) == 6:
                    p.font.color.rgb = RGBColor(int(border_hex[:2], 16), int(border_hex[2:4], 16), int(border_hex[4:], 16))
            except Exception:
                pass
            result.attribution_shape_id = cap_box.shape_id
            result.attribution_shape_name = cap_name

        logger.info(
            f"[ImageComposition] Placed image in S{slide_no}:R{region.region_id} "
            f"({decision.crop_mode.value}) shape_id={pic.shape_id}"
        )

    except Exception as e:
        result.defects.append(f"Image insertion failed: {str(e)[:200]}")
        logger.warning(f"[ImageComposition] Failed to insert image: {e}")

    return result


# ═══════════════════════════════════════════════════════════════
# 4. OOXML CROP & STYLE HELPERS
# ═══════════════════════════════════════════════════════════════

def _apply_pptx_crop(pic_shape, crop_offsets: Dict[str, float]) -> None:
    """Applies PPTX-level crop offsets to a picture shape via OOXML."""
    try:
        blipFill = pic_shape._element.find(
            './/{http://schemas.openxmlformats.org/drawingml/2006/main}blipFill'
        )
        if blipFill is not None:
            srcRect = blipFill.find(
                '{http://schemas.openxmlformats.org/drawingml/2006/main}srcRect'
            )
            if srcRect is None:
                nsmap = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                srcRect = etree.SubElement(
                    blipFill,
                    '{http://schemas.openxmlformats.org/drawingml/2006/main}srcRect'
                )

            # Crop values in OOXML are in 1/1000ths of a percent
            for side in ["left", "top", "right", "bottom"]:
                if side in crop_offsets:
                    val = int(crop_offsets[side] * 100000)  # convert fraction to 1/1000th %
                    srcRect.set(side[0], str(val))  # 'l', 't', 'r', 'b'
    except Exception as e:
        logger.warning(f"[ImageComposition] Crop offset application failed: {e}")


def _set_alt_text(pic_shape, alt_text: str) -> None:
    """Sets accessible alt text on a picture shape."""
    try:
        nvSpPr = pic_shape._element.find(
            './/{http://schemas.openxmlformats.org/presentationml/2006/main}nvPicPr'
        )
        if nvSpPr is None:
            # Try direct path
            nvSpPr = pic_shape._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}nvPicPr')
        
        if nvSpPr is not None:
            cNvPr = nvSpPr.find('{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr')
            if cNvPr is None:
                cNvPr = nvSpPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}cNvPr')
            if cNvPr is not None:
                cNvPr.set('descr', alt_text)
    except Exception:
        pass  # Alt text is best-effort; don't fail the image insertion


def _apply_design_treatment(pic_shape, design_dna: DesignDNA) -> None:
    """
    Applies DesignDNA image treatment (border, corner radius) to picture shape.
    Does not apply destructive filters or recoloring that would alter factual content.
    """
    treatment = design_dna.image_treatment

    if treatment == "bordered":
        _apply_border(pic_shape, design_dna)
    # rounded_corners and masked treatments require OOXML geometry manipulation
    # which is applied only as non-destructive visual styling
    elif treatment == "rounded_corners":
        _apply_rounded_corners(pic_shape, design_dna)


def _apply_border(pic_shape, design_dna: DesignDNA) -> None:
    """Applies a thin border to picture shape using DesignDNA border color."""
    try:
        spPr = pic_shape._element.find(
            './/{http://schemas.openxmlformats.org/drawingml/2006/main}spPr'
        )
        if spPr is not None:
            nsmap = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            ln = etree.SubElement(spPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}ln')
            ln.set('w', '12700')  # 1pt border
            solidFill = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
            srgb = etree.SubElement(solidFill, '{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
            border_hex = design_dna.color_palette.border.lstrip("#")
            srgb.set('val', border_hex)
    except Exception:
        pass


def _apply_rounded_corners(pic_shape, design_dna: DesignDNA) -> None:
    """Applies rounded corners via OOXML geometry preset."""
    try:
        spPr = pic_shape._element.find(
            './/{http://schemas.openxmlformats.org/drawingml/2006/main}spPr'
        )
        if spPr is not None:
            # Set geometry to roundRect with appropriate radius
            prstGeom = spPr.find(
                '{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom'
            )
            if prstGeom is not None:
                prstGeom.set('prst', 'roundRect')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# 5. ASSET MANIFEST
# ═══════════════════════════════════════════════════════════════

class DeckImageManifest(BaseModel):
    """Authoritative asset manifest for all images placed in a deck."""
    deck_topic: str = ""
    total_images: int = 0
    total_image_bytes: int = 0
    image_placements: List[ImageProvenance] = Field(default_factory=list)
    used_content_hashes: List[str] = Field(default_factory=list)
    used_asset_ids: List[str] = Field(default_factory=list)
    used_source_urls: List[str] = Field(default_factory=list)
    provider_usage: Dict[str, int] = Field(default_factory=dict)
    defects_encountered: List[str] = Field(default_factory=list)
    unresolved_image_regions: List[str] = Field(default_factory=list)

    def register_placement(self, provenance: ImageProvenance) -> None:
        """Register an image placement in the manifest."""
        self.image_placements.append(provenance)
        self.total_images += 1
        self.total_image_bytes += provenance.file_size_bytes
        if provenance.downloaded_asset_hash:
            self.used_content_hashes.append(provenance.downloaded_asset_hash)
        if provenance.asset_identifier:
            self.used_asset_ids.append(provenance.asset_identifier)
        if provenance.rights_metadata.original_source_url:
            self.used_source_urls.append(provenance.rights_metadata.original_source_url)
        provider = provenance.rights_metadata.provider
        self.provider_usage[provider] = self.provider_usage.get(provider, 0) + 1
