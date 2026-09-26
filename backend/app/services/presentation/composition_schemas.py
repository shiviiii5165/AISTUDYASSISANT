"""
LearnByGenie PPT vNext — Phase 3.2A Composition Schemas
===================================================
Defines strongly typed composition models, 12-column grid and 30-module vertical
baseline coordinates, typed ContentBinding, and immutable envelopes.

Independent from frozen schemas.py (zero circular dependencies).
Imports only from visual_schemas.py.
"""
from enum import Enum
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator
from .visual_schemas import Phase3LayoutFamily, VisualAssetType, ContentDensity, VisualDensityProfile


# ═══════════════════════════════════════════════════════════════
# 1. ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════

SLIDE_WIDTH_IN: float = 13.333
SLIDE_HEIGHT_IN: float = 7.500

HORIZONTAL_COLUMN_COUNT: int = 12
VERTICAL_MODULE_COUNT: int = 30
VERTICAL_MODULE_HEIGHT_IN: float = 0.250  # 30 * 0.250 in = 7.500 in exact full slide height


class CompositionMode(str, Enum):
    """Structural composition mode for a slide."""
    STANDARD_CANVAS      = "standard_canvas"
    SPLIT_COLUMNS        = "split_columns"
    FOCAL_HERO           = "focal_hero"
    ASYMMETRIC_EDITORIAL = "asymmetric_editorial"
    CARD_GRID            = "card_grid"
    FULL_BLEED_PANEL     = "full_bleed_panel"
    STEP_FLOW            = "step_flow"
    COMPARISON_COLUMNS   = "comparison_columns"
    DATA_DASHBOARD       = "data_dashboard"


class RegionSemanticRole(str, Enum):
    """Semantic role of a layout region."""
    HEADER_TITLE         = "header_title"
    HEADER_SUBTITLE      = "header_subtitle"
    CATEGORY_TAG         = "category_tag"
    PRIMARY_VISUAL       = "primary_visual"
    SECONDARY_VISUAL     = "secondary_visual"
    PRIMARY_TEXT         = "primary_text"
    SUPPORTING_POINTS    = "supporting_points"
    KEY_INSIGHT_CALLOUT  = "key_insight_callout"
    CARD_CONTAINER       = "card_container"
    COMPARISON_COLUMN_A  = "comparison_column_a"
    COMPARISON_COLUMN_B  = "comparison_column_b"
    FORMULA_DISPLAY      = "formula_display"
    CODE_BLOCK           = "code_block"
    METRIC_CARD          = "metric_card"
    PROCESS_STEP         = "process_step"
    TIMELINE_NODE        = "timeline_node"
    CAPTION              = "caption"
    FOOTER_CITATION      = "footer_citation"
    BLEED_BACKGROUND     = "bleed_background"


# Roles that must carry verified semantic content (never decorative-only)
CONTENT_BEARING_ROLES = {
    RegionSemanticRole.HEADER_TITLE,
    RegionSemanticRole.HEADER_SUBTITLE,
    RegionSemanticRole.CATEGORY_TAG,
    RegionSemanticRole.PRIMARY_VISUAL,
    RegionSemanticRole.SECONDARY_VISUAL,
    RegionSemanticRole.PRIMARY_TEXT,
    RegionSemanticRole.SUPPORTING_POINTS,
    RegionSemanticRole.KEY_INSIGHT_CALLOUT,
    RegionSemanticRole.COMPARISON_COLUMN_A,
    RegionSemanticRole.COMPARISON_COLUMN_B,
    RegionSemanticRole.FORMULA_DISPLAY,
    RegionSemanticRole.CODE_BLOCK,
    RegionSemanticRole.METRIC_CARD,
    RegionSemanticRole.PROCESS_STEP,
    RegionSemanticRole.TIMELINE_NODE,
    RegionSemanticRole.CAPTION,
    RegionSemanticRole.FOOTER_CITATION,
}


class RegionAlignment(str, Enum):
    LEFT    = "left"
    CENTER  = "center"
    RIGHT   = "right"
    JUSTIFY = "justify"


class VerticalAlignment(str, Enum):
    TOP    = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class RegionOverflowBehavior(str, Enum):
    TRUNCATE_SEMANTIC = "truncate_semantic"
    MIGRATE_TO_NOTES  = "migrate_to_notes"
    SHRINK_FONT       = "shrink_font"
    REFLOW_LAYOUT     = "reflow_layout"
    DISALLOW          = "disallow"


class SpacingToken(str, Enum):
    """DesignDNA-mapped spacing tokens."""
    XXS = "xxs"  # 2pt  / 0.028 in
    XS  = "xs"   # 4pt  / 0.056 in
    S   = "s"    # 8pt  / 0.111 in
    M   = "m"    # 16pt / 0.222 in
    L   = "l"    # 24pt / 0.333 in
    XL  = "xl"   # 32pt / 0.444 in
    XXL = "xxl"  # 48pt / 0.667 in


class TypographyRole(str, Enum):
    """12 semantic typography roles."""
    DISPLAY         = "display"
    TITLE           = "title"
    SUBTITLE        = "subtitle"
    SECTION_LABEL   = "section_label"
    BODY            = "body"
    BODY_EMPHASIS   = "body_emphasis"
    CAPTION         = "caption"
    ANNOTATION      = "annotation"
    QUOTE           = "quote"
    FORMULA         = "formula"
    TABLE_HEADER    = "table_header"
    TABLE_BODY      = "table_body"


class FormulaRenderMode(str, Enum):
    """Contract for rendering formulas in PPTX."""
    UNICODE_TEXT              = "unicode_text"               # Accessible faithful unicode math
    SAFE_LITERAL_TEXT         = "safe_literal_text"          # Safe plain text without raw LaTeX $
    DEFERRED_COMPLEX_FORMULA  = "deferred_complex_formula"   # Preserved for future specialized pass
    NATIVE_EQUATION_DEFERRED  = "native_equation_deferred"   # Deferred OMML equation generation (Phase 3.3)


class RendererCapability(str, Enum):
    """Accurate classification of python-pptx rendering capabilities."""
    NATIVE               = "native"                # Natively set via python-pptx API
    APPLICATION_RESOLVED = "application_resolved"  # Resolved by LearnByGenie application logic
    XML_EXTENSION        = "xml_extension"         # Manipulated via python-pptx oxml elements
    APPROXIMATED         = "approximated"          # Mapped to nearest native capability (e.g. bold flag)
    DEFERRED             = "deferred"              # Preserved structurally; rendered in later Phase 3.x


RENDERER_OPERATION_CAPABILITIES: Dict[str, RendererCapability] = {
    "primary_font_assignment": RendererCapability.NATIVE,
    "font_size_assignment": RendererCapability.NATIVE,
    "font_color_assignment": RendererCapability.NATIVE,
    "fallback_font_selection": RendererCapability.APPLICATION_RESOLVED,
    "shape_alt_text": RendererCapability.XML_EXTENSION,
    "shape_description": RendererCapability.XML_EXTENSION,
    "border_stroke_compound": RendererCapability.XML_EXTENSION,
    "font_weight_numerical_mapping": RendererCapability.APPROXIMATED,
    "omml_native_equation": RendererCapability.DEFERRED,
    "chart_native_rendering": RendererCapability.DEFERRED,
}


class SurfaceToken(str, Enum):
    TRANSPARENT      = "transparent"
    SURFACE_DEFAULT  = "surface_default"
    SURFACE_ELEVATED = "surface_elevated"
    SURFACE_ACCENT   = "surface_accent"
    SURFACE_MUTED    = "surface_muted"


class BorderToken(str, Enum):
    NONE     = "none"
    HAIRLINE = "hairline"
    THIN     = "thin"
    THICK    = "thick"
    ACCENT   = "accent"


class ColorToken(str, Enum):
    PRIMARY          = "primary"
    PRIMARY_LIGHT    = "primary_light"
    SECONDARY        = "secondary"
    ACCENT           = "accent"
    BACKGROUND       = "background"
    SURFACE          = "surface"
    TEXT_PRIMARY     = "text_primary"
    TEXT_SECONDARY   = "text_secondary"
    TEXT_ON_PRIMARY  = "text_on_primary"
    BORDER           = "border"
    SUCCESS          = "success"
    WARNING          = "warning"
    ERROR            = "error"


class QuadrantId(str, Enum):
    TOP_LEFT     = "top_left"
    TOP_RIGHT    = "top_right"
    BOTTOM_LEFT  = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    FULL_SPAN    = "full_span"


class SourceKind(str, Enum):
    SLIDE_CONTENT           = "slide_content"
    VISUAL_SEMANTIC_PACKET  = "visual_semantic_packet"
    EVIDENCE                = "evidence"
    DECORATIVE              = "decorative"


# Role-Aware Typography Floors (Readable minimum pt bounds)
ROLE_MINIMUM_FONT_SIZES: Dict[TypographyRole, float] = {
    TypographyRole.DISPLAY:         28.0,
    TypographyRole.TITLE:           20.0,
    TypographyRole.SUBTITLE:        12.0,
    TypographyRole.SECTION_LABEL:   10.0,
    TypographyRole.BODY:            11.0,  # Guaranteed readable; never collapses to caption
    TypographyRole.BODY_EMPHASIS:   11.0,
    TypographyRole.QUOTE:           15.0,
    TypographyRole.FORMULA:         14.0,
    TypographyRole.TABLE_HEADER:    10.0,
    TypographyRole.TABLE_BODY:      9.0,   # Role-specific table floor
    TypographyRole.CAPTION:         8.5,   # Role-specific caption floor
    TypographyRole.ANNOTATION:      8.5,   # Role-specific annotation floor
}


# Safe Zone Constants (1-indexed baseline modules)
ZONE_TOP_MARGIN_START: int = 1
ZONE_TOP_MARGIN_END: int = 2
ZONE_TITLE_START: int = 3
ZONE_TITLE_END: int = 7
ZONE_CONTENT_START: int = 8
ZONE_CONTENT_END: int = 27
ZONE_FOOTER_START: int = 28
ZONE_FOOTER_END: int = 30
ZONE_BOTTOM_MARGIN_START: int = 30
ZONE_BOTTOM_MARGIN_END: int = 30

MARGIN_LEFT_IN: float = 0.800
MARGIN_RIGHT_IN: float = 0.800
MARGIN_TOP_IN: float = 0.600
MARGIN_BOTTOM_IN: float = 0.600


class LayoutSafeZone(str, Enum):
    """
    Typed safe zone classifications enforcing containment authority.
    Baseline grid = alignment authority; Safe zones = containment authority.
    """
    SAFE_TITLE   = "safe_title"    # Title zone: rows 3..7 (0.50" - 1.75")
    SAFE_CONTENT = "safe_content"  # Main active content: rows 8..27 (1.75" - 6.75")
    SAFE_FOOTER  = "safe_footer"   # Footer & citation zone: rows 28..30 (6.75" - 7.50")
    FULL_BLEED   = "full_bleed"    # Canvas-wide: rows 1..30 (decorative visuals only)


ROLE_DEFAULT_SAFE_ZONE: Dict[RegionSemanticRole, LayoutSafeZone] = {
    RegionSemanticRole.HEADER_TITLE:         LayoutSafeZone.SAFE_TITLE,
    RegionSemanticRole.HEADER_SUBTITLE:      LayoutSafeZone.SAFE_TITLE,
    RegionSemanticRole.CATEGORY_TAG:         LayoutSafeZone.SAFE_TITLE,
    
    RegionSemanticRole.PRIMARY_VISUAL:       LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.SECONDARY_VISUAL:     LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.PRIMARY_TEXT:         LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.SUPPORTING_POINTS:    LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.KEY_INSIGHT_CALLOUT:  LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.CARD_CONTAINER:       LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.COMPARISON_COLUMN_A:  LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.COMPARISON_COLUMN_B:  LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.FORMULA_DISPLAY:      LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.CODE_BLOCK:           LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.METRIC_CARD:          LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.PROCESS_STEP:         LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.TIMELINE_NODE:        LayoutSafeZone.SAFE_CONTENT,
    RegionSemanticRole.CAPTION:              LayoutSafeZone.SAFE_CONTENT,
    
    RegionSemanticRole.FOOTER_CITATION:      LayoutSafeZone.SAFE_FOOTER,
    
    RegionSemanticRole.BLEED_BACKGROUND:     LayoutSafeZone.FULL_BLEED,
}


class ContentBindingHashMismatch(ValueError):
    """
    Structured defect raised when resolved content payload hash does not match
    the bound content hash.
    """
    def __init__(self, region_id: str, field_path: str, expected_hash: str, actual_hash: str):
        super().__init__(
            f"CONTENT_BINDING_HASH_MISMATCH: region '{region_id}' field '{field_path}' "
            f"expected hash '{expected_hash}' but computed '{actual_hash}'"
        )
        self.region_id = region_id
        self.field_path = field_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash


# ═══════════════════════════════════════════════════════════════
# 2. FORMULA FIDELITY & HELPERS
# ═══════════════════════════════════════════════════════════════

UNICODE_SUBSCRIPTS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ",
    "k": "ₖ", "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ",
    "p": "ₚ", "r": "ᵣ", "s": "ₛ", "t": "ₜ", "u": "ᵤ",
    "v": "ᵥ", "x": "ₓ",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
}

UNICODE_SUPERSCRIPTS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "n": "ⁿ", "i": "ⁱ", "+": "⁺", "-": "⁻", "=": "⁼",
    "(": "⁽", ")": "⁾",
}

UNICODE_GREEK_SYMBOLS = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
    r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ", r"\xi": "ξ",
    r"\pi": "π", r"\rho": "ρ", r"\sigma": "σ", r"\tau": "τ",
    r"\phi": "φ", r"\chi": "χ", r"\psi": "ψ", r"\omega": "ω",
    r"\Delta": "Δ", r"\Sigma": "Σ", r"\Omega": "Ω", r"\Psi": "Ψ",
}

UNICODE_OPERATORS = {
    r"\times": "×", r"\cdot": "·", r"\le": "≤", r"\leq": "≤",
    r"\ge": "≥", r"\geq": "≥", r"\ne": "≠", r"\neq": "≠",
    r"\approx": "≈", r"\pm": "±", r"\to": "→", r"\in": "∈",
    r"\sum": "∑", r"\int": "∫", r"\sqrt": "√", r"\infty": "∞",
    r"\frac{1}{2}": "½", r"\frac{1}{4}": "¼", r"\frac{3}{4}": "¾",
}


def convert_latex_to_faithful_unicode(raw_latex: str) -> str:
    r"""
    Converts mathematically meaningful notation faithfully to Unicode.
    E.g. E_k -> Eₖ (never lossy Ek), x^2 -> x², \lambda -> λ.
    Guarantees zero raw LaTeX delimiters ($, $$, \(, \)) leak into output.
    """
    if not raw_latex:
        return ""
    text = raw_latex.strip()
    
    # Strip delimiters
    for delim in ("$$", "$", r"\[", r"\]", r"\(", r"\)"):
        text = text.replace(delim, "")
    text = text.strip()

    # Replace known operators and symbols
    for tex, uni in UNICODE_OPERATORS.items():
        text = text.replace(tex, uni)
    for tex, uni in UNICODE_GREEK_SYMBOLS.items():
        text = text.replace(tex, uni)

    # Subscripts with braces: e.g. _{max} -> ₘₐₓ, _{k} -> ₖ
    import re
    def sub_brace_repl(m):
        content = m.group(1)
        return "".join(UNICODE_SUBSCRIPTS.get(c, c) for c in content)
    text = re.sub(r'_\{([^}]+)\}', sub_brace_repl, text)

    # Simple single-char subscripts: _k -> ₖ
    def sub_single_repl(m):
        c = m.group(1)
        return UNICODE_SUBSCRIPTS.get(c, f"_{c}")
    text = re.sub(r'_([0-9a-zA-Z\+\-\=])', sub_single_repl, text)

    # Superscripts with braces: e.g. ^{2} -> ²
    def sup_brace_repl(m):
        content = m.group(1)
        return "".join(UNICODE_SUPERSCRIPTS.get(c, c) for c in content)
    text = re.sub(r'\^\{([^}]+)\}', sup_brace_repl, text)

    # Simple single-char superscripts: ^2 -> ²
    def sup_single_repl(m):
        c = m.group(1)
        return UNICODE_SUPERSCRIPTS.get(c, f"^{c}")
    text = re.sub(r'\^([0-9a-zA-Z\+\-\=])', sup_single_repl, text)

    # Strip remaining LaTeX curly braces
    text = text.replace("{", "").replace("}", "")
    return text.strip()


def convert_latex_to_safe_literal(raw_latex: str) -> str:
    """Safely strips raw LaTeX delimiters and environments without lossy text mangling."""
    if not raw_latex:
        return ""
    text = raw_latex.strip()
    for delim in ("$$", "$", r"\[", r"\]", r"\(", r"\)"):
        text = text.replace(delim, "")
    text = text.replace(r"\times", "*").replace(r"\cdot", "*")
    return text.strip()


class FormulaPayload(BaseModel):
    """
    Preserves exact original formula source while offering faithful Unicode
    fallback for Phase 3.2 typography rendering.
    """
    original_source: str                         # Raw LaTeX e.g. "E_k = \\frac{1}{2}mv^2"
    ast_representation: Optional[Dict[str, Any]] = None
    render_mode: FormulaRenderMode = FormulaRenderMode.UNICODE_TEXT
    unicode_representation: str = ""             # Faithful Unicode e.g. "Eₖ = ½mv²"
    safe_literal_representation: str = ""        # Delimiter-free plain text

    @model_validator(mode="after")
    def populate_representations(self):
        if not self.unicode_representation and self.original_source:
            self.unicode_representation = convert_latex_to_faithful_unicode(self.original_source)
        if not self.safe_literal_representation and self.original_source:
            self.safe_literal_representation = convert_latex_to_safe_literal(self.original_source)
        return self


# ═══════════════════════════════════════════════════════════════
# 3. CONTENT BINDING & MANIFEST CONTRACT
# ═══════════════════════════════════════════════════════════════

class ContentBinding(BaseModel):
    """
    Immutable typed binding linking a ContentRegion directly to verified source content.
    Zero new semantic or factual content may be generated in Phase 3.2.
    """
    source_kind: SourceKind = SourceKind.SLIDE_CONTENT
    source_id: str = ""                         # UUID or verified content identifier
    field_path: str = ""                        # e.g. "title", "body_bullets[0]", "formula"
    item_indices: List[int] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    source_object_hash: str = ""                # Full 64-char SHA-256 of immutable source object
    resolved_content_hash: str = ""             # Full 64-char SHA-256 of resolved value
    content_hash: str = ""                      # Backward-compatibility alias for resolved_content_hash
    is_decorative: bool = False                 # True only for structural dividers / containers
    transform_history: List[str] = Field(default_factory=list)

    def short_hash(self) -> str:
        """Returns short prefix for logs/debug output only."""
        h = self.resolved_content_hash or self.content_hash
        return h[:16] if h else ""

    @model_validator(mode="after")
    def validate_content_binding(self):
        # Sync content_hash and resolved_content_hash
        if not self.resolved_content_hash and self.content_hash:
            self.resolved_content_hash = self.content_hash
        elif not self.content_hash and self.resolved_content_hash:
            self.content_hash = self.resolved_content_hash

        if not self.is_decorative:
            if self.source_kind == SourceKind.DECORATIVE:
                raise ValueError("Non-decorative ContentBinding cannot have source_kind=DECORATIVE")
            if not self.source_id or not self.source_id.strip():
                raise ValueError("Non-decorative ContentBinding requires a non-empty source_id")
            if not self.field_path or not self.field_path.strip():
                raise ValueError("Non-decorative ContentBinding requires a non-empty field_path")
            if not self.resolved_content_hash or not self.resolved_content_hash.strip():
                raise ValueError("Non-decorative ContentBinding requires a non-empty resolved_content_hash")
        return self


class CompositionInputManifest(BaseModel):
    """Immutable manifest registry holding verified raw content payloads for a deck."""
    manifest_id: str
    deck_title: str = ""
    slide_content_hashes: Dict[str, str] = Field(default_factory=dict)
    raw_content_items: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @staticmethod
    def compute_payload_hash(val: Any) -> str:
        """Deterministically computes full 64-char SHA-256 hash of a content payload."""
        if val is None:
            return ""
        if isinstance(val, (str, int, float, bool)):
            s = str(val).strip()
        else:
            import json
            s = json.dumps(val, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def register_content(self, source_id: str, content: Dict[str, Any]) -> str:
        """Stores content payload and computes full 64-char SHA-256 hash."""
        chash = self.compute_payload_hash(content)
        self.raw_content_items[source_id] = content
        self.slide_content_hashes[source_id] = chash
        return chash

    def compute_field_hash(self, source_id: str, field_path: str) -> str:
        """Resolves field and returns its exact 64-char SHA-256 resolved_content_hash."""
        item = self.raw_content_items.get(source_id)
        if item is None:
            return ""
        curr = item
        if field_path:
            for part in field_path.split("."):
                if "[" in part and part.endswith("]"):
                    fname, idx_str = part[:-1].split("[")
                    if isinstance(curr, dict):
                        curr = curr.get(fname, [])
                    else:
                        return ""
                    try:
                        idx = int(idx_str)
                        if isinstance(curr, list) and 0 <= idx < len(curr):
                            curr = curr[idx]
                        else:
                            return ""
                    except (ValueError, TypeError):
                        return ""
                else:
                    if isinstance(curr, dict):
                        curr = curr.get(part)
                    else:
                        return ""
        return self.compute_payload_hash(curr)

    def resolve_content(self, binding: ContentBinding, region_id: str = "") -> Any:
        """
        Deterministically resolves displayed content from the immutable manifest.
        Verifies payload hash integrity. If payload and hash disagree, raises CONTENT_BINDING_HASH_MISMATCH.
        """
        if binding.is_decorative:
            return None
        
        item = self.raw_content_items.get(binding.source_id)
        if item is None:
            return None
        
        if not binding.field_path:
            curr = item
        else:
            curr = item
            for part in binding.field_path.split("."):
                if "[" in part and part.endswith("]"):
                    fname, idx_str = part[:-1].split("[")
                    if isinstance(curr, dict):
                        curr = curr.get(fname, [])
                    else:
                        return None
                    try:
                        idx = int(idx_str)
                        if isinstance(curr, list) and 0 <= idx < len(curr):
                            curr = curr[idx]
                        else:
                            return None
                    except (ValueError, TypeError):
                        return None
                else:
                    if isinstance(curr, dict):
                        curr = curr.get(part)
                    else:
                        return None

        # Verify hash integrity against resolved_content_hash
        expected_hash = binding.resolved_content_hash or binding.content_hash
        if expected_hash and curr is not None:
            actual_hash = self.compute_payload_hash(curr)
            # Full 64-char match or prefix match if short prefix was supplied
            if actual_hash != expected_hash and not actual_hash.startswith(expected_hash):
                raise ContentBindingHashMismatch(
                    region_id=region_id or binding.source_id,
                    field_path=binding.field_path,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                )

        return curr


# ═══════════════════════════════════════════════════════════════
# 4. SPATIAL GEOMETRY & REGION MODELS
# ═══════════════════════════════════════════════════════════════

class ResolvedRegionBounds(BaseModel):
    """Exact physical inches resolved after 12-column grid and vertical baseline constraint solving."""
    left_in: float = Field(..., ge=0.0, le=13.333)
    top_in: float = Field(..., ge=0.0, le=7.500)
    width_in: float = Field(..., ge=0.1, le=13.333)
    height_in: float = Field(..., ge=0.1, le=7.500)

    @model_validator(mode="after")
    def validate_canvas_containment(self):
        if self.left_in + self.width_in > 13.334:
            raise ValueError(f"Region right edge {self.left_in + self.width_in:.3f} exceeds slide width 13.333")
        if self.top_in + self.height_in > 7.501:
            raise ValueError(f"Region bottom edge {self.top_in + self.height_in:.3f} exceeds slide height 7.500")
        return self


class TypographyRoleSpec(BaseModel):
    """Typography styling spec bound to a region."""
    role: TypographyRole = TypographyRole.BODY
    font_family: str = "Inter"
    fallback_family: str = "Calibri"
    safe_office_fallback: str = "Calibri"
    font_size_pt: float = Field(..., ge=8.0, le=72.0)
    font_weight: int = Field(default=400, ge=100, le=900)
    line_height_ratio: float = Field(default=1.4, ge=1.0, le=2.2)
    letter_spacing_em: float = Field(default=0.0, ge=-0.05, le=0.2)
    color_token: ColorToken = ColorToken.TEXT_PRIMARY
    max_recommended_lines: int = Field(default=4, ge=1, le=12)

    @model_validator(mode="after")
    def validate_role_minimum_floor(self):
        min_allowed = ROLE_MINIMUM_FONT_SIZES.get(self.role, 8.5)
        if self.font_size_pt < min_allowed:
            raise ValueError(
                f"Font size {self.font_size_pt:.1f}pt for role {self.role.value} "
                f"is below role minimum readable floor {min_allowed:.1f}pt"
            )
        return self


class ContentRegion(BaseModel):
    """Strongly typed spatial region bound to 12-column grid and 30-module baseline rhythm."""
    region_id: str
    semantic_role: RegionSemanticRole
    safe_zone: Optional[LayoutSafeZone] = None
    binding: ContentBinding = Field(default_factory=lambda: ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE))
    quadrant: QuadrantId = QuadrantId.TOP_LEFT
    
    # 12-Column Grid Coordinates
    grid_col_start: int = Field(..., ge=1, le=HORIZONTAL_COLUMN_COUNT)
    grid_col_span: int = Field(..., ge=1, le=HORIZONTAL_COLUMN_COUNT)
    
    # 30-Module Vertical Baseline Coordinates (30 modules * 0.25" = 7.50" height)
    baseline_row_start: int = Field(..., ge=1, le=VERTICAL_MODULE_COUNT)
    baseline_row_span: int = Field(..., ge=1, le=VERTICAL_MODULE_COUNT)
    
    # Resolved Coordinates in Inches
    bounds: ResolvedRegionBounds
    
    # Dimension Bounds
    min_width_in: float = 0.5
    max_width_in: float = 13.333
    min_height_in: float = 0.2
    max_height_in: float = 7.500
    alignment: RegionAlignment = RegionAlignment.LEFT
    vertical_alignment: VerticalAlignment = VerticalAlignment.TOP
    padding_token: SpacingToken = SpacingToken.S
    content_priority: int = Field(default=1, ge=1, le=5)
    overflow_behavior: RegionOverflowBehavior = RegionOverflowBehavior.SHRINK_FONT
    
    # Visual Styling
    typography_spec: Optional[TypographyRoleSpec] = None
    surface_token: SurfaceToken = SurfaceToken.TRANSPARENT
    border_token: BorderToken = BorderToken.NONE
    corner_radius_pt: float = 0.0
    renderer_capability: RendererCapability = RendererCapability.NATIVE
    is_full_bleed: bool = False

    @model_validator(mode="after")
    def validate_grid_and_baseline_bounds(self):
        # Auto-assign default safe zone from semantic role if not explicitly set
        if self.safe_zone is None:
            self.safe_zone = ROLE_DEFAULT_SAFE_ZONE.get(self.semantic_role, LayoutSafeZone.SAFE_CONTENT)

        # 1. Content-bearing binding check (Strict complete bindings: non-decorative, source_id, field_path, hash)
        if self.semantic_role in CONTENT_BEARING_ROLES:
            if self.binding.is_decorative:
                raise ValueError(
                    f"Content-bearing region '{self.region_id}' ({self.semantic_role.value}) cannot carry decorative binding"
                )
            if self.binding.source_kind == SourceKind.DECORATIVE:
                raise ValueError(
                    f"Content-bearing region '{self.region_id}' ({self.semantic_role.value}) cannot have source_kind=DECORATIVE"
                )
            if not self.binding.source_id or not self.binding.source_id.strip():
                raise ValueError(
                    f"Content-bearing region '{self.region_id}' ({self.semantic_role.value}) requires a non-empty source_id"
                )
            if not self.binding.field_path or not self.binding.field_path.strip():
                raise ValueError(
                    f"Content-bearing region '{self.region_id}' ({self.semantic_role.value}) requires a non-empty field_path"
                )
            h = self.binding.resolved_content_hash or self.binding.content_hash
            if not h or not h.strip():
                raise ValueError(
                    f"Content-bearing region '{self.region_id}' ({self.semantic_role.value}) requires a non-empty resolved_content_hash"
                )
            if self.safe_zone == LayoutSafeZone.FULL_BLEED or self.is_full_bleed:
                raise ValueError(
                    f"Ordinary semantic text/content region '{self.region_id}' ({self.semantic_role.value}) cannot use FULL_BLEED"
                )

        # 2. Vertical baseline check: row_start + row_span - 1 <= VERTICAL_MODULE_COUNT (30)
        if self.baseline_row_start + self.baseline_row_span - 1 > VERTICAL_MODULE_COUNT:
            raise ValueError(
                f"Vertical baseline range ({self.baseline_row_start}..{self.baseline_row_start + self.baseline_row_span - 1}) "
                f"exceeds total {VERTICAL_MODULE_COUNT} vertical baseline modules"
            )

        # 3. Horizontal grid check: col_start + col_span - 1 <= HORIZONTAL_COLUMN_COUNT (12)
        if not self.is_full_bleed and (self.grid_col_start + self.grid_col_span - 1 > HORIZONTAL_COLUMN_COUNT):
            raise ValueError(
                f"Column span ({self.grid_col_start} + {self.grid_col_span} - 1) exceeds {HORIZONTAL_COLUMN_COUNT} columns"
            )

        # 4. Safe zone containment checks (Safe zones = containment authority)
        if self.safe_zone == LayoutSafeZone.SAFE_TITLE:
            if self.baseline_row_start < ZONE_TITLE_START or (self.baseline_row_start + self.baseline_row_span - 1 > ZONE_TITLE_END):
                raise ValueError(
                    f"Title region '{self.region_id}' baseline rows ({self.baseline_row_start}..{self.baseline_row_start + self.baseline_row_span - 1}) "
                    f"exceed title-safe zone [{ZONE_TITLE_START}..{ZONE_TITLE_END}]"
                )
            if self.bounds.left_in < MARGIN_LEFT_IN - 0.01 or (self.bounds.left_in + self.bounds.width_in > SLIDE_WIDTH_IN - MARGIN_RIGHT_IN + 0.01):
                raise ValueError(f"Title region '{self.region_id}' horizontal bounds exceed safe margins")

        elif self.safe_zone == LayoutSafeZone.SAFE_CONTENT:
            if self.baseline_row_start < ZONE_CONTENT_START or (self.baseline_row_start + self.baseline_row_span - 1 > ZONE_CONTENT_END):
                raise ValueError(
                    f"Content region '{self.region_id}' baseline rows ({self.baseline_row_start}..{self.baseline_row_start + self.baseline_row_span - 1}) "
                    f"exceed content-safe zone [{ZONE_CONTENT_START}..{ZONE_CONTENT_END}]"
                )
            if self.bounds.left_in < MARGIN_LEFT_IN - 0.01 or (self.bounds.left_in + self.bounds.width_in > SLIDE_WIDTH_IN - MARGIN_RIGHT_IN + 0.01):
                raise ValueError(f"Content region '{self.region_id}' horizontal bounds exceed safe margins")

        elif self.safe_zone == LayoutSafeZone.SAFE_FOOTER:
            if self.baseline_row_start < ZONE_FOOTER_START or (self.baseline_row_start + self.baseline_row_span - 1 > ZONE_FOOTER_END):
                raise ValueError(
                    f"Footer region '{self.region_id}' baseline rows ({self.baseline_row_start}..{self.baseline_row_start + self.baseline_row_span - 1}) "
                    f"exceed footer-safe zone [{ZONE_FOOTER_START}..{ZONE_FOOTER_END}]"
                )
            if self.bounds.left_in < MARGIN_LEFT_IN - 0.01 or (self.bounds.left_in + self.bounds.width_in > SLIDE_WIDTH_IN - MARGIN_RIGHT_IN + 0.01):
                raise ValueError(f"Footer region '{self.region_id}' horizontal bounds exceed safe margins")

        elif self.safe_zone == LayoutSafeZone.FULL_BLEED:
            if not self.is_full_bleed:
                self.is_full_bleed = True

        # 5. Min/Max dimension coherence
        if self.min_width_in > self.max_width_in:
            raise ValueError(f"min_width_in ({self.min_width_in}) exceeds max_width_in ({self.max_width_in})")
        if self.min_height_in > self.max_height_in:
            raise ValueError(f"min_height_in ({self.min_height_in}) exceeds max_height_in ({self.max_height_in})")
        return self


# ═══════════════════════════════════════════════════════════════
# 5. WHITESPACE METRICS & RESPONSIVE CONSTRAINTS
# ═══════════════════════════════════════════════════════════════

class WhitespaceMetrics(BaseModel):
    """
    Region occupancy metrics (measures planned bounding-box geometry,
    not pixel-level ink density).
    """
    total_canvas_area_sq_in: float = 100.0   # 13.333 * 7.500
    region_occupied_area_sq_in: float = 0.0
    region_occupied_area_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    text_area_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    visual_area_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    planned_whitespace_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    target_band_min: float = 0.20
    target_band_max: float = 0.65
    is_within_role_band: bool = True
    quadrant_weights: Dict[QuadrantId, float] = Field(default_factory=dict)


class ResponsiveConstraints(BaseModel):
    allow_font_shrink: bool = True
    min_font_size_pt: float = 11.0
    max_font_shrink_steps: int = 3
    allow_line_spacing_reduction: bool = True
    allow_speaker_note_migration: bool = True
    allow_layout_fallback: bool = True
    fallback_layout_family: Optional[Phase3LayoutFamily] = None


# ═══════════════════════════════════════════════════════════════
# 6. COMPOSITION PLAN & ENVELOPES
# ═══════════════════════════════════════════════════════════════

class SlideCompositionPlan(BaseModel):
    """Complete, deterministic spatial composition plan for a single slide."""
    slide_no: int = Field(..., ge=1)
    layout_family: Phase3LayoutFamily
    composition_mode: CompositionMode
    content_regions: List[ContentRegion] = Field(default_factory=list)
    whitespace_metrics: WhitespaceMetrics = Field(default_factory=WhitespaceMetrics)
    visual_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    hierarchy_levels: int = Field(default=3, ge=1, le=5)
    responsive_constraints: ResponsiveConstraints = Field(default_factory=ResponsiveConstraints)
    composition_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    planning_rationale: str = ""
    template_name: str = "academic_clean"
    palette_name: str = "blue_professional"
    formula_render_mode: FormulaRenderMode = FormulaRenderMode.UNICODE_TEXT
    has_deferred_chart: bool = False

    @field_validator("content_regions")
    @classmethod
    def validate_unique_regions(cls, regions: List[ContentRegion]) -> List[ContentRegion]:
        seen = set()
        for r in regions:
            if r.region_id in seen:
                raise ValueError(f"Duplicate region_id '{r.region_id}' in SlideCompositionPlan")
            seen.add(r.region_id)
        return regions


class ComposedSlideContext(BaseModel):
    """
    Additive envelope binding a SlideSpec to its SlideCompositionPlan
    without modifying frozen SlideSpec.
    """
    slide_no: int
    composition_plan: SlideCompositionPlan
    composition_input_manifest_id: str
    slide_content_id: Optional[str] = None
    slide_content_hash: Optional[str] = None
    visual_packet_id: Optional[str] = None
    visual_packet_hash: Optional[str] = None


class DeckCompositionPlan(BaseModel):
    """
    Deck-level composition envelope.
    Verifies adherence to Phase 3.1 DeckVisualRhythmPlan without recomputing rhythm.
    """
    deck_title: str
    slide_plans: Dict[int, SlideCompositionPlan] = Field(default_factory=dict)
    template_name: str = "academic_clean"
    palette_name: str = "blue_professional"
    rhythm_plan_compliance: float = Field(default=1.0, ge=0.0, le=1.0)
    average_planned_whitespace_ratio: float = 0.38

