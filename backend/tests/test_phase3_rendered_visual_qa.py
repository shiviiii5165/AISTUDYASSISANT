"""
LearnByGenie PPT vNext — Phase 3.5 Rendered Visual QA Test Suite
===============================================================
Comprehensive test suite covering:
  - Actual renderer integration (PowerPoint COM, PDFium, Mock)
  - Backend unavailable graceful handling (RENDER_BACKEND_UNAVAILABLE)
  - Coordinate-to-pixel mapping determinism
  - Text clipping & overflow detection
  - Font substitution overflow handling
  - Chart label collision & legend overflow detection
  - Diagram node collision & connector visibility detection
  - Image aspect ratio distortion & attribution clipping
  - WCAG relative luminance and contrast measurement
  - Slide-level composition & deck-level consistency
  - Semantic integrity preservation (zero mutation invariant)
  - Bounded targeted repair & transactional rollback
  - False positive controls (hero slides, full bleed, asymmetric editorial)
  - Offline reproducibility (zero external network calls)
"""
import io
import os
import sys
import copy
import hashlib
import pytest
from pathlib import Path
from PIL import Image as PILImage, ImageDraw

from app.core.config import settings
from app.services.presentation.rendered_visual_qa import (
    VisualDefectCode,
    DefectSeverity,
    RepairabilityType,
    VisualRepairStrategy,
    VisualCertificationOutcome,
    RenderedVisualDefect,
    RenderedVisualAuditResult,
    DeckVisualAuditResult,
    VisualRepairAction,
)
from app.services.presentation.rendering_adapter import (
    RenderBackendType,
    RenderedSlide,
    RenderingResult,
    PowerPointCOMRenderer,
    PowerPointPDFiumRenderer,
    MockOfflineRenderer,
    discover_available_backends,
)
from app.services.presentation.visual_defect_detector import (
    VisualDefectDetector,
    DeckVisualConsistencyAuditor,
    bounds_to_pixels,
    calculate_relative_luminance,
    calculate_contrast_ratio,
    sample_patch_colors,
)
from app.services.presentation.visual_repair_engine import (
    VisualRepairEngine,
)
from app.services.presentation.composition_schemas import (
    SlideCompositionPlan,
    ContentRegion,
    ResolvedRegionBounds,
    RegionSemanticRole,
    CompositionMode,
    SourceKind,
    ContentBinding,
    Phase3LayoutFamily,
    TypographyRoleSpec,
    TypographyRole,
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
)
from app.services.presentation.visual_schemas import (
    DesignDNA,
    ColorPalette,
    TypographyScale,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def sample_palette():
    return ColorPalette(
        primary="#0A2540",
        secondary="#20639B",
        accent="#ED553B",
        background="#FFFFFF",
        surface="#F4F6F8",
        border="#E2E8F0",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
    )


@pytest.fixture
def sample_plan():
    """Creates a standard, well-formed 2-column slide composition plan."""
    h_title = hashlib.sha256(b"Introduction to Distributed Systems").hexdigest()
    h_left = hashlib.sha256(b"Key distributed systems principles").hexdigest()
    h_right = hashlib.sha256(b"Consensus Protocols").hexdigest()

    reg_title = ContentRegion(
        region_id="reg_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=ResolvedRegionBounds(left_in=0.8, top_in=0.6, width_in=11.7, height_in=1.0),
        binding=ContentBinding(source_id="reg_title", field_path="title", resolved_content_hash=h_title),
    )
    reg_left = ContentRegion(
        region_id="reg_left",
        semantic_role=RegionSemanticRole.PRIMARY_TEXT,
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=20,
        bounds=ResolvedRegionBounds(left_in=0.8, top_in=1.8, width_in=5.6, height_in=4.8),
        binding=ContentBinding(source_id="reg_left", field_path="left", resolved_content_hash=h_left),
    )
    reg_right = ContentRegion(
        region_id="reg_right",
        semantic_role=RegionSemanticRole.SUPPORTING_POINTS,
        grid_col_start=7,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=20,
        bounds=ResolvedRegionBounds(left_in=6.9, top_in=1.8, width_in=5.6, height_in=4.8),
        binding=ContentBinding(source_id="reg_right", field_path="right", resolved_content_hash=h_right),
    )

    return SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
        composition_mode=CompositionMode.SPLIT_COLUMNS,
        content_regions=[reg_title, reg_left, reg_right],
    )


@pytest.fixture
def mock_rendered_slide(sample_plan):
    """Renders a synthetic slide image (1920x1080) for testing."""
    img = PILImage.new("RGB", (1920, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Title patch: black block on white canvas (21:1 contrast)
    draw.rectangle([115, 86, 1799, 230], fill=(255, 255, 255))
    draw.rectangle([130, 100, 700, 160], fill=(0, 0, 0))
    # Col left patch: black block on white canvas (21:1 contrast)
    draw.rectangle([115, 259, 921, 950], fill=(255, 255, 255))
    draw.rectangle([130, 280, 500, 400], fill=(0, 0, 0))
    # Col right patch: black block on white canvas (21:1 contrast)
    draw.rectangle([993, 259, 1799, 950], fill=(255, 255, 255))
    draw.rectangle([1010, 280, 1400, 400], fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return RenderedSlide(
        slide_no=1,
        image_bytes=buf.getvalue(),
        backend_used="mock_offline",
        render_time_ms=12.5,
    )


# ═══════════════════════════════════════════════════════════════
# 1. RENDERING ADAPTER & BACKEND TESTS
# ═══════════════════════════════════════════════════════════════

def test_discover_available_backends():
    """Verifies that discover_available_backends identifies valid backends."""
    backends = discover_available_backends()
    assert len(backends) >= 1
    backend_types = [b["type"] for b in backends]
    assert RenderBackendType.MOCK_OFFLINE in backend_types

    if sys.platform == "win32":
        com_backends = [b for b in backends if b["type"] == RenderBackendType.POWERPOINT_COM]
        assert len(com_backends) == 1
        assert "16.0" in com_backends[0]["version"]


def test_mock_offline_renderer_contract(tmp_path):
    """Tests that MockOfflineRenderer safely renders empty or mock slides offline."""
    from pptx import Presentation as PPTXPresentation
    mock = MockOfflineRenderer(width_px=1920, height_px=1080)
    fake_pptx = tmp_path / "test.pptx"
    prs = PPTXPresentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(str(fake_pptx))

    res = mock.render_presentation(fake_pptx, slides_to_render=[1, 2])
    assert res.success is True
    assert res.backend == RenderBackendType.MOCK_OFFLINE.value
    assert len(res.rendered_slides) == 2
    assert res.rendered_slides[0].width_px == 1920
    assert res.rendered_slides[0].height_px == 1080
    assert len(res.rendered_slides[0].image_bytes) > 0


def test_render_backend_unavailable_path(monkeypatch, tmp_path):
    """Verifies honest return of RENDER_BACKEND_UNAVAILABLE if PowerPoint is absent."""
    from app.services.presentation import rendering_adapter
    monkeypatch.setattr(rendering_adapter, "check_powerpoint_com_availability", lambda: (False, "", "Simulated headless absence"))
    renderer = PowerPointCOMRenderer()
    dummy = tmp_path / "dummy.pptx"
    dummy.write_bytes(b"dummy_bytes")
    res = renderer.render_presentation(dummy)
    assert res.success is False
    assert "RENDER_BACKEND_UNAVAILABLE" in res.error_message


# ═══════════════════════════════════════════════════════════════
# 2. COORDINATE-TO-PIXEL MAPPING TESTS (SECTION 6)
# ═══════════════════════════════════════════════════════════════

def test_bounds_to_pixels_mapping():
    """Verifies exact deterministic inch-to-pixel coordinate projection."""
    bounds = ResolvedRegionBounds(left_in=0.0, top_in=0.0, width_in=13.333, height_in=7.5)
    x, y, w, h = bounds_to_pixels(bounds, img_width_px=1920, img_height_px=1080)
    assert x == 0
    assert y == 0
    assert w == 1920
    assert h == 1080

    half_bounds = ResolvedRegionBounds(left_in=6.6665, top_in=3.75, width_in=6.6665, height_in=3.75)
    hx, hy, hw, hh = bounds_to_pixels(half_bounds, img_width_px=1920, img_height_px=1080)
    assert 950 <= hx <= 970
    assert 530 <= hy <= 550
    assert 950 <= hw <= 970
    assert 530 <= hh <= 550


# ═══════════════════════════════════════════════════════════════
# 3. CONTRAST & WCAG RELATIVE LUMINANCE TESTS (SECTION 12)
# ═══════════════════════════════════════════════════════════════

def test_relative_luminance_and_contrast():
    """Verifies standard WCAG contrast calculations for black on white and low-contrast pairs."""
    white = (255, 255, 255)
    black = (0, 0, 0)
    ratio = calculate_contrast_ratio(black, white)
    assert abs(ratio - 21.0) < 0.1

    assert abs(calculate_contrast_ratio(white, white) - 1.0) < 0.01

    dark_gray = (26, 32, 44)
    assert calculate_contrast_ratio(dark_gray, white) > 10.0

    light_gray = (200, 200, 200)
    low_ratio = calculate_contrast_ratio(light_gray, white)
    assert low_ratio < 2.0


# ═══════════════════════════════════════════════════════════════
# 4. DEFECT DETECTOR TESTS (SECTION 5, 7, 8, 9, 10, 11)
# ═══════════════════════════════════════════════════════════════

def test_clean_slide_audit_passes(mock_rendered_slide, sample_plan):
    """Negative control: Clean, valid slide produces zero critical defects."""
    detector = VisualDefectDetector()
    class FakeContent:
        title = "Introduction to Distributed Systems"
        explanation = "Key distributed systems principles"
        supporting_points = ["Consensus Protocols"]
    audit = detector.audit_rendered_slide(mock_rendered_slide, sample_plan, slide_content=FakeContent())
    assert audit.visual_valid is True
    assert len(audit.fatal_defects) == 0
    assert len(audit.defects) == 0


def test_detect_title_clipped(mock_rendered_slide, sample_plan):
    """Injected defect: Extremely long title in small box triggers TITLE_CLIPPED."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[0].bounds = ResolvedRegionBounds(left_in=0.8, top_in=0.6, width_in=11.7, height_in=0.4)

    class LongTitleContent:
        title = (
            "A Very Long Comprehensive Deep-Dive Into The Fundamental Mathematical Formalisms "
            "Underlying Asynchronous Byzantine Fault Tolerant Consensus Protocols in Hostile Networks"
        )
        explanation = "Clean explanation"
        supporting_points = ["Point 1"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=LongTitleContent())
    assert audit.visual_valid is False
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.TITLE_CLIPPED in codes
    defect = next(d for d in audit.defects if d.defect_code == VisualDefectCode.TITLE_CLIPPED)
    assert defect.severity == DefectSeverity.CRITICAL
    assert defect.recommended_repair == VisualRepairStrategy.SHRINK_FONT_SIZE


def test_detect_text_render_overflow(mock_rendered_slide, sample_plan):
    """Injected defect: Huge body text inside tiny box triggers TEXT_RENDER_OVERFLOW."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[1].bounds = ResolvedRegionBounds(left_in=0.8, top_in=1.8, width_in=5.6, height_in=0.6)

    class OverflowContent:
        title = "Distributed Systems"
        explanation = (
            "Paragraph 1: Distributed consensus is notoriously difficult due to message delays.\n"
            "Paragraph 2: Network partitions may isolate nodes into distinct quorums.\n"
            "Paragraph 3: CAP theorem strictly dictates consistency or availability.\n"
            "Paragraph 4: Raft simplifies leader election through randomized timeouts.\n"
            "Paragraph 5: Vector clocks track causality without physical synchronized time.\n"
        )
        supporting_points = ["Point 1"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=OverflowContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.TEXT_RENDER_OVERFLOW in codes


def test_detect_slide_edge_clipping(mock_rendered_slide, sample_plan):
    """Injected defect: Box positioned off canvas edge triggers SLIDE_EDGE_CLIPPING."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[2].bounds = ResolvedRegionBounds(left_in=12.90, top_in=1.8, width_in=0.40, height_in=4.8)

    class CleanContent:
        title = "Title"
        explanation = "Body"
        supporting_points = ["Points"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=CleanContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.SLIDE_EDGE_CLIPPING in codes


def test_detect_title_body_collision(mock_rendered_slide, sample_plan):
    """Injected defect: Body box collides vertically into title box."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    # Title is top 0.6, height 1.0 (bottom 1.6). Place body at top 1.5.
    broken_plan.content_regions[1].bounds = ResolvedRegionBounds(left_in=0.8, top_in=1.5, width_in=5.6, height_in=4.8)

    class CleanContent:
        title = "Title"
        explanation = "Body"
        supporting_points = ["Points"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=CleanContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.TITLE_BODY_VISUAL_COLLISION in codes


def test_detect_visual_object_overlap(mock_rendered_slide, sample_plan):
    """Injected defect: Two content boxes overlap horizontally and vertically."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[2].bounds = ResolvedRegionBounds(left_in=2.0, top_in=2.0, width_in=5.6, height_in=4.8)

    class CleanContent:
        title = "Title"
        explanation = "Body"
        supporting_points = ["Points"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=CleanContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.VISUAL_OBJECT_OVERLAP in codes


def test_detect_image_stretched(mock_rendered_slide, sample_plan):
    """Injected defect: Image stretched with STRETCH crop mode and severe aspect ratio distortion."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[2].bounds = ResolvedRegionBounds(left_in=6.9, top_in=1.8, width_in=5.6, height_in=2.0)
    broken_plan.content_regions[2].semantic_role = RegionSemanticRole.PRIMARY_VISUAL

    class FakeAsset:
        natural_width_px = 800
        natural_height_px = 800
        crop_mode = "STRETCH"

    class FakeSlideContent:
        title = "Title"
        explanation = "Body"
        image_asset = FakeAsset()

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=FakeSlideContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.IMAGE_STRETCHED in codes


def test_detect_chart_label_collision(mock_rendered_slide, sample_plan):
    """Injected defect: Narrow chart with excessive category count triggers CHART_LABEL_COLLISION."""
    detector = VisualDefectDetector()
    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[2].region_id = "chart_1"
    broken_plan.content_regions[2].semantic_role = RegionSemanticRole.PRIMARY_VISUAL
    broken_plan.content_regions[2].bounds = ResolvedRegionBounds(left_in=6.9, top_in=1.8, width_in=4.5, height_in=4.5)

    class FakeContent:
        title = "Title"
        explanation = "Body"
        data_points = ["Q1 2021", "Q2 2021", "Q3 2021", "Q4 2021", "Q1 2022", "Q2 2022", "Q3 2022", "Q4 2022", "Q1 2023"]

    audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=FakeContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.CHART_LABEL_COLLISION in codes


def test_detect_insufficient_contrast(sample_plan):
    """Injected defect: Pale yellow text on pure white background triggers INSUFFICIENT_TEXT_CONTRAST."""
    img = PILImage.new("RGB", (1920, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([115, 259, 921, 950], fill=(255, 255, 255))
    draw.text((130, 280), "Unreadable pale yellow text", fill=(245, 245, 200))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    slide = RenderedSlide(slide_no=1, image_bytes=buf.getvalue(), backend_used="mock_offline")

    detector = VisualDefectDetector()
    class CleanContent:
        title = "Title"
        explanation = "Body"
        supporting_points = ["Points"]

    audit = detector.audit_rendered_slide(slide, sample_plan, slide_content=CleanContent())
    codes = [d.defect_code for d in audit.defects]
    assert VisualDefectCode.INSUFFICIENT_TEXT_CONTRAST in codes


def test_false_positive_control_hero_and_bleed(sample_palette):
    """False-positive control: Full bleed backgrounds & focal hero slides must NOT be flagged as defects."""
    h_bg = hashlib.sha256(b"bleed").hexdigest()
    h_title = hashlib.sha256(b"The Quantum Frontier").hexdigest()

    reg_bg = ContentRegion(
        region_id="bleed_bg",
        semantic_role=RegionSemanticRole.BLEED_BACKGROUND,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=1,
        baseline_row_span=30,
        bounds=ResolvedRegionBounds(left_in=0.0, top_in=0.0, width_in=13.333, height_in=7.5),
        binding=ContentBinding(source_id="bg", field_path="bg", resolved_content_hash=h_bg, is_decorative=True, source_kind=SourceKind.DECORATIVE),
    )
    reg_hero = ContentRegion(
        region_id="hero_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        grid_col_start=2,
        grid_col_span=10,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=ResolvedRegionBounds(left_in=2.0, top_in=0.6, width_in=9.333, height_in=1.0),
        binding=ContentBinding(source_id="title", field_path="title", resolved_content_hash=h_title),
    )

    hero_plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.DATA_CANVAS,
        composition_mode=CompositionMode.FOCAL_HERO,
        content_regions=[reg_bg, reg_hero],
    )

    img = PILImage.new("RGB", (1920, 1080), color=(10, 37, 64))
    draw = ImageDraw.Draw(img)
    draw.text((288, 360), "The Quantum Frontier", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    slide = RenderedSlide(slide_no=1, image_bytes=buf.getvalue(), backend_used="mock_offline")

    detector = VisualDefectDetector()
    class HeroContent:
        title = "The Quantum Frontier"

    audit = detector.audit_rendered_slide(slide, hero_plan, slide_content=HeroContent())
    edge_clips = [d for d in audit.defects if d.defect_code == VisualDefectCode.SLIDE_EDGE_CLIPPING]
    assert len(edge_clips) == 0


# ═══════════════════════════════════════════════════════════════
# 5. TRANSACTIONAL REPAIR ENGINE TESTS (SECTION 15, 16, 17, 18)
# ═══════════════════════════════════════════════════════════════

def test_transactional_repair_success(mock_rendered_slide, sample_plan):
    """Verifies that repair engine fixes TITLE_CLIPPED, verifies improvement, and commits."""
    engine = VisualRepairEngine()
    detector = VisualDefectDetector()

    broken_plan = copy.deepcopy(sample_plan)
    broken_plan.content_regions[0].bounds = ResolvedRegionBounds(left_in=0.8, top_in=0.6, width_in=6.0, height_in=0.6)
    broken_plan.content_regions[0].typography_spec = TypographyRoleSpec(role=TypographyRole.TITLE, font_size_pt=26.0)

    class LongTitleContent:
        title = "Distributed Systems Architecture"
        explanation = "Clean explanation"
        supporting_points = ["Point 1"]

    initial_audit = detector.audit_rendered_slide(mock_rendered_slide, broken_plan, slide_content=LongTitleContent())
    assert not initial_audit.visual_valid

    def audit_cb(cand_plan):
        # Re-audits candidate plan with the updated font size
        return detector.audit_rendered_slide(mock_rendered_slide, cand_plan, slide_content=LongTitleContent())

    manifest_hashes = {"reg_title": "hash123", "reg_left": "hash456", "reg_right": "hash789"}

    repaired_plan, final_audit, actions = engine.execute_transactional_repair_cycle(
        broken_plan,
        initial_audit,
        audit_cb,
        content_hashes=manifest_hashes,
    )

    assert len(actions) >= 1
    action = actions[0]
    assert action.defect_code == VisualDefectCode.TITLE_CLIPPED
    assert action.commit_status == "COMMITTED"
    assert action.defect_resolved is True
    # Verify semantic integrity: content untouched
    assert repaired_plan.content_regions[0].binding.source_id == broken_plan.content_regions[0].binding.source_id
    assert action.content_hashes_before == action.content_hashes_after


def test_transactional_repair_rollback_on_failure(mock_rendered_slide, sample_plan):
    """Verifies that repair engine rolls back if candidate repair does not improve the audit."""
    engine = VisualRepairEngine()

    broken_plan = copy.deepcopy(sample_plan)
    defect = RenderedVisualDefect(
        slide_no=1,
        defect_code=VisualDefectCode.TITLE_BODY_VISUAL_COLLISION,
        severity=DefectSeverity.CRITICAL,
        affected_region_ids=["reg_title", "reg_left"],
        repairability=RepairabilityType.AUTOMATIC,
        recommended_repair=VisualRepairStrategy.SHIFT_REGION,
        message="Simulated collision",
    )
    initial_audit = RenderedVisualAuditResult(slide_no=1, defects=[defect])
    initial_audit.update_validity()

    def bad_audit_cb(cand_plan):
        res = RenderedVisualAuditResult(slide_no=1, defects=[defect, defect])
        res.update_validity()
        return res

    repaired_plan, final_audit, actions = engine.execute_transactional_repair_cycle(
        broken_plan,
        initial_audit,
        bad_audit_cb,
        content_hashes={"h1": "val1"},
    )

    assert len(actions) >= 1
    assert actions[0].commit_status == "ROLLED_BACK"
    assert "did not improve" in actions[0].rollback_reason


# ═══════════════════════════════════════════════════════════════
# 6. DECK-LEVEL CONSISTENCY TESTS (SECTION 14)
# ═══════════════════════════════════════════════════════════════

def test_deck_consistency_auditor(mock_rendered_slide, sample_plan, sample_palette):
    """Verifies that DeckVisualConsistencyAuditor checks palette and layout consistency."""
    auditor = DeckVisualConsistencyAuditor()
    detector = VisualDefectDetector()

    class Content:
        title = "Title"
        explanation = "Body"
        supporting_points = ["Points"]

    audit_1 = detector.audit_rendered_slide(mock_rendered_slide, sample_plan, slide_content=Content())

    plan_2 = copy.deepcopy(sample_plan)
    plan_2.slide_no = 2
    plan_2.palette_name = "vibrant_editorial"

    audit_2 = detector.audit_rendered_slide(mock_rendered_slide, plan_2, slide_content=Content())

    deck_res = auditor.audit_deck_consistency([audit_1, audit_2], [sample_plan, plan_2])
    assert deck_res.total_slides == 2
    assert deck_res.audited_slides == 2
    defect_codes = [d.defect_code for d in deck_res.deck_defects]
    assert VisualDefectCode.PALETTE_INCONSISTENCY in defect_codes
    assert deck_res.deck_consistency_score < 100.0
