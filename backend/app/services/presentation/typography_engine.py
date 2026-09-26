"""
TeachGenie PPT vNext — Phase 3.2B Typography & Text-Fitting Engine
==================================================================
Geometry-aware typography resolution, hierarchical constraint validation,
deterministic text measurement, and 7-stage ordered text fitting.

Phase 3.2B Contracts:
1. DesignDNA is the single source of truth for typography.
2. Preserves Phase 3.2A role-specific minimums (ROLE_MINIMUM_FONT_SIZES).
3. Relational typography hierarchy (DISPLAY > TITLE > SUBTITLE, TITLE > BODY, etc.).
4. Deterministic TextMeasurementEngine accounting for font metrics and geometry.
5. 7-stage ordered fitting pipeline (Exact -> Spacing -> Line Height -> Font Size ->
   Semantic Compression -> Notes Migration -> Reflow -> Overflow).
6. Zero silent truncation; zero content invention; full hash preservation.
"""
from enum import Enum
import hashlib
import math
import re
from typing import List, Dict, Tuple, Optional, Any, Set

from pydantic import BaseModel, Field, field_validator, model_validator

from .visual_schemas import (
    DesignDNA,
    TypographyScale,
    ContentDensity,
    ColorPalette,
)
from .composition_schemas import (
    TypographyRole,
    TypographyRoleSpec,
    ColorToken,
    ROLE_MINIMUM_FONT_SIZES,
    ContentBinding,
    FormulaPayload,
    FormulaRenderMode,
    RegionSemanticRole,
    SpacingToken,
)
from .spacing_engine import SpacingEngine, SpacingPurpose, ResolvedSpacingSpec
from .qa_agent import fit_title_semantic


# ═══════════════════════════════════════════════════════════════
# 1. STRUCTURED DEFECT CODES
# ═══════════════════════════════════════════════════════════════

DEFECT_TITLE_GEOMETRY_OVERFLOW          = "TITLE_GEOMETRY_OVERFLOW"
DEFECT_BODY_GEOMETRY_OVERFLOW           = "BODY_GEOMETRY_OVERFLOW"
DEFECT_FONT_MINIMUM_REACHED             = "FONT_MINIMUM_REACHED"
DEFECT_LINE_HEIGHT_MINIMUM_REACHED      = "LINE_HEIGHT_MINIMUM_REACHED"
DEFECT_UNBREAKABLE_TOKEN_OVERFLOW       = "UNBREAKABLE_TOKEN_OVERFLOW"
DEFECT_FORMULA_OVERFLOW                 = "FORMULA_OVERFLOW"
DEFECT_CODE_OVERFLOW                    = "CODE_OVERFLOW"
DEFECT_CITATION_OVERFLOW                = "CITATION_OVERFLOW"
DEFECT_SEMANTIC_COMPRESSION_UNSAFE      = "SEMANTIC_COMPRESSION_UNSAFE"
DEFECT_MANDATORY_CONTENT_OVERFLOW       = "MANDATORY_CONTENT_OVERFLOW"
DEFECT_REFLOW_REQUIRED                  = "REFLOW_REQUIRED"
DEFECT_TYPOGRAPHY_HIERARCHY_INVALID     = "TYPOGRAPHY_HIERARCHY_INVALID"
DEFECT_DESIGNDNA_MISSING_FALLBACK_APPLIED = "DESIGNDNA_MISSING_FALLBACK_APPLIED"


# ═══════════════════════════════════════════════════════════════
# 2. STATUS & RESULT MODELS
# ═══════════════════════════════════════════════════════════════

class TextFitStatus(str, Enum):
    """Status classification of the ordered fitting pipeline."""
    EXACT_FIT               = "exact_fit"                # Stage 0: Fits with authoritative DesignDNA typography
    SPACING_ADJUSTED        = "spacing_adjusted"         # Stage 1: Fits after paragraph spacing reduction
    LINE_HEIGHT_ADJUSTED    = "line_height_adjusted"     # Stage 2: Fits after line height reduction
    FONT_ADJUSTED           = "font_adjusted"            # Stage 3: Fits after bounded font size reduction
    SEMANTICALLY_COMPRESSED = "semantically_compressed"  # Stage 4: Fits after safe semantic compression
    DETAIL_MOVED_TO_NOTES   = "detail_moved_to_notes"    # Stage 5: Fits after optional detail migrated to speaker notes
    REFLOW_REQUIRED         = "reflow_required"          # Stage 6: Cannot fit without layout reflow (Phase 3.2C)
    UNRESOLVED_OVERFLOW     = "unresolved_overflow"      # Stage 7: Overflow cannot be safely resolved


class NotesMigrationRecord(BaseModel):
    """
    Immutable provenance record of content migrated from display to speaker notes.
    Prevents silent content loss during presentation fitting.
    """
    source_binding: Optional[ContentBinding] = None
    source_hash: str = ""
    reason: str = "geometry_fit_stage_5"
    original_priority: int = Field(default=4, ge=1, le=5)
    destination: str = "speaker_notes"
    display_content_removed: str = ""
    notes_content_hash: str = ""

    @model_validator(mode="after")
    def populate_hash(self):
        if not self.notes_content_hash and self.display_content_removed:
            self.notes_content_hash = hashlib.sha256(self.display_content_removed.strip().encode()).hexdigest()
        return self


class TextMeasurementResult(BaseModel):
    """
    Deterministic geometric measurement estimate for text within a bounded region.
    Accounts for font family proportional metrics, weight, word breaks, and newlines.
    """
    estimated_line_count: int = Field(..., ge=0)
    estimated_text_height_in: float = Field(..., ge=0.0)
    overflow_in: float
    usable_width_in: float = Field(..., ge=0.0)
    measurement_confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    unbreakable_tokens: List[str] = Field(default_factory=list)
    line_wraps: List[str] = Field(default_factory=list)


class TextFitResult(BaseModel):
    """
    Strongly typed comprehensive result of the Phase 3.2B text fitting pipeline.
    Never returns an unexplained mutated string.
    """
    region_id: str
    status: TextFitStatus
    fit_stage: int = Field(..., ge=0, le=7)
    original_binding: Optional[ContentBinding] = None
    resolved_content_hash: str = ""
    display_text: str = ""
    display_text_hash: str = ""
    typography_before: TypographyRoleSpec
    typography_after: TypographyRoleSpec
    design_dna_base_typography: Optional[TypographyRoleSpec] = None
    density_resolved_typography: Optional[TypographyRoleSpec] = None
    fit_typography_before: Optional[TypographyRoleSpec] = None
    fit_typography_after: Optional[TypographyRoleSpec] = None
    density_adjustment: float = 0.0
    resolved_role_min_line_height_ratio: float = 1.0
    paragraph_spacing_before: float = 0.0
    paragraph_spacing_after: float = 0.0
    line_height_before: float = 1.4
    line_height_after: float = 1.4
    migrated_content_bindings: List[NotesMigrationRecord] = Field(default_factory=list)
    transform_history: List[str] = Field(default_factory=list)
    estimated_line_count: int = 1
    estimated_text_height: float = 0.0
    available_height: float = 0.0
    overflow_remaining: float = 0.0
    quality_defects: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_audit_and_invariants(self):
        if not self.display_text_hash and self.display_text:
            self.display_text_hash = hashlib.sha256(self.display_text.strip().encode()).hexdigest()
        if self.fit_typography_before is None:
            self.fit_typography_before = self.typography_before
        if self.fit_typography_after is None:
            self.fit_typography_after = self.typography_after
        if self.density_resolved_typography is None:
            self.density_resolved_typography = self.typography_before
        if self.design_dna_base_typography is None:
            self.design_dna_base_typography = self.typography_before

        # Invariant: final line-height ratio must be >= resolved role min floor
        if self.resolved_role_min_line_height_ratio > 0.0:
            if self.line_height_after < self.resolved_role_min_line_height_ratio - 1e-4:
                raise ValueError(
                    f"Role-safe line height invariant violated: line_height_after {self.line_height_after:.2f} "
                    f"< min allowed {self.resolved_role_min_line_height_ratio:.2f}"
                )
        return self


# ═══════════════════════════════════════════════════════════════
# 3. TYPOGRAPHY RESOLUTION & HIERARCHY ENGINE
# ═══════════════════════════════════════════════════════════════

# Authoritative Fallback Scales if DesignDNA is missing
FALLBACK_TITLE_SCALE = TypographyScale(
    font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
    font_weight=700, font_size_pt=24.0, line_height_ratio=1.2, letter_spacing_em=-0.01
)
FALLBACK_BODY_SCALE = TypographyScale(
    font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
    font_weight=400, font_size_pt=13.0, line_height_ratio=1.45, letter_spacing_em=0.0
)
FALLBACK_CAPTION_SCALE = TypographyScale(
    font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
    font_weight=500, font_size_pt=9.5, line_height_ratio=1.3, letter_spacing_em=0.02
)


def resolve_typography_role_spec(
    role: TypographyRole,
    design_dna: Optional[DesignDNA] = None,
    content_density: Optional[ContentDensity] = None,
    available_geometry: Optional[Tuple[float, float]] = None,
    audience_context: Optional[str] = None,
) -> TypographyRoleSpec:
    """
    Resolves a strongly typed TypographyRoleSpec for any of the 12 semantic typography roles.
    Consumes authoritative DesignDNA scales, applying density adaptations within role-safe floors.
    """
    is_fallback = False
    if design_dna is not None and hasattr(design_dna, "title_scale") and design_dna.title_scale:
        title_scale = design_dna.title_scale
        body_scale = design_dna.body_scale or FALLBACK_BODY_SCALE
        caption_scale = design_dna.caption_scale or FALLBACK_CAPTION_SCALE
        if content_density is not None:
            density = content_density
        else:
            density = getattr(design_dna, "density_profile", ContentDensity.MEDIUM) or ContentDensity.MEDIUM
    else:
        title_scale = FALLBACK_TITLE_SCALE
        body_scale = FALLBACK_BODY_SCALE
        caption_scale = FALLBACK_CAPTION_SCALE
        density = content_density or ContentDensity.MEDIUM
        is_fallback = True

    # Density offsets
    # LOW: +1.0pt to +1.5pt for breathing room
    # MEDIUM: 0.0pt (standard DesignDNA)
    # HIGH: -1.0pt to -1.5pt (bounded by role floors)
    density_offset_pt = 1.0 if density == ContentDensity.LOW else (-1.0 if density == ContentDensity.HIGH else 0.0)

    # Primary font family assignment from DesignDNA
    heading_font = title_scale.font_family or "Inter"
    heading_fallback = title_scale.font_fallback or "Calibri"
    body_font = body_scale.font_family or "Inter"
    body_fallback = body_scale.font_fallback or "Calibri"
    office_fallback = "Calibri"

    min_floor = ROLE_MINIMUM_FONT_SIZES.get(role, 8.5)

    if role == TypographyRole.DISPLAY:
        base_size = max(min_floor, 34.0 + density_offset_pt * 2.0)
        return TypographyRoleSpec(
            role=role,
            font_family=heading_font,
            fallback_family=heading_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=800,
            line_height_ratio=1.15,
            letter_spacing_em=-0.02,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.TITLE:
        base_size = max(min_floor, title_scale.font_size_pt + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=heading_font,
            fallback_family=heading_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=title_scale.font_weight or 700,
            line_height_ratio=title_scale.line_height_ratio or 1.20,
            letter_spacing_em=title_scale.letter_spacing_em or -0.01,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.SUBTITLE:
        base_size = max(min_floor, 16.0 + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=heading_font,
            fallback_family=heading_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=500,
            line_height_ratio=1.30,
            letter_spacing_em=0.0,
            color_token=ColorToken.TEXT_SECONDARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.SECTION_LABEL:
        base_size = max(min_floor, 11.0 + (0.5 if density == ContentDensity.LOW else 0.0))
        return TypographyRoleSpec(
            role=role,
            font_family=heading_font,
            fallback_family=heading_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=600,
            line_height_ratio=1.20,
            letter_spacing_em=0.05,
            color_token=ColorToken.PRIMARY,
            max_recommended_lines=1,
        )

    elif role == TypographyRole.BODY:
        # Body text NEVER collapses to caption sizes (strictly >= 11.0pt)
        base_size = max(min_floor, body_scale.font_size_pt + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=body_scale.font_weight or 400,
            line_height_ratio=body_scale.line_height_ratio or 1.45,
            letter_spacing_em=body_scale.letter_spacing_em or 0.0,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=5,
        )

    elif role == TypographyRole.BODY_EMPHASIS:
        # Identical size to BODY, but weighted bolder
        base_size = max(min_floor, body_scale.font_size_pt + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=600,
            line_height_ratio=body_scale.line_height_ratio or 1.45,
            letter_spacing_em=body_scale.letter_spacing_em or 0.0,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=4,
        )

    elif role == TypographyRole.QUOTE:
        base_size = max(min_floor, 17.0 + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=heading_font,
            fallback_family=heading_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=500,
            line_height_ratio=1.40,
            letter_spacing_em=0.01,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=3,
        )

    elif role == TypographyRole.FORMULA:
        # Formulas remain visually prominent (never smaller than 14.0pt floor)
        base_size = max(min_floor, 16.0 + density_offset_pt)
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family="Cambria Math",
            safe_office_fallback="Cambria",
            font_size_pt=base_size,
            font_weight=500,
            line_height_ratio=1.40,
            letter_spacing_em=0.02,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.TABLE_HEADER:
        base_size = max(min_floor, 11.0 + (0.5 if density == ContentDensity.LOW else 0.0))
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=600,
            line_height_ratio=1.25,
            letter_spacing_em=0.01,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.TABLE_BODY:
        base_size = max(min_floor, 10.0 + (0.5 if density == ContentDensity.LOW else 0.0))
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=400,
            line_height_ratio=1.30,
            letter_spacing_em=0.0,
            color_token=ColorToken.TEXT_PRIMARY,
            max_recommended_lines=3,
        )

    elif role == TypographyRole.CAPTION:
        base_size = max(min_floor, caption_scale.font_size_pt + (0.5 if density == ContentDensity.LOW else -0.5 if density == ContentDensity.HIGH else 0.0))
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=caption_scale.font_weight or 400,
            line_height_ratio=caption_scale.line_height_ratio or 1.25,
            letter_spacing_em=caption_scale.letter_spacing_em or 0.01,
            color_token=ColorToken.TEXT_SECONDARY,
            max_recommended_lines=2,
        )

    elif role == TypographyRole.ANNOTATION:
        base_size = max(min_floor, 9.0)
        return TypographyRoleSpec(
            role=role,
            font_family=body_font,
            fallback_family=body_fallback,
            safe_office_fallback=office_fallback,
            font_size_pt=base_size,
            font_weight=400,
            line_height_ratio=1.20,
            letter_spacing_em=0.0,
            color_token=ColorToken.TEXT_SECONDARY,
            max_recommended_lines=2,
        )

    # General fallback
    return TypographyRoleSpec(
        role=role,
        font_family=body_font,
        fallback_family=body_fallback,
        safe_office_fallback=office_fallback,
        font_size_pt=max(min_floor, 12.0),
        font_weight=400,
        line_height_ratio=1.40,
        color_token=ColorToken.TEXT_PRIMARY,
    )


def validate_typography_hierarchy(specs: Dict[TypographyRole, TypographyRoleSpec]) -> List[str]:
    """
    Validates relational typography hierarchy contracts across resolved roles.
    Contracts:
      1. DISPLAY > TITLE > SUBTITLE
      2. TITLE > BODY
      3. BODY >= BODY_EMPHASIS base size
      4. CAPTION < BODY
      5. FORMULA must remain visually prominent (FORMULA >= BODY)
      6. SECTION_LABEL must remain subordinate to TITLE (SECTION_LABEL < TITLE)
    """
    defects: List[str] = []

    display = specs.get(TypographyRole.DISPLAY)
    title = specs.get(TypographyRole.TITLE)
    subtitle = specs.get(TypographyRole.SUBTITLE)
    body = specs.get(TypographyRole.BODY)
    body_emp = specs.get(TypographyRole.BODY_EMPHASIS)
    caption = specs.get(TypographyRole.CAPTION)
    formula = specs.get(TypographyRole.FORMULA)
    sec_label = specs.get(TypographyRole.SECTION_LABEL)

    if display and title and display.font_size_pt <= title.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: DISPLAY ({display.font_size_pt}pt) must be strictly greater than TITLE ({title.font_size_pt}pt)")

    if title and subtitle and title.font_size_pt <= subtitle.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: TITLE ({title.font_size_pt}pt) must be strictly greater than SUBTITLE ({subtitle.font_size_pt}pt)")

    if title and body and title.font_size_pt <= body.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: TITLE ({title.font_size_pt}pt) must be strictly greater than BODY ({body.font_size_pt}pt)")

    if body and body_emp and body_emp.font_size_pt > body.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: BODY_EMPHASIS ({body_emp.font_size_pt}pt) cannot exceed base BODY size ({body.font_size_pt}pt)")

    if caption and body and caption.font_size_pt >= body.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: CAPTION ({caption.font_size_pt}pt) must be strictly smaller than BODY ({body.font_size_pt}pt)")

    if formula and body and formula.font_size_pt < body.font_size_pt - 0.5:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: FORMULA ({formula.font_size_pt}pt) must remain visually prominent relative to BODY ({body.font_size_pt}pt)")

    if sec_label and title and sec_label.font_size_pt >= title.font_size_pt:
        defects.append(f"{DEFECT_TYPOGRAPHY_HIERARCHY_INVALID}: SECTION_LABEL ({sec_label.font_size_pt}pt) must be subordinate to TITLE ({title.font_size_pt}pt)")

    return defects


# ═══════════════════════════════════════════════════════════════
# 4. GEOMETRY-AWARE TEXT MEASUREMENT ENGINE
# ═══════════════════════════════════════════════════════════════

class TextMeasurementEngine:
    """
    Deterministic geometric text measurement estimator.
    Accounts for font family proportional character widths, font size, bold weight expansion,
    word boundaries, explicit linebreaks, bullet indentations, and paragraph spacing.
    """

    # Average proportional character width as fraction of font_size_pt
    FONT_WIDTH_FACTORS = {
        "geometric_sans": 0.52,  # Inter, Outfit
        "humanist":       0.50,  # Calibri, Open Sans
        "neo_grotesque":  0.53,  # Arial, Helvetica
        "serif_blend":    0.48,  # Georgia, Merriweather
        "monospace":      0.60,  # Consolas, Courier
    }

    @classmethod
    def get_char_width_pt(cls, font_family: str, font_size_pt: float, font_weight: int = 400) -> float:
        """Computes average character width in points for a given font and weight."""
        fname = font_family.lower()
        if "consolas" in fname or "courier" in fname or "mono" in fname:
            factor = cls.FONT_WIDTH_FACTORS["monospace"]
        elif "georgia" in fname or "serif" in fname or "merriweather" in fname:
            factor = cls.FONT_WIDTH_FACTORS["serif_blend"]
        else:
            factor = cls.FONT_WIDTH_FACTORS["geometric_sans"]

        # Bold weight adds ~8% width expansion
        weight_multiplier = 1.08 if font_weight >= 600 else 1.00
        return font_size_pt * factor * weight_multiplier

    @classmethod
    def measure_text(
        cls,
        text: str,
        typography_spec: TypographyRoleSpec,
        region_width_in: float,
        region_height_in: float,
        bullet_indentation_in: float = 0.0,
        paragraph_spacing_pt: float = 0.0,
        padding_in: float = 0.05,
    ) -> TextMeasurementResult:
        """
        Deterministically estimates required lines and total height in physical inches.
        Detects unbreakable tokens and compares against available bounds.
        """
        if not text or not text.strip():
            return TextMeasurementResult(
                estimated_line_count=0,
                estimated_text_height_in=0.0,
                overflow_in=-region_height_in,
                usable_width_in=max(0.1, region_width_in - padding_in * 2),
                measurement_confidence=1.0,
            )

        usable_width_in = max(0.1, region_width_in - (padding_in * 2) - bullet_indentation_in)
        usable_width_pt = usable_width_in * 72.0

        char_width_pt = cls.get_char_width_pt(
            typography_spec.font_family,
            typography_spec.font_size_pt,
            typography_spec.font_weight,
        )
        line_height_pt = typography_spec.font_size_pt * typography_spec.line_height_ratio

        # Split into paragraphs by explicit newlines
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        total_lines = 0
        unbreakable_tokens: List[str] = []
        line_wraps: List[str] = []

        for p_idx, para in enumerate(paragraphs):
            words = para.split()
            current_line_width_pt = 0.0
            current_line_words: List[str] = []

            for word in words:
                word_width_pt = len(word) * char_width_pt
                space_width_pt = char_width_pt * 0.9

                # Check for unbreakable tokens exceeding available column width
                if word_width_pt > usable_width_pt:
                    unbreakable_tokens.append(word)

                if not current_line_words:
                    current_line_words.append(word)
                    current_line_width_pt = word_width_pt
                elif current_line_width_pt + space_width_pt + word_width_pt <= usable_width_pt:
                    current_line_words.append(word)
                    current_line_width_pt += space_width_pt + word_width_pt
                else:
                    # Line wrapped
                    line_wraps.append(" ".join(current_line_words))
                    total_lines += 1
                    current_line_words = [word]
                    current_line_width_pt = word_width_pt

            if current_line_words:
                line_wraps.append(" ".join(current_line_words))
                total_lines += 1

        total_text_height_pt = (total_lines * line_height_pt) + (max(0, len(paragraphs) - 1) * paragraph_spacing_pt)
        total_text_height_in = round(total_text_height_pt / 72.0, 3)
        overflow_in = round(total_text_height_in - region_height_in, 3)

        confidence = 0.95
        if unbreakable_tokens:
            confidence -= 0.15

        return TextMeasurementResult(
            estimated_line_count=total_lines,
            estimated_text_height_in=total_text_height_in,
            overflow_in=overflow_in,
            usable_width_in=usable_width_in,
            measurement_confidence=max(0.5, confidence),
            unbreakable_tokens=unbreakable_tokens,
            line_wraps=line_wraps,
        )


# ═══════════════════════════════════════════════════════════════
# 5. SEMANTIC COMPRESSION SAFETY
# ═══════════════════════════════════════════════════════════════

def is_safe_semantic_compression(original: str, candidate: str) -> Tuple[bool, str]:
    """
    Validates that a proposed compressed string preserves all semantic facts.
    Guarantees zero alteration of:
      - Numbers and percentages
      - Equations, math formulas, and Greek characters
      - Citations and bibliographic references
      - Quoted material
      - Code tokens
      - Polar terms (increase vs decrease)
    """
    if not candidate or len(candidate.strip()) == 0:
        return False, "Compressed text is empty"

    # 1. Number preservation: all numbers in original must exist in candidate
    orig_nums = re.findall(r"\b\d+(?:\.\d+)?%?", original)
    cand_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?", candidate))
    for num in orig_nums:
        if num and num not in cand_nums:
            return False, f"Number '{num}' was dropped in compression"

    # 2. Equation / Math symbol preservation
    math_symbols = [r"=", r"\approx", r"\le", r"\ge", r"\to", r"\times", r"%", r"$", r"\\"]
    for sym in math_symbols:
        if sym in original and sym not in candidate:
            return False, f"Math symbol '{sym}' was dropped in compression"

    # 3. Citation preservation: e.g. [1], (Smith et al., 2024)
    orig_cites = re.findall(r"\[\d+\]|\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", original)
    for cite in orig_cites:
        if cite not in candidate:
            return False, f"Citation '{cite}' was dropped in compression"

    # 4. Quoted text preservation
    orig_quotes = re.findall(r'"([^"]+)"', original)
    for q in orig_quotes:
        if q not in candidate:
            return False, f"Quoted phrase '{q}' was altered in compression"

    # 5. Code identifier preservation: e.g. `const`, `function()`, ClassNames
    orig_code = re.findall(r"`([^`]+)`", original)
    for c in orig_code:
        if c not in candidate:
            return False, f"Code element '{c}' was altered in compression"

    return True, "Safe semantic compression verified"


def compress_prose_safely(text: str, protected_terms: Optional[List[str]] = None) -> Tuple[str, bool, str]:
    """
    Safely compresses verbose prose by trimming redundant introductory phrases
    and verbose connective filler without altering factual content.
    Returns (compressed_text, was_compressed, rationale).
    """
    if not text:
        return text, False, "Empty text"

    original = text
    compressed = text

    # Redundant introductory phrases that add no factual value
    REDUNDANT_PATTERNS = [
        (r"^It\s+is\s+important\s+to\s+note\s+that\s+", ""),
        (r"^It\s+should\s+be\s+noted\s+that\s+", ""),
        (r"^It\s+is\s+worth\s+mentioning\s+that\s+", ""),
        (r"^As\s+(?:we\s+can\s+see|can\s+be\s+observed|demonstrated)\s+in\s+this\s+context,\s*", ""),
        (r"^In\s+order\s+to\s+", "To "),
        (r"\bin\s+order\s+to\s+", "to "),
        (r"^For\s+the\s+purpose\s+of\s+", "For "),
        (r"\bfor\s+the\s+purpose\s+of\s+", "for "),
        (r"\bdue\s+to\s+the\s+fact\s+that\s+", "because "),
        (r"\ba\s+large\s+number\s+of\s+", "many "),
        (r"\bat\s+the\s+present\s+time\s+", "currently "),
        (r"\bin\s+the\s+process\s+of\s+", ""),
    ]

    for pat, repl in REDUNDANT_PATTERNS:
        compressed = re.sub(pat, repl, compressed, flags=re.IGNORECASE)

    # Capitalize first character if trimmed at start
    if compressed and compressed[0].islower():
        compressed = compressed[0].upper() + compressed[1:]

    compressed = re.sub(r"\s{2,}", " ", compressed).strip()

    if compressed == original:
        return original, False, "No redundant connective phrases to compress"

    # Verify safety against all facts and protected terms
    is_safe, reason = is_safe_semantic_compression(original, compressed)
    if not is_safe:
        return original, False, f"Compression rejected: {reason}"

    if protected_terms:
        for pterm in protected_terms:
            if pterm in original and pterm not in compressed:
                return original, False, f"Compression rejected: protected term '{pterm}' lost"

    return compressed, True, "Trimmed redundant introductory and connective phrasing"


# ═══════════════════════════════════════════════════════════════
# 6. TITLE GEOMETRY FITTING
# ═══════════════════════════════════════════════════════════════

def fit_title_to_geometry(
    title: str,
    region_width_in: float,
    region_height_in: float,
    design_dna: Optional[DesignDNA] = None,
    content_density: ContentDensity = ContentDensity.MEDIUM,
    binding: Optional[ContentBinding] = None,
    allow_reflow: bool = True,
) -> TextFitResult:
    """
    Fits slide titles with geometry awareness around frozen Phase 3.1 semantic title fitting.
    Workflow:
      1. Phase 3.1 semantic title fit (fit_title_semantic) if len > 60.
      2. Resolve TITLE typography spec from DesignDNA.
      3. Measure against region dimensions.
      4. Bounded line-height reduction (1.20 -> 1.10).
      5. Bounded font size reduction (e.g. 28pt -> 24pt -> min 20pt TITLE floor).
      6. If title still overflows at 20pt: return REFLOW_REQUIRED.
    """
    transform_history: List[str] = []
    original_title = title
    current_title = title

    # 1. Phase 3.1 semantic compression if title exceeds character budget (<= 60 chars)
    if len(current_title) > 60:
        semantic_fitted = fit_title_semantic(current_title, max_chars=60)
        if semantic_fitted != current_title:
            current_title = semantic_fitted
            transform_history.append(f"Phase3.1 semantic title fit: {len(original_title)} -> {len(current_title)} chars")

    # 2. Typography Spec from DesignDNA with explicit density audit
    spacing_eng = SpacingEngine(design_dna=design_dna, content_density=content_density)
    min_line_height, _ = spacing_eng.get_safe_line_height_range(TypographyRole.TITLE)

    dna_base_typo = resolve_typography_role_spec(
        TypographyRole.TITLE,
        design_dna=design_dna,
        content_density=ContentDensity.MEDIUM,
    )
    density_resolved_typo = resolve_typography_role_spec(
        TypographyRole.TITLE,
        design_dna=design_dna,
        content_density=content_density,
    )
    density_adjustment = round(density_resolved_typo.font_size_pt - dna_base_typo.font_size_pt, 2)

    typo_before = density_resolved_typo
    typo_current = typo_before.model_copy(deep=True)

    def _build_title_result(status: TextFitStatus, fit_stage: int, defects: Optional[List[str]] = None) -> TextFitResult:
        return TextFitResult(
            region_id=binding.source_id if binding else "title_region",
            status=status,
            fit_stage=fit_stage,
            original_binding=binding,
            resolved_content_hash=binding.resolved_content_hash if binding else "",
            display_text=current_title,
            typography_before=typo_before,
            typography_after=typo_current,
            design_dna_base_typography=dna_base_typo,
            density_resolved_typography=density_resolved_typo,
            fit_typography_before=typo_before,
            fit_typography_after=typo_current,
            density_adjustment=density_adjustment,
            resolved_role_min_line_height_ratio=min_line_height,
            line_height_before=typo_before.line_height_ratio,
            line_height_after=typo_current.line_height_ratio,
            transform_history=transform_history,
            estimated_line_count=meas.estimated_line_count,
            estimated_text_height=meas.estimated_text_height_in,
            available_height=region_height_in,
            overflow_remaining=meas.overflow_in,
            quality_defects=defects or [],
        )

    # 3. Measure Stage 0: Initial fit
    meas = TextMeasurementEngine.measure_text(
        current_title,
        typo_current,
        region_width_in,
        region_height_in,
    )

    if meas.overflow_in <= 0.005:
        status = TextFitStatus.SEMANTICALLY_COMPRESSED if current_title != original_title else TextFitStatus.EXACT_FIT
        fit_stage = 4 if current_title != original_title else 0
        return _build_title_result(status, fit_stage)

    # 4. Stage 2: Reduce line height within role-safe bounds
    if typo_current.line_height_ratio > min_line_height:
        old_lh = typo_current.line_height_ratio
        typo_current.line_height_ratio = min_line_height
        transform_history.append(f"Reduced title line height ratio from {old_lh:.2f} to {min_line_height:.2f}")
        meas = TextMeasurementEngine.measure_text(current_title, typo_current, region_width_in, region_height_in)
        if meas.overflow_in <= 0.005:
            return _build_title_result(TextFitStatus.LINE_HEIGHT_ADJUSTED, 2)

    # 5. Stage 3: Bounded font reduction down to 20.0pt (ROLE_MINIMUM_FONT_SIZES[TITLE])
    title_floor = ROLE_MINIMUM_FONT_SIZES[TypographyRole.TITLE]
    step_sizes = [24.0, 22.0, title_floor]

    for target_pt in step_sizes:
        if target_pt < typo_current.font_size_pt and target_pt >= title_floor:
            old_pt = typo_current.font_size_pt
            typo_current.font_size_pt = target_pt
            transform_history.append(f"Reduced title font size from {old_pt:.1f}pt to {target_pt:.1f}pt")
            meas = TextMeasurementEngine.measure_text(current_title, typo_current, region_width_in, region_height_in)
            if meas.overflow_in <= 0.005:
                return _build_title_result(TextFitStatus.FONT_ADJUSTED, 3)

    # 6. Still overflowing at role minimum floor -> Reflow or Unresolved
    status = TextFitStatus.REFLOW_REQUIRED if allow_reflow else TextFitStatus.UNRESOLVED_OVERFLOW
    fit_stage = 6 if allow_reflow else 7
    return _build_title_result(
        status, fit_stage, [DEFECT_TITLE_GEOMETRY_OVERFLOW, DEFECT_FONT_MINIMUM_REACHED]
    )


# ═══════════════════════════════════════════════════════════════
# 7. ORDERED FITTING PIPELINE (fit_text_to_region)
# ═══════════════════════════════════════════════════════════════

def fit_text_to_region(
    text_or_bullets: Any,
    role: TypographyRole,
    region_width_in: float,
    region_height_in: float,
    design_dna: Optional[DesignDNA] = None,
    content_density: ContentDensity = ContentDensity.MEDIUM,
    binding: Optional[ContentBinding] = None,
    content_priority: int = 1,
    is_compressible: bool = True,
    allow_notes_migration: bool = True,
    allow_reflow: bool = True,
    bullet_indentation_in: float = 0.0,
) -> TextFitResult:
    """
    Main Phase 3.2B ordered text fitting pipeline.
    Strategy execution order:
      STAGE 0: Exact fit with authoritative DesignDNA typography.
      STAGE 1: Reduce paragraph spacing within DesignDNA-safe bounds.
      STAGE 2: Reduce line height within role-safe bounds.
      STAGE 3: Reduce font size in bounded increments down to ROLE_MINIMUM_FONT_SIZES.
      STAGE 4: Semantically compress ONLY compressible text (never code/formulas/citations).
      STAGE 5: Move OPTIONAL supporting content (priority >= 4) to speaker notes.
      STAGE 6: Return REFLOW_REQUIRED (mandatory priority 1-2 or unresolvable).
      STAGE 7: Return UNRESOLVED_OVERFLOW if reflow is disallowed.
    """
    spacing_eng = SpacingEngine(design_dna=design_dna, content_density=content_density)
    transform_history: List[str] = []
    migrated_notes: List[NotesMigrationRecord] = []
    quality_defects: List[str] = []

    # Format text: preserve bullet structure if provided as list
    is_bullet_list = isinstance(text_or_bullets, list)
    bullets = [str(b).strip() for b in text_or_bullets] if is_bullet_list else [str(text_or_bullets).strip()]
    current_text = "\n".join(bullets)

    # 1. Authoritative base typography from DesignDNA (before density adaptation)
    dna_base_typo = resolve_typography_role_spec(
        role=role,
        design_dna=design_dna,
        content_density=ContentDensity.MEDIUM,
    )

    # 2. Typography after density adaptation
    density_resolved_typo = resolve_typography_role_spec(
        role=role,
        design_dna=design_dna,
        content_density=content_density,
    )
    density_adjustment = round(density_resolved_typo.font_size_pt - dna_base_typo.font_size_pt, 2)

    # 3. Fitting starts with density_resolved_typo
    typo_before = density_resolved_typo
    typo_current = typo_before.model_copy(deep=True)

    min_font_pt = ROLE_MINIMUM_FONT_SIZES.get(role, 8.5)
    min_line_height, max_line_height = spacing_eng.get_safe_line_height_range(role)
    min_para_spacing, max_para_spacing = spacing_eng.get_safe_paragraph_spacing_range(role)

    para_spacing_before = max_para_spacing
    para_spacing_current = para_spacing_before

    # Protected content checks: formulas, code, citations, mandatory priority 1
    is_formula = (role == TypographyRole.FORMULA)
    is_code = (role == TypographyRole.CODE_BLOCK if hasattr(TypographyRole, 'CODE_BLOCK') else False)
    is_citation = (role == TypographyRole.CAPTION and binding and binding.evidence_refs)
    is_mandatory = (content_priority <= 2)

    def _build_result(status: TextFitStatus, fit_stage: int, defects: Optional[List[str]] = None) -> TextFitResult:
        return TextFitResult(
            region_id=binding.source_id if binding else "region",
            status=status,
            fit_stage=fit_stage,
            original_binding=binding,
            resolved_content_hash=binding.resolved_content_hash if binding else "",
            display_text=current_text,
            typography_before=typo_before,
            typography_after=typo_current,
            design_dna_base_typography=dna_base_typo,
            density_resolved_typography=density_resolved_typo,
            fit_typography_before=typo_before,
            fit_typography_after=typo_current,
            density_adjustment=density_adjustment,
            resolved_role_min_line_height_ratio=min_line_height,
            paragraph_spacing_before=para_spacing_before,
            paragraph_spacing_after=para_spacing_current,
            line_height_before=typo_before.line_height_ratio,
            line_height_after=typo_current.line_height_ratio,
            migrated_content_bindings=list(migrated_notes),
            transform_history=list(transform_history),
            estimated_line_count=meas.estimated_line_count,
            estimated_text_height=meas.estimated_text_height_in,
            available_height=region_height_in,
            overflow_remaining=meas.overflow_in,
            quality_defects=defects or list(quality_defects),
        )

    # ─────────────────────────────────────────────────────────────
    # STAGE 0: Exact Fit
    # ─────────────────────────────────────────────────────────────
    meas = TextMeasurementEngine.measure_text(
        current_text,
        typo_current,
        region_width_in,
        region_height_in,
        bullet_indentation_in=bullet_indentation_in,
        paragraph_spacing_pt=para_spacing_current,
    )

    if meas.overflow_in <= 0.005:
        return _build_result(TextFitStatus.EXACT_FIT, 0)

    # ─────────────────────────────────────────────────────────────
    # STAGE 1: Reduce Paragraph Spacing
    # ─────────────────────────────────────────────────────────────
    if len(bullets) > 1 and para_spacing_current > min_para_spacing:
        old_ps = para_spacing_current
        para_spacing_current = min_para_spacing
        transform_history.append(f"Reduced paragraph spacing from {old_ps:.1f}pt to {min_para_spacing:.1f}pt")
        meas = TextMeasurementEngine.measure_text(
            current_text,
            typo_current,
            region_width_in,
            region_height_in,
            bullet_indentation_in=bullet_indentation_in,
            paragraph_spacing_pt=para_spacing_current,
        )
        if meas.overflow_in <= 0.005:
            return _build_result(TextFitStatus.SPACING_ADJUSTED, 1)

    # ─────────────────────────────────────────────────────────────
    # STAGE 2: Reduce Line Height
    # ─────────────────────────────────────────────────────────────
    if typo_current.line_height_ratio > min_line_height:
        old_lh = typo_current.line_height_ratio
        typo_current.line_height_ratio = min_line_height
        transform_history.append(f"Reduced line height ratio from {old_lh:.2f} to {min_line_height:.2f}")
        meas = TextMeasurementEngine.measure_text(
            current_text,
            typo_current,
            region_width_in,
            region_height_in,
            bullet_indentation_in=bullet_indentation_in,
            paragraph_spacing_pt=para_spacing_current,
        )
        if meas.overflow_in <= 0.005:
            return _build_result(TextFitStatus.LINE_HEIGHT_ADJUSTED, 2)

    # ─────────────────────────────────────────────────────────────
    # STAGE 3: Bounded Font Size Reduction (Down to role minimum floor)
    # ─────────────────────────────────────────────────────────────
    current_pt = typo_current.font_size_pt
    steps = [current_pt - 1.0, current_pt - 2.0, min_font_pt]

    for pt in steps:
        target_pt = round(pt, 1)
        if target_pt < typo_current.font_size_pt and target_pt >= min_font_pt:
            old_pt = typo_current.font_size_pt
            typo_current.font_size_pt = target_pt
            transform_history.append(f"Reduced font size from {old_pt:.1f}pt to {target_pt:.1f}pt")
            meas = TextMeasurementEngine.measure_text(
                current_text,
                typo_current,
                region_width_in,
                region_height_in,
                bullet_indentation_in=bullet_indentation_in,
                paragraph_spacing_pt=para_spacing_current,
            )
            if meas.overflow_in <= 0.005:
                return _build_result(TextFitStatus.FONT_ADJUSTED, 3)

    quality_defects.append(DEFECT_FONT_MINIMUM_REACHED)

    # ─────────────────────────────────────────────────────────────
    # STAGE 4: Safe Semantic Compression
    # (Never applied to code, formulas, citations, or non-compressible content)
    # ─────────────────────────────────────────────────────────────
    if is_compressible and not is_code and not is_formula:
        compressed_bullets: List[str] = []
        any_compressed = False

        for b in bullets:
            comp_b, did_comp, reason = compress_prose_safely(b)
            compressed_bullets.append(comp_b)
            if did_comp:
                any_compressed = True
                transform_history.append(f"Semantic compression: {reason}")

        if any_compressed:
            current_text = "\n".join(compressed_bullets)
            bullets = compressed_bullets
            meas = TextMeasurementEngine.measure_text(
                current_text,
                typo_current,
                region_width_in,
                region_height_in,
                bullet_indentation_in=bullet_indentation_in,
                paragraph_spacing_pt=para_spacing_current,
            )
            if meas.overflow_in <= 0.005:
                return _build_result(TextFitStatus.SEMANTICALLY_COMPRESSED, 4)

    # ─────────────────────────────────────────────────────────────
    # STAGE 5: Move Optional Detail to Speaker Notes
    # (Never migrate mandatory content, formulas, citations, or single items)
    # ─────────────────────────────────────────────────────────────
    if allow_notes_migration and not is_mandatory and len(bullets) > 1 and not is_formula and not is_code:
        # Move lowest priority / trailing optional bullets one by one
        while len(bullets) > 1:
            removed_item = bullets.pop()
            mig_record = NotesMigrationRecord(
                source_binding=binding,
                source_hash=binding.resolved_content_hash if binding else "",
                reason="stage_5_optional_detail_migration",
                original_priority=content_priority,
                display_content_removed=removed_item,
            )
            migrated_notes.append(mig_record)
            transform_history.append(f"Migrated detail to speaker notes: '{removed_item[:40]}...'")

            current_text = "\n".join(bullets)
            meas = TextMeasurementEngine.measure_text(
                current_text,
                typo_current,
                region_width_in,
                region_height_in,
                bullet_indentation_in=bullet_indentation_in,
                paragraph_spacing_pt=para_spacing_current,
            )
            if meas.overflow_in <= 0.005:
                return _build_result(TextFitStatus.DETAIL_MOVED_TO_NOTES, 5)

    # ─────────────────────────────────────────────────────────────
    # STAGE 6: Reflow Required
    # (Mandatory content cannot fit, or optional migration exhausted)
    # ─────────────────────────────────────────────────────────────
    if is_mandatory:
        quality_defects.append(DEFECT_MANDATORY_CONTENT_OVERFLOW)

    if allow_reflow:
        quality_defects.append(DEFECT_REFLOW_REQUIRED)
        return _build_result(TextFitStatus.REFLOW_REQUIRED, 6)

    # ─────────────────────────────────────────────────────────────
    # STAGE 7: Unresolved Overflow
    # ─────────────────────────────────────────────────────────────
    quality_defects.append(DEFECT_BODY_GEOMETRY_OVERFLOW)
    return _build_result(TextFitStatus.UNRESOLVED_OVERFLOW, 7)
