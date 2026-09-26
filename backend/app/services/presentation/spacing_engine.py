"""
TeachGenie PPT vNext — Phase 3.2B Spacing Engine
================================================
Consumes frozen Phase 3.1 DesignDNA spacing tokens to resolve semantic spacing
purposes (margins, card padding, paragraph gaps, title-to-content spacing).

Zero independent spacing grammars: DesignDNA is the single source of truth.
No arbitrary inch or point constants scattered throughout layout logic.
"""
from enum import Enum
from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field

from .visual_schemas import DesignDNA, SpacingScale, ContentDensity
from .composition_schemas import SpacingToken, TypographyRole


# ═══════════════════════════════════════════════════════════════
# 1. SEMANTIC SPACING PURPOSES
# ═══════════════════════════════════════════════════════════════

class SpacingPurpose(str, Enum):
    """Semantic purpose of spatial gap or padding."""
    OUTER_MARGIN        = "outer_margin"         # Canvas boundary margin
    TITLE_TO_SUBTITLE   = "title_to_subtitle"    # Gap between title and subtitle
    TITLE_TO_CONTENT    = "title_to_content"     # Gap between header zone and active content zone
    PARAGRAPH_GAP       = "paragraph_gap"        # Spacing between body paragraphs
    BULLET_GAP          = "bullet_gap"           # Spacing between bullet items
    TEXT_TO_VISUAL      = "text_to_visual"       # Gap between text region and visual region
    CARD_PADDING        = "card_padding"         # Interior padding of card containers
    CARD_GAP            = "card_gap"             # Gap between adjacent cards
    CAPTION_GAP         = "caption_gap"          # Gap between visual and caption
    SECTION_GAP         = "section_gap"          # Structural division gap
    FORMULA_PADDING     = "formula_padding"      # Interior breathing room around formula displays
    CODE_PADDING        = "code_padding"         # Interior padding for code blocks


# Default semantic token mapping for each purpose
DEFAULT_PURPOSE_TOKENS: Dict[SpacingPurpose, SpacingToken] = {
    SpacingPurpose.OUTER_MARGIN:        SpacingToken.XL,   # 32pt / 0.444 in
    SpacingPurpose.TITLE_TO_SUBTITLE:   SpacingToken.XS,   # 4pt  / 0.056 in
    SpacingPurpose.TITLE_TO_CONTENT:    SpacingToken.L,    # 24pt / 0.333 in
    SpacingPurpose.PARAGRAPH_GAP:       SpacingToken.S,    # 8pt  / 0.111 in
    SpacingPurpose.BULLET_GAP:          SpacingToken.S,    # 8pt  / 0.111 in
    SpacingPurpose.TEXT_TO_VISUAL:      SpacingToken.M,    # 16pt / 0.222 in
    SpacingPurpose.CARD_PADDING:        SpacingToken.M,    # 16pt / 0.222 in
    SpacingPurpose.CARD_GAP:            SpacingToken.S,    # 8pt  / 0.111 in
    SpacingPurpose.CAPTION_GAP:         SpacingToken.XS,   # 4pt  / 0.056 in
    SpacingPurpose.SECTION_GAP:         SpacingToken.XL,   # 32pt / 0.444 in
    SpacingPurpose.FORMULA_PADDING:     SpacingToken.S,    # 8pt  / 0.111 in
    SpacingPurpose.CODE_PADDING:        SpacingToken.S,    # 8pt  / 0.111 in
}

# Fallback SpacingScale if DesignDNA is missing or corrupt
FALLBACK_SPACING_SCALE = SpacingScale(
    xs=4.0,
    s=8.0,
    m=16.0,
    l=24.0,
    xl=32.0,
    xxl=48.0,
)


# ═══════════════════════════════════════════════════════════════
# 2. RESOLVED SPACING MODELS
# ═══════════════════════════════════════════════════════════════

class ResolvedSpacingSpec(BaseModel):
    """
    Resolved physical spacing specification.
    Maintains semantic token reference while providing exact points and inches.
    """
    purpose: SpacingPurpose
    token: SpacingToken
    pt_value: float = Field(..., ge=0.0)
    in_value: float = Field(..., ge=0.0)
    min_pt_value: float = Field(default=0.0, ge=0.0)
    max_pt_value: float = Field(default=72.0, ge=0.0)
    density_adapted: bool = False
    is_fallback: bool = False


# ═══════════════════════════════════════════════════════════════
# 3. SPACING ENGINE
# ═══════════════════════════════════════════════════════════════

class SpacingEngine:
    """
    Authoritative spacing resolver consuming DesignDNA spacing scale.
    Adapts spacing systematically by content density without breaking token contracts.
    """

    def __init__(
        self,
        design_dna: Optional[DesignDNA] = None,
        content_density: Optional[ContentDensity] = None,
    ):
        self.is_fallback: bool = False
        if design_dna is not None and hasattr(design_dna, "spacing_scale"):
            self.spacing_scale = design_dna.spacing_scale
            if content_density is not None:
                self.density = content_density
            else:
                self.density = getattr(design_dna, "density_profile", ContentDensity.MEDIUM) or ContentDensity.MEDIUM
        else:
            self.spacing_scale = FALLBACK_SPACING_SCALE
            self.density = content_density or ContentDensity.MEDIUM
            self.is_fallback = True

        # Precompute base token values in points
        self._token_points: Dict[SpacingToken, float] = {
            SpacingToken.XXS: max(2.0, round(self.spacing_scale.xs * 0.5, 1)),
            SpacingToken.XS:  self.spacing_scale.xs,
            SpacingToken.S:   self.spacing_scale.s,
            SpacingToken.M:   self.spacing_scale.m,
            SpacingToken.L:   self.spacing_scale.l,
            SpacingToken.XL:  self.spacing_scale.xl,
            SpacingToken.XXL: self.spacing_scale.xxl,
        }

    def resolve_token_points(self, token: SpacingToken) -> float:
        """Resolves raw points for a SpacingToken from DesignDNA."""
        return self._token_points.get(token, 8.0)

    def resolve_token_inches(self, token: SpacingToken) -> float:
        """Resolves exact inches for a SpacingToken (pt / 72)."""
        return round(self.resolve_token_points(token) / 72.0, 3)

    def resolve_spacing(
        self,
        purpose: SpacingPurpose,
        override_token: Optional[SpacingToken] = None,
    ) -> ResolvedSpacingSpec:
        """
        Resolves semantic spacing for a specific purpose using DesignDNA.
        Applies role-aware density adjustments (tightening under HIGH, expanding under LOW).
        """
        token = override_token or DEFAULT_PURPOSE_TOKENS.get(purpose, SpacingToken.S)
        base_pt = self.resolve_token_points(token)

        # Density scaling multiplier
        if self.density == ContentDensity.HIGH:
            multiplier = 0.80  # 20% tighter spacing under high density
        elif self.density == ContentDensity.LOW:
            multiplier = 1.20  # 20% more breathing room under low density
        else:
            multiplier = 1.00

        # Safe bounds: spacing cannot collapse to 0 or exceed 1.5x base
        min_allowed_pt = max(2.0, round(base_pt * 0.5, 1))
        max_allowed_pt = round(base_pt * 1.5, 1)

        adapted_pt = round(max(min_allowed_pt, min(base_pt * multiplier, max_allowed_pt)), 1)
        adapted_in = round(adapted_pt / 72.0, 3)

        return ResolvedSpacingSpec(
            purpose=purpose,
            token=token,
            pt_value=adapted_pt,
            in_value=adapted_in,
            min_pt_value=min_allowed_pt,
            max_pt_value=max_allowed_pt,
            density_adapted=(multiplier != 1.0),
            is_fallback=self.is_fallback,
        )

    def get_safe_paragraph_spacing_range(self, role: TypographyRole) -> Tuple[float, float]:
        """
        Returns (min_pt, max_pt) safe paragraph spacing range for a typography role.
        Stage 1 fitting reduces paragraph spacing within these bounds.
        """
        base_s = self.resolve_token_points(SpacingToken.S)  # 8pt
        if role in (TypographyRole.DISPLAY, TypographyRole.TITLE):
            return (4.0, 16.0)
        elif role == TypographyRole.SUBTITLE:
            return (2.0, 8.0)
        elif role in (TypographyRole.BODY, TypographyRole.BODY_EMPHASIS):
            return (2.0, base_s * 1.5)  # Can compress from 12pt down to 2pt
        elif role == TypographyRole.CAPTION:
            return (1.0, 4.0)
        elif role in (TypographyRole.TABLE_HEADER, TypographyRole.TABLE_BODY):
            return (2.0, 6.0)
        return (2.0, 8.0)

    def get_safe_line_height_range(self, role: TypographyRole) -> Tuple[float, float]:
        """
        Returns (min_ratio, max_ratio) safe line-height bounds for a typography role.
        Stage 2 fitting reduces line-height ratio within these bounds.
        """
        if role == TypographyRole.TITLE:
            return (1.08, 1.30)
        elif role == TypographyRole.DISPLAY:
            return (1.05, 1.25)
        elif role in (TypographyRole.BODY, TypographyRole.BODY_EMPHASIS):
            return (1.15, 1.60)  # Body text never collapses below 1.15 line-height
        elif role == TypographyRole.CAPTION:
            return (1.15, 1.40)
        elif role == TypographyRole.FORMULA:
            return (1.20, 1.60)
        elif role in (TypographyRole.TABLE_HEADER, TypographyRole.TABLE_BODY):
            return (1.20, 1.50)
        return (1.15, 1.50)
