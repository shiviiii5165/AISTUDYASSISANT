"""
LearnByGenie Artifact Certification — Notation QA
================================================
Audits mathematical and chemical notation in the rendered artifact.
Triangulates between:
- DOM structure (ensuring semantic tags like <sup>, <sub>, .fraction are applied)
- Extracted PDF text (verifying key symbols and species exist without corruption)
- Font glyph health (verifying Greek letters and scientific symbols)
"""
import re
from typing import List, Dict, Any, Tuple
from .schemas import RenderingDefect, RenderingDefectType


class NotationQACertifier:
    """Verifies that mathematical and chemical notation is properly typeset."""

    REQUIRED_CHEMISTRY_SPECIES = [
        ("H2O", ["H2O", "H₂O", "H<sub>2</sub>O"]),
        ("NH3", ["NH3", "NH₃", "NH<sub>3</sub>"]),
        ("SO4^2-", ["SO4", "SO₄", "SO<sub>4</sub>"]),
        ("SF6", ["SF6", "SF₆", "SF<sub>6</sub>"]),
        ("Na+", ["Na+", "Na⁺", "Na<sup>+</sup>"]),
        ("Cl-", ["Cl-", "Cl⁻", "Cl<sup>−</sup>"]),
    ]

    REQUIRED_HYBRIDIZATIONS = [
        ("sp3", ["sp3", "sp³", "sp<sup>3</sup>"]),
        ("sp2", ["sp2", "sp²", "sp<sup>2</sup>"]),
        ("sp", ["sp"]),
    ]

    @classmethod
    def audit_notation(
        cls,
        dom_html: str,
        extracted_pdf_text: str,
        topic: str
    ) -> Tuple[List[RenderingDefect], Dict[str, Any]]:
        """Audits notation quality across DOM structure and extracted PDF text."""
        defects: List[RenderingDefect] = []
        details: Dict[str, Any] = {
            "verified_species": [],
            "verified_hybridizations": [],
            "verified_equations": []
        }

        # 1. Chemical Species Verification (for chemistry topics)
        is_chem = any(k in topic.lower() for k in ["chemical", "bonding", "molecule", "reaction", "acid", "chemistry"])
        if is_chem:
            for spec_name, variants in cls.REQUIRED_CHEMISTRY_SPECIES:
                # Check if species appears in topic or content
                if any(v.lower() in dom_html.lower() for v in variants):
                    details["verified_species"].append(spec_name)

            for hyb_name, variants in cls.REQUIRED_HYBRIDIZATIONS:
                if any(v.lower() in dom_html.lower() for v in variants):
                    details["verified_hybridizations"].append(hyb_name)

        # 2. Equation Formatting Check
        # If "bond order" is discussed, ensure fraction structure exists in DOM
        if "bond order" in dom_html.lower():
            has_fraction = "fraction" in dom_html or "num" in dom_html or "/" in dom_html or "Nb" in dom_html
            if has_fraction:
                details["verified_equations"].append("Bond Order Equation")
            else:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.MATH_RENDER_FAILURE,
                    message="Bond Order formula discussed but lacks proper fraction typesetting.",
                    severity="error"
                ))

        # 3. Glyphs and Greek Symbol Verification
        # Check for tofu / replacement characters
        for bad_glyph in ["\ufffd", "□"]:
            if bad_glyph in extracted_pdf_text or bad_glyph in dom_html:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.MISSING_GLYPH,
                    message=f"Missing font glyph / replacement character '{bad_glyph}' detected in rendered artifact.",
                    severity="critical"
                ))

        # Scientific glyph audit: σ, π, Δ, ±, ≤, ≥, ⁺, ⁻, ², ³, ₄
        tested_glyphs = ["σ", "π", "Δ", "±", "≤", "≥", "⁺", "⁻", "²", "³", "₄"]
        glyph_equivs = {
            "²": ["²", "<sup>2</sup>", "&sup2;"],
            "³": ["³", "<sup>3</sup>", "&sup3;"],
            "⁺": ["⁺", "<sup>+</sup>"],
            "⁻": ["⁻", "<sup>−</sup>", "<sup>-</sup>"],
            "₄": ["₄", "<sub>4</sub>"],
        }
        details["supported_glyphs"] = [
            g for g in tested_glyphs
            if any(eq in dom_html or eq in extracted_pdf_text for eq in glyph_equivs.get(g, [g]))
        ]

        if "sigma" in dom_html.lower() or "\\sigma" in dom_html.lower():
            if "σ" in dom_html or "σ" in extracted_pdf_text or "sigma" in extracted_pdf_text.lower():
                details["verified_equations"].append("Sigma (σ) Bond Symbol")

        if "pi bond" in dom_html.lower() or "\\pi" in dom_html.lower():
            if "π" in dom_html or "π" in extracted_pdf_text or "pi" in extracted_pdf_text.lower():
                details["verified_equations"].append("Pi (π) Bond Symbol")

        return defects, details

    @classmethod
    def audit_document_notation(cls, doc: Any) -> List[RenderingDefect]:
        """Audits document text directly for unrendered notation."""
        sections = getattr(doc, "sections", [])
        all_text = " ".join([f"{getattr(s, 'title', '')} {getattr(s, 'content', '')}" for s in sections])
        topic = getattr(doc, "topic", "") or getattr(doc, "title", "")
        defects, _ = cls.audit_notation(dom_html=all_text, extracted_pdf_text=all_text, topic=topic)

        # Check for unrendered species directly in raw text
        for raw_spec in ["H2O", "NH3", "SO4^2-", "SF6"]:
            if raw_spec in all_text and "<sub>" not in all_text and "₂" not in all_text and "₃" not in all_text:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.CHEMICAL_FORMULA_UNRENDERED,
                    message=f"Raw unrendered chemical formula '{raw_spec}' found in note content.",
                    severity="error"
                ))
        for raw_hyb in ["sp3", "sp2", "sp3d"]:
            if raw_hyb in all_text and "<sup>" not in all_text and "³" not in all_text and "²" not in all_text:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.HYBRIDIZATION_UNRENDERED,
                    message=f"Raw unrendered hybridization '{raw_hyb}' found in note content.",
                    severity="error"
                ))
        return defects
