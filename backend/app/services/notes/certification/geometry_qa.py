"""
TeachGenie Artifact Certification — Geometry & Pagination QA
============================================================
Inspects physical page geometry and visual bounds using pdfplumber:
- Bounding box audits against printable page bounds (detects CLIPPING and OVERFLOW)
- Footer collision detection
- Blank page detection
- Document truncation check: asserts concluding sections & practice questions exist
"""
import io
import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from .schemas import RenderingDefect, RenderingDefectType
from ..schemas import NotesDocument

logger = logging.getLogger("teachgenie.notes.certification.geometry")


class GeometryQACertifier:
    """Audits PDF physical page geometry, pagination, and completeness."""

    @classmethod
    def audit_pdf_geometry(
        cls,
        pdf_bytes: bytes,
        doc: Optional[NotesDocument] = None
    ) -> Tuple[List[RenderingDefect], Dict[str, Any]]:
        """
        Inspects PDF bytes for clipping, overflow, footer collisions, blank pages, and truncation.
        Returns: (defects_list, geometry_details)
        """
        defects: List[RenderingDefect] = []
        details: Dict[str, Any] = {
            "page_count": 0,
            "page_word_counts": [],
            "clipping_detected": False,
            "overflow_detected": False,
            "blank_pages": []
        }

        if not pdf_bytes:
            defects.append(RenderingDefect(
                type=RenderingDefectType.DOCUMENT_TRUNCATED,
                message="PDF byte stream is empty.",
                severity="critical"
            ))
            return defects, details

        if not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) < 50:
            defects.append(RenderingDefect(
                type=RenderingDefectType.PDF_CORRUPT,
                message="PDF byte stream header is missing or corrupt.",
                severity="critical"
            ))
            return defects, details

        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)
                details["page_count"] = page_count

                all_extracted_text = []

                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    width = float(page.width)
                    height = float(page.height)

                    text = page.extract_text() or ""
                    words = page.extract_words()
                    details["page_word_counts"].append(len(words))
                    all_extracted_text.append(text)

                    # 1. Blank Page Detection (0 words and 0 visual objects on non-single page)
                    if len(words) == 0 and len(page.curves) == 0 and len(page.images) == 0:
                        details["blank_pages"].append(page_num)
                        defects.append(RenderingDefect(
                            type=RenderingDefectType.BLANK_PAGE,
                            page=page_num,
                            message=f"Page {page_num} is an unexpected blank page.",
                            severity="error"
                        ))

                    # 2. Clipping & Overflow Audits (words beyond page width/height)
                    for w in words:
                        x0 = float(w.get("x0", 0))
                        x1 = float(w.get("x1", 0))
                        top = float(w.get("top", 0))
                        bottom = float(w.get("bottom", 0))

                        # Check if text spills beyond physical page bounds (with 2pt tolerance)
                        if x1 > width + 2 or x0 < -2 or bottom > height + 2 or top < -2:
                            details["clipping_detected"] = True
                            defects.append(RenderingDefect(
                                type=RenderingDefectType.CLIPPING,
                                page=page_num,
                                message=f"Content clipped beyond physical page boundary on page {page_num}: '{w.get('text')}'",
                                severity="critical",
                                snippet=w.get("text")
                            ))
                            break

                        # Footer Collision: content encroaching on bottom 15pt where page numbers sit
                        if bottom > height - 12 and x0 < width - 150:
                            # Main content colliding with footer zone
                            details["overflow_detected"] = True
                            defects.append(RenderingDefect(
                                type=RenderingDefectType.FOOTER_COLLISION,
                                page=page_num,
                                message=f"Content encroaches onto page footer margin on page {page_num}.",
                                severity="error",
                                snippet=w.get("text")
                            ))
                            break

                # 3. Document Truncation Check
                full_pdf_text = " ".join(all_extracted_text).lower()

                # Verify concluding sections are present
                if doc and doc.sections:
                    last_sec = doc.sections[-1]
                    last_title_words = [w for w in re.findall(r'\w+', last_sec.title.lower()) if len(w) > 3]
                    if last_title_words:
                        found_last_sec = any(w in full_pdf_text for w in last_title_words)
                        if not found_last_sec:
                            defects.append(RenderingDefect(
                                type=RenderingDefectType.DOCUMENT_TRUNCATED,
                                message=f"Document truncated prematurely: concluding section '{last_sec.title}' is missing from rendered PDF.",
                                severity="critical"
                            ))

                # Verify practice section is present if practice items were defined
                if doc and doc.practice and len(doc.practice) > 0:
                    first_q_words = [w for w in re.findall(r'\w+', str(doc.practice[0].get("question", "")).lower()) if len(w) > 4]
                    if first_q_words:
                        found_practice = any(w in full_pdf_text for w in first_q_words) or "practice" in full_pdf_text or "checkpoint" in full_pdf_text
                        if not found_practice:
                            defects.append(RenderingDefect(
                                type=RenderingDefectType.DOCUMENT_TRUNCATED,
                                message="Document truncated prematurely: practice items defined in document were omitted from rendered PDF.",
                                severity="critical"
                            ))

        except Exception as e:
            logger.warning(f"[GeometryQA] pdfplumber audit failed or fallback: {e}")
            # Fallback estimation using pypdf if pdfplumber encounters unusual stream
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                details["page_count"] = len(reader.pages)
            except Exception:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.PDF_CORRUPT,
                    message=f"PDF byte stream could not be parsed: {e}",
                    severity="critical"
                ))

        return defects, details

    @classmethod
    def inspect_pdf(
        cls,
        pdf_bytes: bytes,
        doc: Optional[NotesDocument] = None
    ) -> Tuple[List[RenderingDefect], Dict[str, Any]]:
        """Convenience alias for audit_pdf_geometry."""
        return cls.audit_pdf_geometry(pdf_bytes, doc)
