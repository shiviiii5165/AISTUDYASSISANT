"""
TeachGenie PPT vNext — Phase 3.2B Typography, Spacing & Text-Fitting Test Suite
=================================================================================
Validates Phase 3.2B contracts:
  1. Authoritative DesignDNA typography consumption and density adaptation
  2. Fallback DesignDNA handling when missing or corrupt
  3. Role-specific font size minimums (BODY strictly >= 11.0pt)
  4. Relational typographic hierarchy contract (DISPLAY > TITLE > SUBTITLE > BODY)
  5. SpacingEngine semantic purpose resolution without magic constants
  6. TextMeasurementEngine geometry-aware line and height estimation
  7. Title geometry fitting around Phase 3.1 semantic title fitting
  8. Safe semantic compression preserving numbers, equations, quotes, citations
  9. Formula safety: Unicode preservation, no delimiter leaks, no splitting
  10. Code safety: syntax preservation, indentation, no truncation
  11. Citation safety: evidence_refs preservation
  12. 7-stage ordered fitting pipeline (Stages 0..6)
  13. Speaker notes migration with typed NotesMigrationRecord
  14. Mandatory content protection (priority 1-2 never dropped)
  15. Genuine runtime test fixtures across 5 held-out disciplines:
      - Computer Science (Node.js architecture)
      - Biology (Photosynthesis)
      - Literature (Macbeth)
      - Mathematics (Eigenvalues/eigenvectors)
      - Economics (Inflation/monetary policy)
"""
import hashlib
import pytest
from typing import Dict, Any, List

from app.services.presentation.visual_schemas import (
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
)
from app.services.presentation.composition_schemas import (
    TypographyRole,
    TypographyRoleSpec,
    ROLE_MINIMUM_FONT_SIZES,
    ContentBinding,
    SourceKind,
    FormulaPayload,
    FormulaRenderMode,
    SpacingToken,
)
from app.services.presentation.spacing_engine import (
    SpacingEngine,
    SpacingPurpose,
    ResolvedSpacingSpec,
    DEFAULT_PURPOSE_TOKENS,
    FALLBACK_SPACING_SCALE,
)
from app.services.presentation.typography_engine import (
    TextFitStatus,
    NotesMigrationRecord,
    TextMeasurementResult,
    TextMeasurementEngine,
    TextFitResult,
    resolve_typography_role_spec,
    validate_typography_hierarchy,
    is_safe_semantic_compression,
    compress_prose_safely,
    fit_title_to_geometry,
    fit_text_to_region,
    DEFECT_TITLE_GEOMETRY_OVERFLOW,
    DEFECT_BODY_GEOMETRY_OVERFLOW,
    DEFECT_FONT_MINIMUM_REACHED,
    DEFECT_LINE_HEIGHT_MINIMUM_REACHED,
    DEFECT_FORMULA_OVERFLOW,
    DEFECT_CODE_OVERFLOW,
    DEFECT_CITATION_OVERFLOW,
    DEFECT_MANDATORY_CONTENT_OVERFLOW,
    DEFECT_REFLOW_REQUIRED,
    DEFECT_TYPOGRAPHY_HIERARCHY_INVALID,
    DEFECT_DESIGNDNA_MISSING_FALLBACK_APPLIED,
)


# Helper fixture for standard DesignDNA
@pytest.fixture
def standard_dna() -> DesignDNA:
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=26.0, line_height_ratio=1.20, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=13.5, line_height_ratio=1.45, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25, letter_spacing_em=0.02,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.MEDIUM,
    )


# ═══════════════════════════════════════════════════════════════
# 1. DESIGNDNA TYPOGRAPHY CONSUMPTION & DENSITY ADAPTATION
# ═══════════════════════════════════════════════════════════════

def test_designdna_authoritative_typography_consumption(standard_dna):
    """Validates that TypographyEngine derives tokens strictly from DesignDNA."""
    title_spec = resolve_typography_role_spec(TypographyRole.TITLE, design_dna=standard_dna)
    assert title_spec.font_family == "Inter"
    assert title_spec.font_weight == 700
    assert title_spec.font_size_pt == 26.0
    assert title_spec.line_height_ratio == 1.20

    body_spec = resolve_typography_role_spec(TypographyRole.BODY, design_dna=standard_dna)
    assert body_spec.font_family == "Inter"
    assert body_spec.font_weight == 400
    assert body_spec.font_size_pt == 13.5
    assert body_spec.line_height_ratio == 1.45


def test_density_adaptation_within_safe_bounds(standard_dna):
    """Validates density adaptation (LOW adds size, HIGH tightens within floors)."""
    # MEDIUM (Baseline)
    body_med = resolve_typography_role_spec(TypographyRole.BODY, design_dna=standard_dna, content_density=ContentDensity.MEDIUM)
    # LOW Density: slightly larger
    body_low = resolve_typography_role_spec(TypographyRole.BODY, design_dna=standard_dna, content_density=ContentDensity.LOW)
    # HIGH Density: slightly tighter
    body_high = resolve_typography_role_spec(TypographyRole.BODY, design_dna=standard_dna, content_density=ContentDensity.HIGH)

    assert body_low.font_size_pt > body_med.font_size_pt
    assert body_high.font_size_pt < body_med.font_size_pt
    assert body_high.font_size_pt >= ROLE_MINIMUM_FONT_SIZES[TypographyRole.BODY]


def test_fallback_designdna_behavior_when_missing():
    """Validates fallback typography specs when DesignDNA is missing (None)."""
    title_fallback = resolve_typography_role_spec(TypographyRole.TITLE, design_dna=None)
    assert title_fallback.font_size_pt >= 20.0
    assert title_fallback.font_family == "Inter"

    body_fallback = resolve_typography_role_spec(TypographyRole.BODY, design_dna=None)
    assert body_fallback.font_size_pt >= 11.0
    assert body_fallback.role == TypographyRole.BODY


# ═══════════════════════════════════════════════════════════════
# 2. ROLE MINIMUM FONT FLOORS & READABILITY
# ═══════════════════════════════════════════════════════════════

def test_role_minimum_floors_preserved(standard_dna):
    """Ensures BODY text never collapses to caption size (8.5pt) and respects 11.0pt floor."""
    body_floor = ROLE_MINIMUM_FONT_SIZES[TypographyRole.BODY]
    assert body_floor == 11.0

    body_spec = resolve_typography_role_spec(
        TypographyRole.BODY,
        design_dna=standard_dna,
        content_density=ContentDensity.HIGH,
    )
    assert body_spec.font_size_pt >= 11.0

    caption_spec = resolve_typography_role_spec(TypographyRole.CAPTION, design_dna=standard_dna)
    assert caption_spec.font_size_pt >= 8.5
    assert caption_spec.font_size_pt < body_spec.font_size_pt


# ═══════════════════════════════════════════════════════════════
# 3. TYPOGRAPHIC HIERARCHY CONTRACT & DEFECTS
# ═══════════════════════════════════════════════════════════════

def test_typographic_hierarchy_validity(standard_dna):
    """Validates that standard role resolution produces a valid relational hierarchy."""
    roles = [
        TypographyRole.DISPLAY,
        TypographyRole.TITLE,
        TypographyRole.SUBTITLE,
        TypographyRole.SECTION_LABEL,
        TypographyRole.BODY,
        TypographyRole.BODY_EMPHASIS,
        TypographyRole.CAPTION,
        TypographyRole.FORMULA,
    ]
    specs = {r: resolve_typography_role_spec(r, design_dna=standard_dna) for r in roles}
    defects = validate_typography_hierarchy(specs)
    assert len(defects) == 0, f"Unexpected hierarchy defects: {defects}"

    # Relational hierarchy checks
    assert specs[TypographyRole.DISPLAY].font_size_pt > specs[TypographyRole.TITLE].font_size_pt
    assert specs[TypographyRole.TITLE].font_size_pt > specs[TypographyRole.SUBTITLE].font_size_pt
    assert specs[TypographyRole.TITLE].font_size_pt > specs[TypographyRole.BODY].font_size_pt
    assert specs[TypographyRole.BODY].font_size_pt >= specs[TypographyRole.BODY_EMPHASIS].font_size_pt
    assert specs[TypographyRole.CAPTION].font_size_pt < specs[TypographyRole.BODY].font_size_pt
    assert specs[TypographyRole.FORMULA].font_size_pt >= specs[TypographyRole.BODY].font_size_pt


def test_typographic_hierarchy_defect_detection():
    """Validates structured defect generation when hierarchy is inverted without violating role floors."""
    invalid_specs = {
        TypographyRole.TITLE: TypographyRoleSpec(role=TypographyRole.TITLE, font_size_pt=20.0),
        TypographyRole.BODY: TypographyRoleSpec(role=TypographyRole.BODY, font_size_pt=20.0),  # BODY >= TITLE!
        TypographyRole.CAPTION: TypographyRoleSpec(role=TypographyRole.CAPTION, font_size_pt=11.0),
    }
    invalid_specs_caption = {
        TypographyRole.TITLE: TypographyRoleSpec(role=TypographyRole.TITLE, font_size_pt=24.0),
        TypographyRole.BODY: TypographyRoleSpec(role=TypographyRole.BODY, font_size_pt=11.0),
        TypographyRole.CAPTION: TypographyRoleSpec(role=TypographyRole.CAPTION, font_size_pt=11.0),  # CAPTION >= BODY!
    }
    defects1 = validate_typography_hierarchy(invalid_specs)
    assert len(defects1) >= 1
    assert any("must be strictly greater than BODY" in d for d in defects1)

    defects2 = validate_typography_hierarchy(invalid_specs_caption)
    assert len(defects2) >= 1
    assert any("must be strictly smaller than BODY" in d for d in defects2)



# ═══════════════════════════════════════════════════════════════
# 4. SPACING ENGINE & SEMANTIC PURPOSES
# ═══════════════════════════════════════════════════════════════

def test_spacing_engine_purpose_resolution(standard_dna):
    """Validates semantic spacing purpose resolution from DesignDNA tokens."""
    engine = SpacingEngine(design_dna=standard_dna, content_density=ContentDensity.MEDIUM)

    title_to_content = engine.resolve_spacing(SpacingPurpose.TITLE_TO_CONTENT)
    assert title_to_content.token == SpacingToken.L
    assert title_to_content.pt_value == 24.0
    assert title_to_content.in_value == round(24.0 / 72.0, 3)

    card_padding = engine.resolve_spacing(SpacingPurpose.CARD_PADDING)
    assert card_padding.token == SpacingToken.M
    assert card_padding.pt_value == 16.0

    bullet_gap = engine.resolve_spacing(SpacingPurpose.BULLET_GAP)
    assert bullet_gap.token == SpacingToken.S
    assert bullet_gap.pt_value == 8.0


def test_spacing_engine_density_scaling(standard_dna):
    """Validates density scaling: HIGH tightens spacing, LOW expands spacing."""
    engine_med = SpacingEngine(design_dna=standard_dna, content_density=ContentDensity.MEDIUM)
    engine_high = SpacingEngine(design_dna=standard_dna, content_density=ContentDensity.HIGH)
    engine_low = SpacingEngine(design_dna=standard_dna, content_density=ContentDensity.LOW)

    gap_med = engine_med.resolve_spacing(SpacingPurpose.CARD_GAP)
    gap_high = engine_high.resolve_spacing(SpacingPurpose.CARD_GAP)
    gap_low = engine_low.resolve_spacing(SpacingPurpose.CARD_GAP)

    assert gap_high.pt_value < gap_med.pt_value
    assert gap_low.pt_value > gap_med.pt_value


# ═══════════════════════════════════════════════════════════════
# 5. GEOMETRY-AWARE TEXT MEASUREMENT ENGINE
# ═══════════════════════════════════════════════════════════════

def test_text_measurement_engine_line_wrapping():
    """Validates deterministic text measurement accounting for width and word boundaries."""
    typo = TypographyRoleSpec(
        role=TypographyRole.BODY,
        font_family="Inter",
        font_size_pt=14.0,
        line_height_ratio=1.4,
    )
    # 20 words in a narrow 3.0" column will wrap onto multiple lines
    text = "The mitochondria is the powerhouse of eukaryotic cells responsible for oxidative phosphorylation and generating adenosine triphosphate energy molecules."
    res = TextMeasurementEngine.measure_text(
        text=text,
        typography_spec=typo,
        region_width_in=3.0,
        region_height_in=3.0,
    )
    assert res.estimated_line_count >= 4
    assert res.estimated_text_height_in > 0.8
    assert res.overflow_in < 0.0  # Fits inside 3.0" height


def test_text_measurement_engine_unbreakable_token():
    """Validates detection of tokens exceeding available column width."""
    typo = TypographyRoleSpec(
        role=TypographyRole.BODY,
        font_family="Inter",
        font_size_pt=14.0,
    )
    # Extremely long unbreakable chemical identifier
    long_token = "Deoxyribonucleicacidphosphodiesterlinkagepolynucleotideterminus"
    res = TextMeasurementEngine.measure_text(
        text=f"Structure: {long_token}",
        typography_spec=typo,
        region_width_in=2.0,  # Narrow column ~144pt
        region_height_in=2.0,
    )
    assert len(res.unbreakable_tokens) > 0
    assert long_token in res.unbreakable_tokens


# ═══════════════════════════════════════════════════════════════
# 6. TITLE GEOMETRY FITTING & PHASE 3.1 COMPLIANCE
# ═══════════════════════════════════════════════════════════════

def test_title_fitting_with_phase31_semantic_fit():
    """
    Validates title fitting:
    - Long title (> 60 chars) uses Phase 3.1 fit_title_semantic
    - Preserves central concept and subject
    - Bounded font size down to 20pt floor
    """
    long_title = "An In-Depth Comprehensive Overview of Protein Synthesis and Translation"
    binding = ContentBinding(
        source_id="title_s1",
        field_path="title",
        resolved_content_hash=hashlib.sha256(long_title.encode()).hexdigest(),
    )
    # 11.7" width title zone with 1.25" height
    res = fit_title_to_geometry(
        title=long_title,
        region_width_in=11.7,
        region_height_in=1.25,
        binding=binding,
    )
    assert len(res.display_text) <= 60
    assert "Protein Synthesis" in res.display_text
    assert res.status in (TextFitStatus.SEMANTICALLY_COMPRESSED, TextFitStatus.EXACT_FIT)
    assert res.typography_after.font_size_pt >= 20.0


def test_title_fitting_narrow_geometry_font_adjustment():
    """Validates that a 50-char title in a very narrow column adjusts font size safely."""
    title_text = "Thermodynamic Entropy and Statistical States"
    binding = ContentBinding(
        source_id="title_s2",
        field_path="title",
        resolved_content_hash=hashlib.sha256(title_text.encode()).hexdigest(),
    )
    # Narrow column (3.5" wide) and tight height (0.50" = 1 baseline row)
    res = fit_title_to_geometry(
        title=title_text,
        region_width_in=3.5,
        region_height_in=0.50,
        binding=binding,
    )
    # It either fits with adjusted typography or requests reflow
    assert res.status in (TextFitStatus.FONT_ADJUSTED, TextFitStatus.LINE_HEIGHT_ADJUSTED, TextFitStatus.REFLOW_REQUIRED)
    assert res.typography_after.font_size_pt >= 20.0


# ═══════════════════════════════════════════════════════════════
# 7. SEMANTIC COMPRESSION SAFETY & CONTENT PRESERVATION
# ═══════════════════════════════════════════════════════════════

def test_safe_semantic_compression_trims_filler():
    """Validates trimming redundant introductory phrases without loss of facts."""
    prose = "It is important to note that central banks increase interest rates by 2.5% to combat inflation."
    comp, was_comp, reason = compress_prose_safely(prose)
    assert was_comp is True
    assert "2.5%" in comp, "Lost critical percentage"
    assert "inflation" in comp
    assert not comp.startswith("It is important to note that")


def test_safe_semantic_compression_rejects_dropping_numbers_or_quotes():
    """Validates rejection of candidate compression that drops numbers or quotes."""
    orig = "GDP grew by 3.2% in 2024 according to official reports."
    bad_cand = "GDP grew according to official reports."  # Dropped 3.2% and 2024
    is_safe, reason = is_safe_semantic_compression(orig, bad_cand)
    assert is_safe is False
    assert "Number '3.2%' was dropped" in reason


# ═══════════════════════════════════════════════════════════════
# 8. FORMULA, CODE & CITATION SAFETY
# ═══════════════════════════════════════════════════════════════

def test_formula_safety_no_semantic_compression():
    """Validates that mathematical formulas are NEVER semantically compressed or truncated."""
    formula_latex = r"E_k = \frac{1}{2}mv^2"
    binding = ContentBinding(
        source_id="formula_01",
        field_path="formula",
        resolved_content_hash=hashlib.sha256(formula_latex.encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=formula_latex,
        role=TypographyRole.FORMULA,
        region_width_in=5.0,
        region_height_in=1.0,
        binding=binding,
    )
    # Formulas must remain intact
    assert res.display_text == formula_latex
    assert res.status != TextFitStatus.SEMANTICALLY_COMPRESSED
    assert res.typography_after.font_size_pt >= 14.0  # Formula minimum floor


def test_code_safety_preserves_syntax_and_indentation():
    """Validates that code blocks preserve exact indentation and are not rewritten."""
    code_snippet = "async function fetchData(url) {\n    const res = await fetch(url);\n    return res.json();\n}"
    binding = ContentBinding(
        source_id="code_01",
        field_path="code",
        resolved_content_hash=hashlib.sha256(code_snippet.encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=code_snippet,
        role=TypographyRole.TABLE_BODY,  # Monospace / table role
        region_width_in=6.0,
        region_height_in=2.0,
        binding=binding,
        is_compressible=False,  # Code is never marked compressible
    )
    assert "    const res = await fetch(url);" in res.display_text
    assert res.status != TextFitStatus.SEMANTICALLY_COMPRESSED


def test_citation_safety_preserves_evidence_refs():
    """Validates that citation markers and evidence references are never dropped."""
    citation_text = "Results corroborated by observational cosmology [1]."
    binding = ContentBinding(
        source_id="cite_01",
        field_path="citations[0]",
        resolved_content_hash=hashlib.sha256(citation_text.encode()).hexdigest(),
        evidence_refs=["cite_nature_cosmology_2023"],
    )
    res = fit_text_to_region(
        text_or_bullets=citation_text,
        role=TypographyRole.CAPTION,
        region_width_in=6.0,
        region_height_in=0.5,
        binding=binding,
    )
    assert "[1]" in res.display_text
    assert res.original_binding.evidence_refs == ["cite_nature_cosmology_2023"]


# ═══════════════════════════════════════════════════════════════
# 9. ORDERED FITTING PIPELINE & NOTES MIGRATION
# ═══════════════════════════════════════════════════════════════

def test_fitting_pipeline_stage1_spacing_adjusted():
    """Validates Stage 1: Paragraph spacing adjustment resolves mild multi-bullet overflow."""
    bullets = [
        "First primary concept establishing core domain foundational axioms.",
        "Second complementary concept exploring practical dynamic applications.",
        "Third empirical observation confirming theoretical predictions consistently.",
    ]
    binding = ContentBinding(
        source_id="bullets_01",
        field_path="body_bullets",
        resolved_content_hash=hashlib.sha256("\n".join(bullets).encode()).hexdigest(),
    )
    # Geometry where default paragraph spacing slightly overflows, but reduced spacing fits
    res = fit_text_to_region(
        text_or_bullets=bullets,
        role=TypographyRole.BODY,
        region_width_in=5.5,
        region_height_in=1.65,
        binding=binding,
    )
    assert res.status in (TextFitStatus.EXACT_FIT, TextFitStatus.SPACING_ADJUSTED)
    assert res.fit_stage in (0, 1)


def test_fitting_pipeline_stage3_font_adjusted():
    """Validates Stage 3: Bounded font reduction resolves text overflow without dropping content."""
    text = "Detailed explanation of macroeconomic quantitative easing and federal reserve open market balance sheet expansions."
    binding = ContentBinding(
        source_id="body_qe",
        field_path="body",
        resolved_content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    # Tight height (0.50") where 13.5pt overflows but 11.5pt fits
    res = fit_text_to_region(
        text_or_bullets=text,
        role=TypographyRole.BODY,
        region_width_in=4.5,
        region_height_in=0.55,
        binding=binding,
    )
    assert res.status in (TextFitStatus.FONT_ADJUSTED, TextFitStatus.LINE_HEIGHT_ADJUSTED)
    assert res.typography_after.font_size_pt >= 11.0


def test_fitting_pipeline_stage5_detail_moved_to_notes():
    """Validates Stage 5: Optional trailing bullets migrated to speaker notes with NotesMigrationRecord."""
    bullets = [
        "Primary finding: Enzyme catalytic activity accelerates exponentially with temperature up to optimum.",
        "Secondary observation: Denaturation begins at 45°C as hydrogen bonds break down.",
        "Optional footnote: Laboratory buffer solution maintained at pH 7.4 throughout all trial runs.",
        "Expendable detail: Reagent batch #4029 was supplied by Sigma-Aldrich on dry ice.",
    ]
    binding = ContentBinding(
        source_id="bio_bullets",
        field_path="observations",
        resolved_content_hash=hashlib.sha256("\n".join(bullets).encode()).hexdigest(),
    )
    # Constrained box (1.2" height) that cannot hold 4 bullets even at 11pt
    res = fit_text_to_region(
        text_or_bullets=bullets,
        role=TypographyRole.BODY,
        region_width_in=5.0,
        region_height_in=1.20,
        binding=binding,
        content_priority=4,  # Optional support
        allow_notes_migration=True,
    )
    assert res.status == TextFitStatus.DETAIL_MOVED_TO_NOTES
    assert res.fit_stage == 5
    assert len(res.migrated_content_bindings) > 0
    mig = res.migrated_content_bindings[0]
    assert len(mig.notes_content_hash) == 64
    assert mig.destination == "speaker_notes"


def test_fitting_pipeline_mandatory_content_protection_reflow():
    """Validates that mandatory content (priority 1) is NEVER moved to notes; triggers REFLOW_REQUIRED."""
    mandatory_bullets = [
        "Core Law 1: An isolated system remains in state of rest or uniform motion unless acted on.",
        "Core Law 2: Force equals rate of change of momentum (F = ma).",
        "Core Law 3: For every action there is an equal and opposite reaction force.",
        "Core Constraint: Relativistic corrections apply when velocities approach speed of light c.",
    ]
    binding = ContentBinding(
        source_id="laws_mandatory",
        field_path="newton_laws",
        resolved_content_hash=hashlib.sha256("\n".join(mandatory_bullets).encode()).hexdigest(),
    )
    # Extremely cramped region (0.6" height)
    res = fit_text_to_region(
        text_or_bullets=mandatory_bullets,
        role=TypographyRole.BODY,
        region_width_in=4.0,
        region_height_in=0.60,
        binding=binding,
        content_priority=1,  # MANDATORY
        allow_notes_migration=False,  # Disallowed for mandatory
        allow_reflow=True,
    )
    assert res.status == TextFitStatus.REFLOW_REQUIRED
    assert res.fit_stage == 6
    assert DEFECT_MANDATORY_CONTENT_OVERFLOW in res.quality_defects
    assert len(res.migrated_content_bindings) == 0  # Zero bullets dropped!


# ═══════════════════════════════════════════════════════════════
# 10. GENUINE RUNTIME SAMPLES ACROSS 5 DISCIPLINES
# ═══════════════════════════════════════════════════════════════

def test_runtime_sample_computer_science_nodejs():
    """Runtime sample 1: Computer Science — Node.js Architecture (EXACT_FIT)."""
    text = "V8 JavaScript Engine executes single-threaded event loop delegating asynchronous I/O operations to libuv worker threadpool."
    binding = ContentBinding(
        source_id="cs_nodejs_01",
        field_path="architecture_summary",
        resolved_content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=text,
        role=TypographyRole.BODY,
        region_width_in=5.8,
        region_height_in=1.8,
        binding=binding,
    )
    assert res.status == TextFitStatus.EXACT_FIT
    assert res.fit_stage == 0


def test_runtime_sample_biology_photosynthesis():
    """Runtime sample 2: Biology — Photosynthesis (SPACING_ADJUSTED)."""
    bullets = [
        "Light reactions occur within thylakoid membranes synthesizing ATP and NADPH.",
        "Calvin-Benson cycle fixes CO₂ into glyceraldehyde-3-phosphate in stroma.",
        "Rubisco enzyme catalyzes initial carboxylation step under regulatory light control.",
    ]
    binding = ContentBinding(
        source_id="bio_photo_01",
        field_path="phases",
        resolved_content_hash=hashlib.sha256("\n".join(bullets).encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=bullets,
        role=TypographyRole.BODY,
        region_width_in=5.2,
        region_height_in=1.65,
        binding=binding,
    )
    assert res.status in (TextFitStatus.EXACT_FIT, TextFitStatus.SPACING_ADJUSTED)


def test_runtime_sample_literature_macbeth():
    """Runtime sample 3: Literature — Macbeth (FONT_ADJUSTED)."""
    text = "Shakespeare portrays tragic ambition through Macbeth's fatal hubris, wherein prophecy catalyses regicide and psychological disintegration."
    binding = ContentBinding(
        source_id="lit_macbeth_01",
        field_path="thesis",
        resolved_content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=text,
        role=TypographyRole.BODY,
        region_width_in=4.2,
        region_height_in=0.68,
        binding=binding,
    )
    assert res.status in (TextFitStatus.FONT_ADJUSTED, TextFitStatus.LINE_HEIGHT_ADJUSTED)
    assert res.typography_after.font_size_pt >= 11.0


def test_runtime_sample_mathematics_eigenvalues():
    """Runtime sample 4: Mathematics — Eigenvalues & Eigenvectors (DETAIL_MOVED_TO_NOTES)."""
    bullets = [
        "Characteristic equation: det(A - λI) = 0 yields n complex or real eigenvalues for square matrix A.",
        "Eigenvector v satisfies (A - λI)v = 0 spanning the non-trivial invariant eigenspace E_λ.",
        "Diagonalizable matrix decomposition: P⁻¹AP = D where D is a diagonal matrix of all eigenvalues.",
        "Optional note: Gram-Schmidt orthogonalization applies to symmetric matrices to construct orthonormal bases.",
    ]
    binding = ContentBinding(
        source_id="math_eigen_01",
        field_path="theorems",
        resolved_content_hash=hashlib.sha256("\n".join(bullets).encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=bullets,
        role=TypographyRole.BODY,
        region_width_in=5.0,
        region_height_in=0.90,
        binding=binding,
        content_priority=4,
        allow_notes_migration=True,
    )
    assert res.status == TextFitStatus.DETAIL_MOVED_TO_NOTES
    assert len(res.migrated_content_bindings) >= 1



def test_runtime_sample_economics_inflation_monetary_policy():
    """Runtime sample 5: Economics — Inflation & Monetary Policy (REFLOW_REQUIRED)."""
    mandatory_content = [
        "Phillips Curve demonstrates short-run trade-off between inflation and unemployment rates.",
        "Quantity Theory of Money: MV = PY links money supply growth directly to price level increases.",
        "Taylor Rule dictates central bank policy rate adjustments based on inflation gap and output gap.",
        "Quantitative tightening reduces central bank balance sheet to withdraw systemic liquidity reserves.",
    ]
    binding = ContentBinding(
        source_id="econ_infl_01",
        field_path="policy_pillars",
        resolved_content_hash=hashlib.sha256("\n".join(mandatory_content).encode()).hexdigest(),
    )
    # Extremely cramped 0.5" height cannot fit 4 mandatory concepts -> must trigger REFLOW_REQUIRED
    res = fit_text_to_region(
        text_or_bullets=mandatory_content,
        role=TypographyRole.BODY,
        region_width_in=4.0,
        region_height_in=0.50,
        binding=binding,
        content_priority=1,  # Mandatory
        allow_notes_migration=False,
        allow_reflow=True,
    )
    assert res.status == TextFitStatus.REFLOW_REQUIRED
    assert res.fit_stage == 6
    assert DEFECT_MANDATORY_CONTENT_OVERFLOW in res.quality_defects


# ═══════════════════════════════════════════════════════════════
# 11. AUDIT TRAIL CONSISTENCY & ROLE-SAFE LINE HEIGHT INVARIANTS
# ═══════════════════════════════════════════════════════════════

def test_audit_trail_consistency_and_explicit_fields():
    """
    Validates that:
      1. Explicit audit trail fields are populated (design_dna_base_typography,
         density_resolved_typography, fit_typography_before, fit_typography_after,
         density_adjustment, fit_stage).
      2. Stage 1 (spacing adjustment) does NOT perform font reduction.
      3. Density adaptation before fitting is distinctly accounted for.
    """
    dna = DesignDNA(
        theme_family="modern_minimal",
        tone="clean",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=24.0, line_height_ratio=1.20, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=12.5, line_height_ratio=1.45, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25, letter_spacing_em=0.02,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.HIGH,
    )
    bullets = [
        "Photosystem II absorbs light energy and oxidizes water.",
        "High-energy electrons transfer through plastoquinone to cytochrome b6f.",
        "ATP synthase harnesses the electrochemical proton gradient to generate ATP.",
    ]
    binding = ContentBinding(
        source_id="bio_audit_01",
        field_path="sections.light_dependent",
        resolved_content_hash=hashlib.sha256("\n".join(bullets).encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=bullets,
        role=TypographyRole.BODY,
        region_width_in=6.0,
        region_height_in=1.15,
        design_dna=dna,
        content_density=ContentDensity.HIGH,
        binding=binding,
        content_priority=2,
    )

    # 1. Verify audit trail fields are present
    assert res.design_dna_base_typography is not None
    assert res.density_resolved_typography is not None
    assert res.fit_typography_before is not None
    assert res.fit_typography_after is not None

    # 2. DesignDNA base was 12.5pt; HIGH density adapted to 11.5pt (-1.0pt offset)
    assert res.design_dna_base_typography.font_size_pt == 12.5
    assert res.density_resolved_typography.font_size_pt == 11.5
    assert res.density_adjustment == -1.0

    # 3. Fitting resolved at Stage 1 (SPACING_ADJUSTED): font size MUST NOT change during Stage 1
    assert res.status == TextFitStatus.SPACING_ADJUSTED
    assert res.fit_stage == 1
    assert res.fit_typography_before.font_size_pt == 11.5
    assert res.fit_typography_after.font_size_pt == 11.5

    # 4. Transform history records only spacing adjustment, NO font reduction records
    assert any("paragraph spacing" in t.lower() for t in res.transform_history)
    assert not any("font size" in t.lower() for t in res.transform_history)


def test_no_noop_transform_history_records():
    """Validates that transform_history never logs no-op or identical-size state changes."""
    dna = DesignDNA(
        theme_family="editorial",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Georgia", font_fallback="Calibri", font_weight=700,
            font_size_pt=28.0, line_height_ratio=1.20, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Georgia", font_fallback="Calibri", font_weight=400,
            font_size_pt=15.0, line_height_ratio=1.45, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Georgia", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25, letter_spacing_em=0.02,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.LOW,
    )
    text = (
        'Shakespeare constructs Macbeth\'s tragic downfall through unchecked ambition, '
        'manifest when he declares: "Stars, hide your fires; let not light see my black and deep desires." '
        'Lady Macbeth amplifies this psychological trajectory.'
    )
    binding = ContentBinding(
        source_id="lit_macbeth_audit",
        field_path="analysis.themes",
        resolved_content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    res = fit_text_to_region(
        text_or_bullets=text,
        role=TypographyRole.BODY,
        region_width_in=5.5,
        region_height_in=0.75,
        design_dna=dna,
        content_density=ContentDensity.LOW,
        binding=binding,
        content_priority=2,
    )
    assert res.status == TextFitStatus.FONT_ADJUSTED
    assert res.fit_stage == 3

    # Check every font reduction transform: from Xpt to Ypt must satisfy Y < X
    for record in res.transform_history:
        if "Reduced font size" in record:
            import re
            m = re.search(r"from\s+(\d+\.?\d*)pt\s+to\s+(\d+\.?\d*)pt", record)
            assert m is not None, f"Expected 'from Xpt to Ypt' format in: {record}"
            from_pt = float(m.group(1))
            to_pt = float(m.group(2))
            assert to_pt < from_pt, f"No-op font reduction detected: from {from_pt} to {to_pt}"


def test_role_safe_line_height_invariants_across_roles(standard_dna):
    """
    Validates that final_line_height_ratio >= resolved_role_min_line_height_ratio
    for every role: BODY, BODY_EMPHASIS, TITLE, CAPTION, FORMULA, TABLE_BODY.
    """
    roles_to_test = [
        (TypographyRole.BODY, 1.15),
        (TypographyRole.BODY_EMPHASIS, 1.15),
        (TypographyRole.CAPTION, 1.15),
        (TypographyRole.FORMULA, 1.20),
        (TypographyRole.TABLE_BODY, 1.20),
    ]
    for role, expected_min_lh in roles_to_test:
        binding = ContentBinding(
            source_id=f"test_{role.value}",
            field_path="text",
            resolved_content_hash="hash",
        )
        res = fit_text_to_region(
            text_or_bullets="Sample text testing role-safe minimum line height ratio constraints.",
            role=role,
            region_width_in=5.0,
            region_height_in=0.60,
            design_dna=standard_dna,
            binding=binding,
        )
        assert res.resolved_role_min_line_height_ratio == expected_min_lh
        assert res.line_height_after >= expected_min_lh - 1e-4

    # Test TITLE via fit_title_to_geometry
    title_res = fit_title_to_geometry(
        title="Sample Academic Presentation Title For Line Height Verification",
        region_width_in=6.0,
        region_height_in=0.60,
        design_dna=standard_dna,
    )
    assert title_res.resolved_role_min_line_height_ratio == 1.08
    assert title_res.line_height_after >= 1.08 - 1e-4


def test_role_safe_line_height_invariant_violation_raises(standard_dna):
    """Validates that constructing a TextFitResult with line_height_after < min floor raises ValueError."""
    spec = resolve_typography_role_spec(TypographyRole.BODY, design_dna=standard_dna)
    with pytest.raises(ValueError, match="Role-safe line height invariant violated"):
        TextFitResult(
            region_id="invalid_lh_region",
            status=TextFitStatus.LINE_HEIGHT_ADJUSTED,
            fit_stage=2,
            typography_before=spec,
            typography_after=spec,
            resolved_role_min_line_height_ratio=1.15,
            line_height_after=1.05,  # Violates 1.15 min floor for BODY!
        )

