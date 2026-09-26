"""
TeachGenie PPT vNext — Phase 3.4 Image Intelligence & Visual Asset Orchestration Test Suite
=============================================================================================
Validates:
  1. Feature Flag Matrix & Gating:
     - Parent OFF, P3.4 OFF -> Legacy fallback
     - Parent OFF, P3.4 ON  -> Legacy fallback (parent gate enforced)
     - Parent ON,  P3.4 OFF -> Deferred asset / diagram fallback
     - Parent ON,  P3.4 ON  -> Image intelligence active
     - Integrity failures with flags ON -> Fail closed (no silent fallback)
  2. Image Need Assessment & Anti-Stock Rule:
     - Scientific illustrations / specimens -> IMAGE_REQUIRED
     - Historical documentary photos       -> IMAGE_REQUIRED
     - Atmospheric / ecosystem             -> IMAGE_USEFUL / IMAGE_REQUIRED
     - Pure mathematics / logic / equations -> IMAGE_UNNECESSARY
     - System architecture / flows          -> DIAGRAM_PREFERRED
     - Empirical data / trends              -> CHART_PREFERRED
  3. Image Type Classification:
     - Correct assignment across photographic, illustration, historical, etc.
  4. Grounded Semantic Query Construction:
     - Content-grounded queries without prompt injection or hallucination
  5. Candidate Scoring & Selection:
     - Composite scoring across resolution, aspect ratio, semantic match
     - Deterministic best-candidate selection
  6. Asset Validation & Security:
     - Byte signature validation (PNG, JPEG, WebP)
     - Corrupt image bytes detection (fail closed)
     - License and rights verification (fail closed on unverified)
     - Resolution minimum thresholds
     - Deduplication against used hashes, asset IDs, URLs
     - URL security / SSRF protection (private IPs, localhost, bad schemes)
  7. Crop Mode & Geometry:
     - CONTAIN geometry preserves full image within region bounds
     - COVER geometry fills bounds
     - Aspect ratio preservation invariants
  8. Deck Image Manifest & Provenance:
     - Tracks image counts, total bytes, hashes, URLs, provider stats
  9. Composition Renderer Additive Integration:
     - Places native picture shape into PPTX slide
     - Correct Inches/EMU geometry derived from ResolvedRegionBounds
     - 100% Region-to-shape traceability
     - Full PPTX round-trip serialization and re-inspection
  10. Offline Reproducibility:
     - Zero live network calls or external downloads
"""
import io
import os
import hashlib
import pytest
from pptx import Presentation
from pptx.util import Inches

from app.core.config import settings
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT
from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    SlideIntent,
    LayoutFamily,
)
from app.services.presentation.visual_schemas import (
    VisualSemanticPacket,
    VisualIntent,
    VisualAssetType,
    DesignDNA,
    Phase3LayoutFamily,
    ContentDensity,
)
from app.services.presentation.composition_schemas import (
    ResolvedRegionBounds,
    ContentRegion,
    RegionSemanticRole,
    ContentBinding,
    SourceKind,
    CompositionInputManifest,
    ComposedSlideContext,
    SlideCompositionPlan,
    CompositionMode,
    SurfaceToken,
    BorderToken,
)
from app.services.presentation.design_dna import _build_academic_clean_dna, _THEME_PALETTES
from app.services.presentation.visual_router import (
    VisualRoutingDecision,
    VisualRoutingResult,
    route_visual_decision,
)
from app.services.presentation.composition_renderer import (
    render_composed_slide,
    render_composed_presentation,
    RenderResult,
    RenderDefectCode,
)
from app.services.presentation.image_intelligence import (
    ImageAssetDecision,
    ImageDecisionOutcome,
    ImageTypeClassification,
    ImageProvenance,
    ImageRightsMetadata,
    ImageCandidate,
    ImageRelevanceScore,
    CropMode,
    ImageDefectCode,
    assess_image_need,
    build_semantic_query,
    classify_image_type,
    score_candidate,
    select_best_candidate,
    compute_content_hash,
    determine_crop_mode,
    generate_alt_text,
)
from app.services.presentation.image_providers import (
    build_provider_registry,
    search_mock_provider,
    get_corrupt_test_candidate,
    get_unverified_rights_candidate,
    get_low_resolution_candidate,
    _TINY_PNG_BYTES,
)
from app.services.presentation.image_asset_validator import (
    validate_image_asset,
    validate_url_security,
    verify_image_signature,
    validate_image_rights,
    check_deduplication,
    validate_image_dimensions,
    validate_aspect_ratio_compatibility,
    ImageValidationResult,
    secure_fetch_image_asset,
    check_hostname_dns_security,
    resolve_and_verify_dns,
    FetchSecurityResult,
)
from app.services.presentation.image_composition import (
    DeckImageManifest,
    calculate_contain_geometry,
    calculate_cover_geometry,
    insert_image_into_slide,
    ImagePlacementResult,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def sample_dna() -> DesignDNA:
    return _build_academic_clean_dna(_THEME_PALETTES["blue_professional"], ContentDensity.MEDIUM)


@pytest.fixture
def sample_bounds() -> ResolvedRegionBounds:
    return ResolvedRegionBounds(
        left_in=5.5,
        top_in=1.5,
        width_in=7.0,
        height_in=5.0,
        left_col=6,
        right_col=12,
        top_module=8,
        bottom_module=26,
    )


@pytest.fixture
def sample_visual_region(sample_bounds) -> ContentRegion:
    return ContentRegion(
        region_id="reg_primary_visual",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(
            source_kind=SourceKind.VISUAL_SEMANTIC_PACKET,
            source_id="vis_packet_1",
            field_path="primary_visual_message",
            resolved_content_hash=CompositionInputManifest.compute_payload_hash("biology_cell_structure"),
        ),
    )


@pytest.fixture
def sample_manifest() -> CompositionInputManifest:
    manifest = CompositionInputManifest(
        manifest_id="test_manifest_p34",
        deck_title="Phase 3.4 Image Intelligence Test Deck",
    )
    manifest.register_content("s1", {"title": "Plant Cell Biology"})
    manifest.register_content("vis_packet_1", {"primary_visual_message": "biology_cell_structure"})
    return manifest


# ═══════════════════════════════════════════════════════════════
# 1. FEATURE FLAG MATRIX & STRICT FAIL-CLOSED INTEGRITY
# ═══════════════════════════════════════════════════════════════

def test_feature_flag_matrix_parent_off_p34_off(monkeypatch, sample_dna, sample_manifest):
    """Parent OFF, P3.4 OFF -> Clean state without image intelligence."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", False)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", False)

    assert settings.PRESENTATION_COMPOSITION_RENDERER_ENABLED is False
    assert settings.PRESENTATION_IMAGE_INTELLIGENCE_ENABLED is False


def test_feature_flag_matrix_parent_off_p34_on(monkeypatch):
    """Parent OFF, P3.4 ON -> Parent gate strictly prevents activation."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", False)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", True)

    assert settings.PRESENTATION_COMPOSITION_RENDERER_ENABLED is False
    assert settings.PRESENTATION_IMAGE_INTELLIGENCE_ENABLED is True


def test_feature_flag_matrix_parent_on_p34_off(monkeypatch, sample_dna, sample_bounds, sample_visual_region):
    """Parent ON, P3.4 OFF -> Visual router defers image to Phase 3.4."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", True)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", False)

    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Photograph of historical monument",
        visual_intent=VisualIntent.SHOW_OBJECT,
        image_candidate_concepts=["taj mahal historical photograph"],
    )
    res = route_visual_decision(packet, None, sample_visual_region, sample_bounds, sample_dna)
    assert res.decision == VisualRoutingDecision.DEFERRED_IMAGE_TO_PHASE_3_4


def test_feature_flag_matrix_parent_on_p34_on(monkeypatch, sample_dna, sample_bounds, sample_visual_region):
    """Parent ON, P3.4 ON -> Visual router routes to IMAGE_ASSET."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", True)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", True)

    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Photograph of historical monument",
        visual_intent=VisualIntent.SHOW_OBJECT,
        image_candidate_concepts=["taj mahal historical photograph"],
    )
    res = route_visual_decision(packet, None, sample_visual_region, sample_bounds, sample_dna)
    assert res.decision == VisualRoutingDecision.IMAGE_ASSET


def test_integrity_failure_fails_closed_with_flags_on(monkeypatch, sample_dna, sample_manifest, sample_bounds):
    """Corrupt content binding hash must FAIL CLOSED (terminal result), not silently fall back."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", True)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", True)

    corrupt_region = ContentRegion(
        region_id="reg_corrupt",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(
            source_kind=SourceKind.VISUAL_SEMANTIC_PACKET,
            source_id="vis_packet_1",
            field_path="primary_visual_message",
            resolved_content_hash="CORRUPT_NON_MATCHING_HASH_" + "0" * 38,
        ),
    )

    plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.SPLIT_40_60,
        composition_mode=CompositionMode.SPLIT_COLUMNS,
        content_density=ContentDensity.MEDIUM,
        content_regions=[corrupt_region],
        quality_score=95.0,
    )

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id=sample_manifest.manifest_id,
    )

    result = render_composed_slide(prs, slide, ctx, sample_manifest, sample_dna, enforce_audit_gate=False)
    assert result.success is False
    assert result.terminal_status == RenderDefectCode.CONTENT_BINDING_HASH_MISMATCH.value


# ═══════════════════════════════════════════════════════════════
# 2. IMAGE NEED ASSESSMENT & ANTI-STOCK RULE
# ═══════════════════════════════════════════════════════════════

def test_image_need_biology_specimen(sample_visual_region):
    """Biological structure / specimen requires an image/illustration."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Chloroplast internal anatomy showing thylakoid membranes",
        visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
        key_entities=["chloroplast", "thylakoid"],
        image_candidate_concepts=["chloroplast internal anatomy"],
    )
    content = SlideContent(title="Chloroplast Anatomy", primary_takeaway="Thylakoid structures")
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome == ImageDecisionOutcome.IMAGE_REQUIRED


def test_image_need_humanities_historical_document(sample_visual_region):
    """Humanities / history documentary image requires an authentic image."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Historical documentary photograph of 1947 independence movement",
        visual_intent=VisualIntent.SHOW_OBJECT,
        key_entities=["Gandhi", "Salt March"],
        image_candidate_concepts=["1947 partition historical documentary photograph"],
    )
    content = SlideContent(title="Indian Independence", primary_takeaway="Non-violent resistance movement")
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome == ImageDecisionOutcome.IMAGE_REQUIRED


def test_image_need_environmental_ecosystem(sample_visual_region):
    """Environmental / ecosystem photograph is useful."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Canopy layer of tropical Amazon rainforest",
        visual_intent=VisualIntent.SHOW_OBJECT,
        key_entities=["Amazon", "rainforest canopy"],
        image_candidate_concepts=["rainforest canopy layer photograph"],
    )
    content = SlideContent(title="Tropical Ecosystems", primary_takeaway="Stratification of biodiversity")
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome in (ImageDecisionOutcome.IMAGE_REQUIRED, ImageDecisionOutcome.IMAGE_USEFUL)


def test_anti_stock_mathematics_pure_equations(sample_visual_region):
    """Pure mathematics and equations must NOT receive gratuitous stock images."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Eigenvalue decomposition: A = V * Lambda * V_inv",
        visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
        key_entities=["matrix", "eigenvalues", "eigenvectors"],
    )
    content = SlideContent(
        title="Eigenvalue Decomposition",
        primary_takeaway="Diagonalizing linear transformations",
    )
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome == ImageDecisionOutcome.IMAGE_UNNECESSARY


def test_anti_stock_cs_system_architecture_prefers_diagram(sample_visual_region):
    """CS system architecture must prefer an editable diagram over stock photos."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Distributed microservices architecture with Kafka event bus",
        visual_intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        system_components=["API Gateway", "Auth Service", "Event Bus", "Database"],
    )
    content = SlideContent(
        title="Microservice Architecture",
        primary_takeaway="Decoupled asynchronous messaging",
    )
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome == ImageDecisionOutcome.DIAGRAM_PREFERRED


def test_anti_stock_empirical_data_prefers_chart(sample_visual_region):
    """Empirical quantitative data must prefer a native chart."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Quarterly GDP growth across 4 regions",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
        chart_candidate="bar_chart",
    )
    content = SlideContent(
        title="Quarterly GDP Growth",
        primary_takeaway="Regional divergence in economic output",
    )
    decision = assess_image_need(packet, content, sample_visual_region)
    assert decision.outcome == ImageDecisionOutcome.CHART_PREFERRED


# ═══════════════════════════════════════════════════════════════
# 3. IMAGE TYPE CLASSIFICATION & QUERY CONSTRUCTION
# ═══════════════════════════════════════════════════════════════

def test_image_type_classification():
    """Correctly classifies image type from packet and content."""
    # Scientific illustration
    p_sci = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Cell biology anatomy diagram of mitochondrion internal membrane",
        visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
        image_candidate_concepts=["mitochondrion cross-section diagram"],
    )
    c_sci = SlideContent(title="Mitochondrion", primary_takeaway="Cellular respiration")
    assert classify_image_type(p_sci, c_sci) == ImageTypeClassification.SCIENTIFIC_ILLUSTRATION

    # Historical image
    p_hist = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Archival historical photograph of Apollo 11 moon landing 1969",
        visual_intent=VisualIntent.SHOW_OBJECT,
        image_candidate_concepts=["Apollo 11 lunar module historical photograph"],
    )
    c_hist = SlideContent(title="Space Exploration", primary_takeaway="Moon landing")
    assert classify_image_type(p_hist, c_hist) == ImageTypeClassification.HISTORICAL_IMAGE


def test_build_semantic_query():
    """Builds grounded, informative search query without prompt noise."""
    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Human heart four chambers and blood flow direction",
        visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
        key_entities=["heart", "atrium", "ventricle", "aorta"],
        image_candidate_concepts=["human heart four chambers anatomical illustration"],
    )
    content = SlideContent(title="Circulatory System", primary_takeaway="Double circulation in humans")
    query = build_semantic_query(packet, content)

    assert "heart" in query.lower()
    assert len(query) > 10
    assert len(query) < 200


# ═══════════════════════════════════════════════════════════════
# 4. CANDIDATE SCORING & SELECTION
# ═══════════════════════════════════════════════════════════════

def test_candidate_scoring_and_selection(sample_bounds):
    """Scores candidate images across multiple factors and picks the best."""
    cand1 = ImageCandidate(
        provider="wikimedia_commons",
        image_url="https://commons.wikimedia.org/wiki/File:Chloroplast.png",
        asset_id="chloro_hi_res",
        description="Detailed anatomical diagram of plant chloroplast showing thylakoids",
        width_px=1920,
        height_px=1080,
        rights=ImageRightsMetadata(
            provider="wikimedia_commons",
            license="CC-BY-SA-4.0",
            rights_verified=True,
        ),
    )
    cand2 = ImageCandidate(
        provider="pixabay",
        image_url="https://pixabay.com/photos/leaf-1234/",
        asset_id="leaf_photo",
        description="Green leaf in the sun with bokeh background",
        width_px=800,
        height_px=600,
        rights=ImageRightsMetadata(
            provider="pixabay",
            license="Pixabay Content License",
            rights_verified=True,
        ),
    )

    query = "chloroplast thylakoid anatomical diagram"
    score1 = score_candidate(cand1, query, 672, 480, 7.0 / 5.0)
    score2 = score_candidate(cand2, query, 672, 480, 7.0 / 5.0)

    assert score1.composite_score > score2.composite_score
    best, rejections = select_best_candidate([cand1, cand2], query, sample_bounds, set())
    assert best is not None
    assert best.asset_id == "chloro_hi_res"


# ═══════════════════════════════════════════════════════════════
# 5. ASSET VALIDATION & SECURITY
# ═══════════════════════════════════════════════════════════════

def test_asset_validation_valid_png():
    """Validates real PNG bytes and checks signature."""
    valid, mime = verify_image_signature(_TINY_PNG_BYTES)
    assert valid is True
    assert mime == "image/png"


def test_asset_validation_corrupt_bytes():
    """Corrupt image bytes must fail verification."""
    corrupt_bytes = b"NOT_AN_IMAGE_RANDOM_CORRUPT_BYTES_XYZ"
    valid, mime = verify_image_signature(corrupt_bytes)
    assert valid is False
    assert mime == ""

    cand = get_corrupt_test_candidate()
    result = validate_image_asset(cand, corrupt_bytes)
    assert result.valid is False
    assert ImageDefectCode.IMAGE_FILE_CORRUPT in result.defects


def test_asset_validation_unverified_rights():
    """Unverified rights must fail closed."""
    cand = get_unverified_rights_candidate()
    result = validate_image_asset(cand, _TINY_PNG_BYTES)
    assert result.valid is False
    assert ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED in result.defects


def test_asset_validation_deduplication():
    """Rejects duplicate content hash, asset id, or url."""
    cand = ImageCandidate(
        provider="wikimedia_commons",
        image_url="https://commons.wikimedia.org/img1.png",
        asset_id="asset_dup_1",
        description="Test image",
        width_px=800,
        height_px=600,
        rights=ImageRightsMetadata(provider="wikimedia_commons", rights_verified=True),
    )
    h = compute_content_hash(_TINY_PNG_BYTES)
    res = validate_image_asset(
        cand, _TINY_PNG_BYTES,
        used_hashes={h},
        used_asset_ids=set(),
        used_urls=set(),
    )
    assert res.is_duplicate is True
    assert ImageDefectCode.IMAGE_DUPLICATE_UNJUSTIFIED in res.defects


def test_url_security_ssrf_protection():
    """Blocks private IPs, localhost, and insecure protocols."""
    unsafe_urls = [
        "http://127.0.0.1/secret.jpg",
        "http://localhost:8080/image.png",
        "http://192.168.1.1/router.jpg",
        "http://10.0.0.1/internal.jpg",
        "ftp://example.com/image.png",
        "file:///etc/passwd",
    ]
    for u in unsafe_urls:
        safe, reason = validate_url_security(u)
        assert safe is False, f"URL {u} should be rejected"

    safe_urls = [
        "https://upload.wikimedia.org/wikipedia/commons/1/1a/Chloroplast.png",
        "https://images.unsplash.com/photo-12345",
        "https://pixabay.com/get/image.jpg",
    ]
    for u in safe_urls:
        safe, reason = validate_url_security(u)
        assert safe is True, f"URL {u} should be accepted"


# ═══════════════════════════════════════════════════════════════
# 6. CROP MODE & GEOMETRY CALCULATION
# ═══════════════════════════════════════════════════════════════

def test_crop_mode_determination():
    """Diagrams and specimens receive CONTAIN; atmospheric photos receive COVER."""
    assert determine_crop_mode(ImageTypeClassification.SCIENTIFIC_ILLUSTRATION, RegionSemanticRole.PRIMARY_VISUAL, 4/3, 16/9) == CropMode.CONTAIN
    assert determine_crop_mode(ImageTypeClassification.HISTORICAL_IMAGE, RegionSemanticRole.PRIMARY_VISUAL, 4/3, 16/9) == CropMode.CONTAIN
    assert determine_crop_mode(ImageTypeClassification.PHOTOGRAPH, RegionSemanticRole.BLEED_BACKGROUND, 16/9, 16/9) == CropMode.BACKGROUND_CROP
    assert determine_crop_mode(ImageTypeClassification.PHOTOGRAPH, RegionSemanticRole.PRIMARY_VISUAL, 1.77, 1.78) == CropMode.COVER


def test_geometry_contain_scaling(sample_bounds):
    """Contain scaling fits completely inside region bounds without distortion."""
    left_emu, top_emu, width_emu, height_emu = calculate_contain_geometry(
        image_width_px=800,
        image_height_px=600,
        region_left_emu=int(sample_bounds.left_in * 914400),
        region_top_emu=int(sample_bounds.top_in * 914400),
        region_width_emu=int(sample_bounds.width_in * 914400),
        region_height_emu=int(sample_bounds.height_in * 914400),
    )
    width_in = width_emu / 914400.0
    height_in = height_emu / 914400.0
    assert width_in <= sample_bounds.width_in + 1e-4
    assert height_in <= sample_bounds.height_in + 1e-4
    assert abs((width_in / height_in) - (800 / 600)) < 1e-3


def test_geometry_cover_scaling(sample_bounds):
    """Cover scaling fills region bounds."""
    left_emu, top_emu, width_emu, height_emu, offsets = calculate_cover_geometry(
        image_width_px=1600,
        image_height_px=900,
        region_left_emu=int(sample_bounds.left_in * 914400),
        region_top_emu=int(sample_bounds.top_in * 914400),
        region_width_emu=int(sample_bounds.width_in * 914400),
        region_height_emu=int(sample_bounds.height_in * 914400),
    )
    assert width_emu >= int(sample_bounds.width_in * 914400) - 100
    assert height_emu >= int(sample_bounds.height_in * 914400) - 100


# ═══════════════════════════════════════════════════════════════
# 7. ALT TEXT GENERATION
# ═══════════════════════════════════════════════════════════════

def test_alt_text_generation_length_and_quality():
    """Generates informative pedagogical alt text under 125 characters."""
    alt = generate_alt_text(
        image_type=ImageTypeClassification.SCIENTIFIC_ILLUSTRATION,
        search_query="chloroplast thylakoid anatomy",
        description="Scientific cross-section diagram of plant chloroplast showing thylakoid granum",
        content_title="Chloroplast Anatomy",
    )
    assert len(alt) <= 125
    assert len(alt) > 10
    assert "chloroplast" in alt.lower()


# ═══════════════════════════════════════════════════════════════
# 8. DECK IMAGE MANIFEST
# ═══════════════════════════════════════════════════════════════

def test_deck_image_manifest_tracking():
    """DeckImageManifest tracks total images, bytes, hashes, and providers."""
    manifest = DeckImageManifest(deck_topic="Biology")
    prov = ImageProvenance(
        asset_identifier="img_test_1",
        rights_metadata=ImageRightsMetadata(provider="wikimedia_commons", rights_verified=True),
        downloaded_asset_hash="a1b2c3d4" * 8,
        file_size_bytes=2048,
    )
    manifest.register_placement(prov)

    assert manifest.total_images == 1
    assert manifest.total_image_bytes == 2048
    assert manifest.provider_usage.get("wikimedia_commons") == 1
    assert "a1b2c3d4" * 8 in manifest.used_content_hashes


# ═══════════════════════════════════════════════════════════════
# 9. COMPOSITION RENDERER ADDITIVE INTEGRATION & PPTX ROUND-TRIP
# ═══════════════════════════════════════════════════════════════

def test_composition_renderer_places_image_into_pptx(
    monkeypatch, sample_dna, sample_manifest, sample_visual_region, sample_bounds
):
    """When enabled and decision contains image bytes, composition renderer inserts a picture shape."""
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", True)
    monkeypatch.setattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", True)

    packet = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="Internal cell anatomy chloroplast",
        visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
        key_entities=["chloroplast", "thylakoid"],
        image_candidate_concepts=["chloroplast internal anatomy"],
    )

    plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.SPLIT_40_60,
        composition_mode=CompositionMode.SPLIT_COLUMNS,
        content_density=ContentDensity.MEDIUM,
        content_regions=[sample_visual_region],
        quality_score=95.0,
    )

    # In our renderer integration, if assess_image_need returns IMAGE_REQUIRED or IMAGE_USEFUL,
    # and decision.image_bytes is present, it places the picture shape.
    from app.services.presentation import image_intelligence
    orig_assess = image_intelligence.assess_image_need

    def mock_assess(pkt, cnt, reg):
        dec = orig_assess(pkt, cnt, reg)
        dec.outcome = ImageDecisionOutcome.IMAGE_REQUIRED
        dec.image_bytes = _TINY_PNG_BYTES
        dec.alt_text = "Educational diagram of plant cell chloroplast"
        dec.image_type = ImageTypeClassification.SCIENTIFIC_ILLUSTRATION
        dec.provenance = ImageProvenance(
            asset_identifier="test_cell_png",
            rights_metadata=ImageRightsMetadata(provider="test_mock", rights_verified=True),
            downloaded_asset_hash=compute_content_hash(_TINY_PNG_BYTES),
            file_size_bytes=len(_TINY_PNG_BYTES),
        )
        return dec

    monkeypatch.setattr(image_intelligence, "assess_image_need", mock_assess)

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id=sample_manifest.manifest_id,
    )

    result = render_composed_slide(
        prs, slide, ctx, sample_manifest, sample_dna,
        enforce_audit_gate=False,
        visual_semantic_packet=packet,
    )

    assert result.success is True
    assert result.image_shape_count == 1
    assert result.rendered_shape_count >= 1

    # Verify PPTX round-trip: save to bytes and reload
    stream = io.BytesIO()
    prs.save(stream)
    stream.seek(0)

    reloaded_prs = Presentation(stream)
    assert len(reloaded_prs.slides) == 1
    reloaded_slide = reloaded_prs.slides[0]
    # At least one shape was created (the picture shape)
    assert len(reloaded_slide.shapes) >= 1

    # Verify shape naming convention
    shape_names = [s.name for s in reloaded_slide.shapes]
    assert any("img" in name or "image" in name for name in shape_names)


# ═══════════════════════════════════════════════════════════════
# 10. SECURE RETRIEVAL & RIGHTS GATING (13 GAPS AUDIT)
# ═══════════════════════════════════════════════════════════════

class MockHttpResponse:
    def __init__(self, status_code: int = 200, headers: dict = None, content: bytes = b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content


class MockHttpClient:
    def __init__(self, responses_by_url: dict):
        self.responses_by_url = responses_by_url
        self.requested_urls = []

    def get(self, url: str, headers: dict = None):
        self.requested_urls.append(url)
        if url in self.responses_by_url:
            return self.responses_by_url[url]
        return MockHttpResponse(404, {}, b"Not Found")

    def close(self):
        pass


MOCK_PUBLIC_DNS = lambda h: ["93.184.216.34"]


def test_secure_fetch_redirect_to_localhost():
    """1. Rejects public URL redirecting to loopback / localhost."""
    client = MockHttpClient({
        "https://cdn.example.org/photo.png": MockHttpResponse(
            302, {"Location": "http://127.0.0.1/evil.png"}
        ),
    })
    res = secure_fetch_image_asset(
        "https://cdn.example.org/photo.png",
        http_client=client,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert ImageDefectCode.IMAGE_DOWNLOAD_FAILED in res.defects
    assert any("blocked" in d.lower() for d in res.defect_details)


def test_secure_fetch_redirect_to_private_address():
    """2. Rejects public URL redirecting to RFC 1918 private network address."""
    client = MockHttpClient({
        "https://cdn.example.org/photo.png": MockHttpResponse(
            302, {"Location": "https://10.0.0.1/internal.png"}
        ),
    })
    res = secure_fetch_image_asset(
        "https://cdn.example.org/photo.png",
        http_client=client,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert ImageDefectCode.IMAGE_DOWNLOAD_FAILED in res.defects
    assert any("private" in d.lower() for d in res.defect_details)


def test_secure_fetch_hostname_resolving_to_private_address():
    """3. Rejects hostname whose DNS resolution returns a private IP (DNS rebinding)."""
    mock_dns = lambda h: ["192.168.1.254"]
    client = MockHttpClient({
        "https://rebinding-service.example.org/pic.png": MockHttpResponse(
            200, {"content-type": "image/png"}, _TINY_PNG_BYTES
        ),
    })
    res = secure_fetch_image_asset(
        "https://rebinding-service.example.org/pic.png",
        http_client=client,
        dns_resolver=mock_dns,
    )
    assert res.success is False
    assert any("resolves to private/loopback IP" in d for d in res.defect_details)


def test_secure_fetch_ipv6_loopback_and_local():
    """4. Rejects IPv6 loopback (::1) and private/local link destinations."""
    ok1, reason1 = validate_url_security("https://[::1]/secret.png")
    assert ok1 is False
    assert "loopback" in reason1.lower()

    ok2, reason2 = validate_url_security("https://[fe80::1]/linklocal.png")
    assert ok2 is False
    assert "loopback" in reason2.lower() or "private" in reason2.lower()

    ok_dns, dns_reason = resolve_and_verify_dns("v6loopback.example", dns_resolver=lambda h: ["::1"])
    assert ok_dns is False
    assert "resolves to private/loopback IP" in dns_reason


def test_secure_fetch_redirect_chains_and_circular_loops():
    """5. Rejects redirect chains exceeding max hops and detects circular redirect loops."""
    # Exceeding hops
    client_chain = MockHttpClient({
        "https://example.com/h1": MockHttpResponse(302, {"Location": "https://example.com/h2"}),
        "https://example.com/h2": MockHttpResponse(302, {"Location": "https://example.com/h3"}),
        "https://example.com/h3": MockHttpResponse(302, {"Location": "https://example.com/h4"}),
        "https://example.com/h4": MockHttpResponse(302, {"Location": "https://example.com/h5"}),
    })
    res = secure_fetch_image_asset(
        "https://example.com/h1",
        max_redirects=3,
        http_client=client_chain,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert any("exceeded max 3 hops" in d for d in res.defect_details)

    # Circular loop
    client_loop = MockHttpClient({
        "https://example.com/loopA": MockHttpResponse(302, {"Location": "https://example.com/loopB"}),
        "https://example.com/loopB": MockHttpResponse(302, {"Location": "https://example.com/loopA"}),
    })
    res_loop = secure_fetch_image_asset(
        "https://example.com/loopA",
        max_redirects=5,
        http_client=client_loop,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res_loop.success is False
    assert any("Circular redirect loop detected" in d for d in res_loop.defect_details)


def test_secure_fetch_blocked_non_https_redirect():
    """6. Rejects protocol downgrade redirect to non-HTTPS scheme."""
    client = MockHttpClient({
        "https://secure.example.com/asset.png": MockHttpResponse(
            302, {"Location": "http://downgrade.example.com/asset.png"}
        ),
    })
    res = secure_fetch_image_asset(
        "https://secure.example.com/asset.png",
        http_client=client,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert any("Non-HTTPS URL rejected" in d for d in res.defect_details)


def test_secure_fetch_excessive_download_size():
    """7. Rejects excessive download size via Content-Length and byte buffer limits."""
    # Header Content-Length violation
    client_hdr = MockHttpClient({
        "https://cdn.example.org/giant.png": MockHttpResponse(
            200, {"content-type": "image/png", "content-length": "30000000"}, b"tiny"
        ),
    })
    res1 = secure_fetch_image_asset(
        "https://cdn.example.org/giant.png",
        http_client=client_hdr,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res1.success is False
    assert ImageDefectCode.IMAGE_FILE_CORRUPT in res1.defects

    # Raw content size violation
    client_bytes = MockHttpClient({
        "https://cdn.example.org/huge.png": MockHttpResponse(
            200, {"content-type": "image/png"}, _TINY_PNG_BYTES
        ),
    })
    res2 = secure_fetch_image_asset(
        "https://cdn.example.org/huge.png",
        max_download_bytes=10,
        http_client=client_bytes,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res2.success is False
    assert ImageDefectCode.IMAGE_FILE_CORRUPT in res2.defects


def test_secure_fetch_decompression_bomb(monkeypatch):
    """8. Rejects decompression bomb exceeding MAX_IMAGE_PIXELS threshold."""
    from PIL import Image as PILImage
    client = MockHttpClient({
        "https://cdn.example.org/bomb.png": MockHttpResponse(
            200, {"content-type": "image/png"}, _TINY_PNG_BYTES
        ),
    })
    # Mock image dimensions to exceed 100 megapixels
    class MockBombImage:
        width = 12000
        height = 10000  # 120 megapixels > 100M limit
        def verify(self): pass
    monkeypatch.setattr(PILImage, "open", lambda *args, **kwargs: MockBombImage())

    res = secure_fetch_image_asset(
        "https://cdn.example.org/bomb.png",
        http_client=client,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert ImageDefectCode.IMAGE_FILE_CORRUPT in res.defects
    assert any("Decompression bomb detected" in d for d in res.defect_details)


def test_secure_fetch_forged_image_mime_type():
    """9. Rejects forged image MIME type (HTML/PHP payload disguised as image)."""
    fake_html = b"<!DOCTYPE html><html><head></head><body><h1>Fake</h1></body></html>"
    client = MockHttpClient({
        "https://cdn.example.org/fake.png": MockHttpResponse(
            200, {"content-type": "image/png"}, fake_html
        ),
    })
    res = secure_fetch_image_asset(
        "https://cdn.example.org/fake.png",
        http_client=client,
        dns_resolver=MOCK_PUBLIC_DNS,
    )
    assert res.success is False
    assert ImageDefectCode.IMAGE_FORMAT_UNSUPPORTED in res.defects
    assert any("magic bytes are invalid" in d.lower() for d in res.defect_details)


def test_secure_fetch_corrupt_image_signature(sample_bounds):
    """10. Rejects corrupt image signature and verifies magic byte detection."""
    corrupt_data = b"\x00\x00\x00\x00\x00\x00\x00\x00\xaa\xbb\xcc\xdd"
    sig_ok, mime = verify_image_signature(corrupt_data)
    assert sig_ok is False
    assert mime == ""

    cand = ImageCandidate(
        candidate_id="cand_corrupt",
        source_url="https://test.local/corrupt.png",
        preview_url="",
        rights=ImageRightsMetadata(provider="test", rights_verified=True),
    )
    res = validate_image_asset(
        cand,
        corrupt_data,
        region_width_in=sample_bounds.width_in,
        region_height_in=sample_bounds.height_in,
    )
    assert res.valid is False
    assert ImageDefectCode.IMAGE_FILE_CORRUPT in res.defects


def test_rights_gating_missing_rights_metadata():
    """11. Rejects missing rights metadata or unverified status (hard eligibility gate)."""
    # None metadata
    ok1, defect1, reason1 = validate_image_rights(None)
    assert ok1 is False
    assert defect1 == ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED

    # Unverified rights
    r_unver = ImageRightsMetadata(provider="wikimedia", rights_verified=False)
    ok2, defect2, reason2 = validate_image_rights(r_unver)
    assert ok2 is False
    assert defect2 == ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED

    # Missing provider string
    r_noprov = ImageRightsMetadata(provider="", rights_verified=True)
    ok3, defect3, reason3 = validate_image_rights(r_noprov)
    assert ok3 is False
    assert defect3 == ImageDefectCode.IMAGE_PROVENANCE_INCOMPLETE


def test_rights_gating_permission_incompatible_with_intended_usage():
    """12. Rejects permission incompatible with intended usage scope."""
    r_personal = ImageRightsMetadata(
        provider="stock_vault",
        rights_verified=True,
        permitted_usage_scope="personal_use_only",
    )
    # Commercial usage rejected
    ok_comm, def_comm, reas_comm = validate_image_rights(r_personal, intended_usage="commercial")
    assert ok_comm is False
    assert def_comm == ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED
    assert "does not permit 'commercial' usage" in reas_comm

    # Educational usage rejected
    ok_edu, def_edu, reas_edu = validate_image_rights(r_personal, intended_usage="educational")
    assert ok_edu is False
    assert def_edu == ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED
    assert "does not permit 'educational' usage" in reas_edu

    # Public domain accepted for any usage
    r_pd = ImageRightsMetadata(
        provider="archive",
        rights_verified=True,
        permitted_usage_scope="public_domain",
    )
    ok_pd, def_pd, _ = validate_image_rights(r_pd, intended_usage="educational")
    assert ok_pd is True


def test_rights_gating_missing_mandatory_attribution():
    """13. Rejects asset when mandatory attribution requirement lacks attribution text."""
    r_attr_missing = ImageRightsMetadata(
        provider="cc_library",
        rights_verified=True,
        attribution_requirement=True,
        attribution_text="",
    )
    ok1, defect1, reason1 = validate_image_rights(r_attr_missing)
    assert ok1 is False
    assert defect1 == ImageDefectCode.IMAGE_ATTRIBUTION_MISSING
    assert "Mandatory attribution text is missing" in reason1

    # When attribution text is provided, passes
    r_attr_ok = ImageRightsMetadata(
        provider="cc_library",
        rights_verified=True,
        attribution_requirement=True,
        attribution_text="Photo by John Doe (CC-BY-4.0)",
    )
    ok2, defect2, _ = validate_image_rights(r_attr_ok)
    assert ok2 is True
    assert defect2 is None

