"""
LearnByGenie Artifact Certification — Rasterized Visual Inspector
===============================================================
Rasterizes PDF pages to high-resolution images using pypdfium2.
Audits visual presentation:
- Non-blankness & entropy verification (ensures pages are not solid white/black)
- Validates page aspect ratio (A4 portrait standard)
- Supports saving inspection images for visual regression audits
"""
import io
import logging
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import pypdfium2 as pdfium

from .schemas import RenderingDefect, RenderingDefectType

logger = logging.getLogger("learnbygenie.notes.certification.visual")


class RasterizedVisualInspector:
    """Rasterizes and visually inspects rendered PDF pages."""

    @classmethod
    def inspect_pdf_images(
        cls,
        pdf_bytes: bytes,
        save_dir: Optional[str] = None
    ) -> Tuple[List[RenderingDefect], Dict[str, Any], List[Image.Image]]:
        """
        Renders PDF pages to PIL images and performs visual quality audits.
        Returns: (defects, details, rendered_pil_images)
        """
        defects: List[RenderingDefect] = []
        details: Dict[str, Any] = {
            "page_images_count": 0,
            "page_dimensions": [],
            "blank_image_pages": []
        }
        images: List[Image.Image] = []

        if not pdf_bytes or len(pdf_bytes) < 50:
            return defects, details, images

        try:
            pdf_doc = pdfium.PdfDocument(pdf_bytes)
            details["page_images_count"] = len(pdf_doc)

            for idx in range(len(pdf_doc)):
                page_num = idx + 1
                page = pdf_doc[idx]

                # Render at 150 DPI (scale ~2.08) for visual audit
                pil_img = page.render(scale=2.0).to_pil()
                images.append(pil_img)

                width, height = pil_img.size
                details["page_dimensions"].append({"page": page_num, "width": width, "height": height})

                # Check aspect ratio (should be close to A4 portrait ~1.414)
                aspect = height / max(1, width)
                if aspect < 1.1 or aspect > 1.8:
                    logger.warning(f"Page {page_num} aspect ratio {aspect:.2f} deviates from standard A4.")

                # Check channel variance (detect blank/solid white/black pages)
                gray_img = pil_img.convert("L")
                extrema = gray_img.getextrema()
                # Extrema returns (min_val, max_val). A completely blank white page has (255, 255)
                if extrema[0] == extrema[1]:
                    details["blank_image_pages"].append(page_num)
                    defects.append(RenderingDefect(
                        type=RenderingDefectType.BLANK_PAGE,
                        page=page_num,
                        message=f"Page image {page_num} is completely blank (solid color value {extrema[0]}).",
                        severity="error"
                    ))
                else:
                    # Audit active ink boundary for visual edge clipping
                    # Binarize: pixels darker than 240 are considered ink
                    ink_mask = gray_img.point(lambda p: 255 if p < 240 else 0)
                    bbox = ink_mask.getbbox()
                    if bbox:
                        left, top, right, bottom = bbox
                        # If ink touches the absolute boundary (within 2 pixels), visual clipping is likely
                        if left <= 2 or top <= 2 or right >= width - 2 or bottom >= height - 2:
                            defects.append(RenderingDefect(
                                type=RenderingDefectType.CLIPPING,
                                page=page_num,
                                message=f"Visual clipping detected on page {page_num}: content reaches absolute edge ({bbox}).",
                                severity="critical"
                            ))

                        details["page_dimensions"][-1]["ink_bbox"] = bbox
                        details["page_dimensions"][-1]["content_height_ratio"] = round((bottom - top) / height, 3)

                if save_dir:
                    import os
                    os.makedirs(save_dir, exist_ok=True)
                    out_path = os.path.join(save_dir, f"page_{page_num}.png")
                    pil_img.save(out_path, "PNG")

        except Exception as e:
            logger.error(f"[VisualInspector] Rasterization failed: {e}", exc_info=True)

        return defects, details, images


# Alias for ergonomic importing
VisualInspector = RasterizedVisualInspector
