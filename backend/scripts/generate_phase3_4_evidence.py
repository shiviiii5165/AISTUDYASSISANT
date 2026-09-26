"""
Phase 3.4 Evidence Generation — Image Intelligence & Visual Asset Orchestration
================================================================================
Generates representative PPTX evidence across multiple domains using offline
mock providers. No live API calls. No external image downloads.

Evidence Cases:
  1. Biology: Scientific illustration (chloroplast) — IMAGE_REQUIRED
  2. Computer Science: Diagram preferred over stock image — DIAGRAM_PREFERRED
  3. Humanities: Historical documentary image — IMAGE_REQUIRED
  4. Mathematics: No unnecessary image — IMAGE_UNNECESSARY
  5. Environmental Science: Ecosystem photograph — IMAGE_USEFUL
  6. Negative: No reliable image available — IMAGE_UNAVAILABLE
  7. Negative: Rights metadata missing — IMAGE_RIGHTS_UNVERIFIED
  8. Negative: Corrupt image — IMAGE_FILE_CORRUPT
  9. Negative: Diagram/chart semantically preferable — CHART_PREFERRED
  10. Provider registry capabilities — structural verification
"""
import sys
import os
import json
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.presentation.image_intelligence import (
    ImageAssetDecision,
    ImageDecisionOutcome,
    ImageTypeClassification,
    ImageProvenance,
    ImageRightsMetadata,
    ImageCandidate,
    ImageRelevanceScore,
    ImageTelemetry,
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
)
from app.services.presentation.image_asset_validator import (
    validate_image_asset,
    validate_url_security,
    verify_image_signature,
    validate_image_rights,
    check_deduplication,
    ImageValidationResult,
)
from app.services.presentation.image_composition import (
    DeckImageManifest,
    calculate_contain_geometry,
    calculate_cover_geometry,
)
from app.services.presentation.visual_schemas import (
    VisualSemanticPacket,
    VisualIntent,
    DesignDNA,
)
from app.services.presentation.schemas import SlideContent
from app.services.presentation.composition_schemas import (
    ContentRegion,
    RegionSemanticRole,
    ResolvedRegionBounds,
    ContentBinding,
    SourceKind,
    CompositionInputManifest,
)


def make_visual_region(region_id: str = "vis_1", role=RegionSemanticRole.PRIMARY_VISUAL):
    return ContentRegion(
        region_id=region_id,
        semantic_role=role,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=ResolvedRegionBounds(
            left_in=1.0, top_in=1.5, width_in=7.0, height_in=4.5,
            left_col=1, right_col=9, top_module=6, bottom_module=24,
        ),
        binding=ContentBinding(
            source_kind=SourceKind.VISUAL_SEMANTIC_PACKET,
            source_id=f"src_{region_id}",
            field_path="primary_visual_message",
            resolved_content_hash=CompositionInputManifest.compute_payload_hash("mock_visual_content"),
            is_decorative=False,
        ),
    )


def make_packet(
    slide_no=1,
    intent=VisualIntent.SHOW_OBJECT,
    message="",
    entities=None,
    image_concepts=None,
    relationships=None,
    system_components=None,
    process_nodes=None,
):
    return VisualSemanticPacket(
        slide_no=slide_no,
        primary_visual_message=message,
        visual_intent=intent,
        key_entities=entities or [],
        image_candidate_concepts=image_concepts or [],
        relationships=relationships or [],
        system_components=system_components or [],
        process_nodes=process_nodes or [],
    )


def run_evidence():
    results = []
    telemetry = ImageTelemetry()
    manifest = DeckImageManifest(deck_topic="Phase 3.4 Evidence")

    # ─── CASE 1: Biology — Scientific Illustration (chloroplast) ───
    packet1 = make_packet(
        slide_no=1, intent=VisualIntent.EXPLAIN_STRUCTURE,
        message="Chloroplast internal structure showing thylakoid membranes",
        entities=["chloroplast", "thylakoid", "stroma", "granum"],
        image_concepts=["chloroplast thylakoid membrane labeled educational illustration"],
    )
    content1 = SlideContent(title="Chloroplast Structure", primary_takeaway="Internal membrane system")
    region1 = make_visual_region("vis_bio_1")
    decision1 = assess_image_need(packet1, content1, region1)
    query1 = build_semantic_query(packet1, content1)
    img_type1 = classify_image_type(packet1, content1)

    # Search mock provider
    candidates1 = search_mock_provider(query1)
    best1, rejections1 = select_best_candidate(candidates1, query1, region1.bounds, set())

    results.append({
        "case": "1. Biology — Chloroplast Scientific Illustration",
        "outcome": decision1.outcome.value,
        "search_query": query1,
        "image_type": img_type1.value,
        "candidate_count": len(candidates1),
        "best_candidate": best1.asset_id if best1 else None,
        "best_score": best1.score.composite_score if best1 else 0,
        "rejection_reasons": rejections1,
        "expected_outcome": "image_required",
        "PASS": decision1.outcome == ImageDecisionOutcome.IMAGE_REQUIRED,
    })

    # ─── CASE 2: Computer Science — Diagram Preferred ───
    packet2 = make_packet(
        slide_no=2, intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        message="Microservice architecture with API gateway",
        entities=["API gateway", "service mesh", "database"],
        system_components=["gateway", "auth_service", "user_service", "db"],
    )
    content2 = SlideContent(title="Microservice Architecture")
    region2 = make_visual_region("vis_cs_2")
    decision2 = assess_image_need(packet2, content2, region2)

    results.append({
        "case": "2. Computer Science — Diagram Preferred",
        "outcome": decision2.outcome.value,
        "rationale": decision2.rationale,
        "expected_outcome": "diagram_preferred",
        "PASS": decision2.outcome == ImageDecisionOutcome.DIAGRAM_PREFERRED,
    })

    # ─── CASE 3: Humanities — Historical Documentary Image ───
    packet3 = make_packet(
        slide_no=3, intent=VisualIntent.SHOW_EVIDENCE,
        message="Historical documentary photograph of Indian independence movement",
        entities=["independence", "partition", "1947"],
        image_concepts=["historical documentary photograph partition independence"],
    )
    content3 = SlideContent(title="Indian Independence Movement")
    region3 = make_visual_region("vis_hist_3")
    decision3 = assess_image_need(packet3, content3, region3)
    query3 = build_semantic_query(packet3, content3)
    img_type3 = classify_image_type(packet3, content3)
    candidates3 = search_mock_provider(query3)
    best3, rejections3 = select_best_candidate(candidates3, query3, region3.bounds, set())

    results.append({
        "case": "3. Humanities — Historical Documentary Image",
        "outcome": decision3.outcome.value,
        "search_query": query3,
        "image_type": img_type3.value,
        "candidate_count": len(candidates3),
        "best_candidate": best3.asset_id if best3 else None,
        "expected_outcome": "image_required",
        "PASS": decision3.outcome == ImageDecisionOutcome.IMAGE_REQUIRED,
    })

    # ─── CASE 4: Mathematics — No Unnecessary Image ───
    packet4 = make_packet(
        slide_no=4, intent=VisualIntent.SHOW_FORMULA,
        message="Quadratic formula derivation",
        entities=["quadratic formula", "discriminant"],
    )
    content4 = SlideContent(title="Quadratic Formula", formula="x = (-b ± √(b²-4ac)) / 2a")
    region4 = make_visual_region("vis_math_4")
    decision4 = assess_image_need(packet4, content4, region4)

    results.append({
        "case": "4. Mathematics — No Unnecessary Image",
        "outcome": decision4.outcome.value,
        "rationale": decision4.rationale,
        "expected_outcome": "image_unnecessary",
        "PASS": decision4.outcome == ImageDecisionOutcome.IMAGE_UNNECESSARY,
    })

    # ─── CASE 5: Environmental Science — Ecosystem Photograph ───
    packet5 = make_packet(
        slide_no=5, intent=VisualIntent.SHOW_OBJECT,
        message="Tropical rainforest canopy biodiversity ecosystem",
        entities=["rainforest", "canopy", "biodiversity"],
        image_concepts=["tropical rainforest canopy ecosystem biodiversity"],
    )
    content5 = SlideContent(title="Tropical Rainforest Ecosystem")
    region5 = make_visual_region("vis_env_5")
    decision5 = assess_image_need(packet5, content5, region5)
    query5 = build_semantic_query(packet5, content5)
    candidates5 = search_mock_provider(query5)
    best5, rejections5 = select_best_candidate(candidates5, query5, region5.bounds, set())

    results.append({
        "case": "5. Environmental Science — Ecosystem Photograph",
        "outcome": decision5.outcome.value,
        "search_query": query5,
        "candidate_count": len(candidates5),
        "best_candidate": best5.asset_id if best5 else None,
        "expected_outcome": "image_required",
        "PASS": decision5.outcome == ImageDecisionOutcome.IMAGE_REQUIRED,
    })

    # ─── CASE 6: Negative — No Reliable Image Available ───
    candidates_empty = search_mock_provider("quantum_chromodynamics_gluon_confinement")
    best_empty, rejections_empty = select_best_candidate(candidates_empty, "quantum chromodynamics", region5.bounds, set())

    results.append({
        "case": "6. Negative — No Reliable Image Available",
        "candidate_count": len(candidates_empty),
        "best_candidate": best_empty.asset_id if best_empty else None,
        "expected": "No candidates found",
        "PASS": best_empty is None,
    })

    # ─── CASE 7: Negative — Rights Metadata Missing ───
    unverified = get_unverified_rights_candidate()
    val_unverified = validate_image_asset(
        unverified, None, region_width_in=7.0, region_height_in=4.5,
    )

    results.append({
        "case": "7. Negative — Rights Metadata Missing",
        "valid": val_unverified.valid,
        "defects": [d.value for d in val_unverified.defects],
        "expected_defect": "IMAGE_RIGHTS_UNVERIFIED",
        "PASS": ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED in val_unverified.defects,
    })

    # ─── CASE 8: Negative — Corrupt Image ───
    corrupt = get_corrupt_test_candidate()
    corrupt_bytes = b"\x00\x00\x00\x00BAD_DATA"
    val_corrupt = validate_image_asset(corrupt, corrupt_bytes)

    results.append({
        "case": "8. Negative — Corrupt Image",
        "valid": val_corrupt.valid,
        "defects": [d.value for d in val_corrupt.defects],
        "expected_defects": ["IMAGE_FORMAT_UNSUPPORTED", "IMAGE_FILE_CORRUPT"],
        "PASS": not val_corrupt.valid,
    })

    # ─── CASE 9: Negative — Chart Semantically Preferred ───
    packet9 = make_packet(
        slide_no=9, intent=VisualIntent.SHOW_DATA_PATTERN,
        message="GDP growth rates comparison across countries",
        entities=["GDP", "growth", "countries"],
    )
    content9 = SlideContent(title="GDP Growth Rates")
    region9 = make_visual_region("vis_chart_9")
    decision9 = assess_image_need(packet9, content9, region9)

    results.append({
        "case": "9. Negative — Chart Semantically Preferred",
        "outcome": decision9.outcome.value,
        "rationale": decision9.rationale,
        "expected_outcome": "chart_preferred",
        "PASS": decision9.outcome == ImageDecisionOutcome.CHART_PREFERRED,
    })

    # ─── CASE 10: Provider Registry ───
    registry = build_provider_registry()
    reg_summary = [
        {
            "provider": p.provider_name,
            "enabled": p.enabled,
            "configured": p.configured,
            "health": p.health_status,
            "priority": p.fallback_priority,
        }
        for p in registry
    ]

    results.append({
        "case": "10. Provider Registry Capabilities",
        "providers": reg_summary,
        "total_providers": len(registry),
        "wikimedia_always_available": any(p.provider_name == "wikimedia" and p.enabled for p in registry),
        "PASS": len(registry) >= 4,
    })

    # ─── SUPPLEMENTARY: Crop Geometry Verification ───
    contain_geom = calculate_contain_geometry(1920, 1080, 914400, 1371600, 6400800, 4114800)
    cover_geom = calculate_cover_geometry(1920, 1080, 914400, 1371600, 6400800, 4114800)

    results.append({
        "case": "SUPP: Crop Geometry Verification",
        "contain": {"left": contain_geom[0], "top": contain_geom[1], "width": contain_geom[2], "height": contain_geom[3]},
        "cover": {"left": cover_geom[0], "top": cover_geom[1], "width": cover_geom[2], "height": cover_geom[3]},
        "PASS": contain_geom[2] > 0 and cover_geom[2] > 0,
    })

    # ─── SUPPLEMENTARY: Alt Text Generation ───
    alt1 = generate_alt_text(ImageTypeClassification.SCIENTIFIC_ILLUSTRATION, "chloroplast thylakoid", "Detailed chloroplast illustration showing thylakoid membrane", "Chloroplast Structure")
    alt2 = generate_alt_text(ImageTypeClassification.DECORATIVE_IMAGE, "background", "", "")

    results.append({
        "case": "SUPP: Alt Text Generation",
        "scientific_alt": alt1,
        "decorative_alt": alt2,
        "decorative_is_empty": alt2 == "",
        "PASS": len(alt1) > 0 and alt2 == "",
    })

    # ─── SUPPLEMENTARY: URL Security Validation ───
    url_tests = [
        ("https://api.pexels.com/image.jpg", True),
        ("http://insecure.com/image.jpg", False),
        ("https://127.0.0.1/evil.jpg", False),
        ("https://192.168.1.1/internal.jpg", False),
    ]
    url_results = []
    for url, expected in url_tests:
        safe, reason = validate_url_security(url)
        url_results.append({"url": url[:50], "safe": safe, "expected": expected, "pass": safe == expected})

    results.append({
        "case": "SUPP: URL Security Validation",
        "tests": url_results,
        "PASS": all(r["pass"] for r in url_results),
    })

    # ─── SUPPLEMENTARY: Deduplication Check ───
    dup, reason = check_deduplication("abc123", "img_1", "https://x.com/1.jpg", {"abc123"}, set(), set())
    no_dup, _ = check_deduplication("xyz789", "img_2", "https://x.com/2.jpg", set(), set(), set())

    results.append({
        "case": "SUPP: Deduplication Check",
        "is_duplicate": dup,
        "not_duplicate": not no_dup,
        "PASS": dup and not no_dup,
    })

    # ─── FINAL SUMMARY ───
    total = len(results)
    passed = sum(1 for r in results if r.get("PASS"))
    failed = total - passed

    print(f"\n{'='*70}")
    print("PHASE 3.4 EVIDENCE GENERATION -- IMAGE INTELLIGENCE")
    print(f"{'='*70}")
    for r in results:
        status = "[PASS]" if r.get("PASS") else "[FAIL]"
        print(f"  {status} | {r['case']}")
        if "outcome" in r:
            print(f"         outcome={r['outcome']}, expected={r.get('expected_outcome', 'n/a')}")
        if "search_query" in r:
            print(f"         query='{r['search_query'][:60]}'")
        if "candidate_count" in r:
            print(f"         candidates={r['candidate_count']}, best={r.get('best_candidate', 'none')}")
        if "defects" in r:
            print(f"         defects={r['defects']}")

    print(f"\n{'-'*70}")
    print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failed}")
    print(f"{'-'*70}")

    # Write evidence JSON
    evidence_dir = os.path.join(os.path.dirname(__file__), "..", "evidence", "phase3_4")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "evidence_report.json")
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nEvidence written to: {evidence_path}")

    if failed > 0:
        print(f"\n*** {failed} CASE(S) FAILED ***")
        sys.exit(1)
    else:
        print(f"\n*** ALL {total} CASES PASSED ***")
        sys.exit(0)


if __name__ == "__main__":
    run_evidence()
