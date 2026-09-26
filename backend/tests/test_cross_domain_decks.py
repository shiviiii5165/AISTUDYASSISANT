"""
TeachGenie PPT vNEXT — Cross-Domain Deck Regression Suite
=========================================================
Tests representative 10-slide decks across 4 distinct domains:
1. Cell Division (Biology)
2. TCP Congestion Control (Networking)
3. Market Equilibrium (Economics)
4. Probability Distributions (Mathematics)

Validates:
- Content completeness (semantic gate 0 violations)
- Table population (meaningful comparands, dimensions, values)
- Process-stage consistency
- Notes alignment & no cross-slide contamination
- Actual PPTX preservation (serialization and re-opening)
"""
import pytest
import io
import re
from pathlib import Path
from pptx import Presentation

from app.services.presentation.schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind,
    DesignSystem, SlideType, SlideIntent, ContentPattern, TextBudget,
    ContentOrigin, SemanticStatus, SlideBlueprint, SlideConceptPacket,
    ContentQualityScores
)
from app.services.presentation.brief_builder import build_presentation_brief
from app.services.presentation.content_agent import (
    _synthesize_dynamic_slide_content,
    _synchronize_slidecontent_to_dict
)
from app.services.presentation.content_completeness_gate import (
    audit_deck_content_completeness,
    validate_slide_content_completeness
)
from app.services.presentation.deck_content_memory import DeckContentMemory
from app.services.presentation.engine.builder import build_presentation_spec


DOMAINS = [
    {
        "topic": "Cell Division",
        "domain": "Biology",
        "canonical_concepts": ["Mitosis", "Meiosis", "Prophase", "Metaphase", "Anaphase", "Telophase", "Cytokinesis", "Spindle"],
        "comparison_title_1": "Contrasting Mitosis and Meiosis Pathways",
        "comparison_title_2": "Comparing Plant and Animal Cytokinesis Models",
        "process_title": "Sequential Execution Stages of Mitotic Division",
        "summary_title": "Architectural Synthesis: Cell Division Mechanics",
        "stages": ["Prophase Spindle Assembly", "Metaphase Chromosome Alignment", "Anaphase Chromatid Separation", "Telophase & Cytokinesis Resolution"],
        "dims": ["Biological Function", "Ploidy Outcome", "Genetic Variation", "Replication Cycles"],
    },
    {
        "topic": "TCP Congestion Control",
        "domain": "Computer Networking",
        "canonical_concepts": ["Loss-Based", "Delay-Based", "Slow Start", "Congestion Avoidance", "Fast Retransmit", "Fast Recovery", "BBR", "AIMD"],
        "comparison_title_1": "Contrasting Loss-Based and Delay-Based Congestion Control",
        "comparison_title_2": "Comparing Reno and BBR Operational Models",
        "process_title": "Operational Execution Stages of TCP Congestion Avoidance",
        "summary_title": "Architectural Synthesis: TCP Flow Governance",
        "stages": ["Slow Start Exponential Probing", "Congestion Avoidance Additive Increase", "Fast Retransmit Packet Loss Detection", "Fast Recovery Window Stabilization"],
        "dims": ["Congestion Signal", "Window Growth Model", "Buffer Bloat Susceptibility", "Bandwidth Probing Mechanism"],
    },
    {
        "topic": "Market Equilibrium",
        "domain": "Economics",
        "canonical_concepts": ["Supply", "Demand", "Excess Demand", "Price Bidding", "Market Clearing", "Elasticity", "Surplus", "Deadweight Loss"],
        "comparison_title_1": "Contrasting Perfectly Competitive and Monopoly Market Structures",
        "comparison_title_2": "Comparing Short-Run and Long-Run Equilibrium Adjustments",
        "process_title": "Execution Stages of Market Price Discovery and Clearing",
        "summary_title": "Architectural Synthesis: Market Equilibrium Governance",
        "stages": ["Initial Demand-Supply Disequilibrium", "Price Bidding Adjustments", "Quantity Supplied Rebalancing", "Market Clearing State Attainment"],
        "dims": ["Market Power", "Price Determination", "Allocative Efficiency", "Consumer Surplus Retention"],
    },
    {
        "topic": "Probability Distributions",
        "domain": "Mathematics",
        "canonical_concepts": ["Discrete Distribution", "Continuous Distribution", "PMF", "PDF", "Cumulative CDF", "Expectation", "Variance", "Support"],
        "comparison_title_1": "Contrasting Discrete and Continuous Probability Formulations",
        "comparison_title_2": "Comparing Parametric and Non-Parametric Modeling Tradeoffs",
        "process_title": "Execution Stages of Empirical Distribution Estimation",
        "summary_title": "Architectural Synthesis: Probabilistic Modeling Principles",
        "stages": ["Sample Space Definition", "Probability Function Specification", "Normalization Verification", "Expectation and Moment Calculation"],
        "dims": ["Domain Support", "Probability Assignment", "Cumulative Mapping", "Expectation Integral Formula"],
    },
]


@pytest.mark.parametrize("domain_info", DOMAINS, ids=[d["topic"] for d in DOMAINS])
def test_cross_domain_deck_generation_and_preservation(domain_info):
    topic = domain_info["topic"]
    cfg = PresentationConfig(
        topic=topic,
        slide_count=10,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
        theme="blue_professional",
        enable_images=False,
        enable_diagrams=True,
    )
    brief = build_presentation_brief(cfg)

    blueprints = [
        # Slide 1: Cover
        SlideBlueprint(
            slide_number=1,
            intent=SlideIntent.COVER,
            narrative_role="cover",
            learning_purpose=f"Introduction to {topic}",
            primary_message=f"{topic}: Foundations and Core Principles",
            key_takeaway=f"{topic}: Foundations and Core Principles",
            canonical_concepts=domain_info["canonical_concepts"][:2],
            text_budget=TextBudget(body_words_max=30),
        ),
        # Slide 2: Problem Context
        SlideBlueprint(
            slide_number=2,
            intent=SlideIntent.CONTEXT,
            narrative_role="context",
            learning_purpose=f"Foundational challenges of {topic}",
            primary_message=f"Problem context and operational constraints behind {topic}",
            key_takeaway=f"Managing {topic} demands precise coordination between underlying physical constraints and system mechanisms.",
            canonical_concepts=domain_info["canonical_concepts"][:3],
            text_budget=TextBudget(body_words_max=50),
        ),
        # Slide 3: Architecture / System Overview
        SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.SYSTEM_OVERVIEW,
            narrative_role="architecture",
            learning_purpose=f"Structural breakdown of {topic}",
            primary_message=f"System architecture and component topology of {topic}",
            key_takeaway=f"Core structural topology governs state transitions and mechanics in {topic}.",
            canonical_concepts=domain_info["canonical_concepts"][:3],
            text_budget=TextBudget(body_words_max=50),
        ),
        # Slide 4: Core Subsystems
        SlideBlueprint(
            slide_number=4,
            intent=SlideIntent.COMPONENT_BREAKDOWN,
            narrative_role="components",
            learning_purpose=f"Subsystems of {topic}",
            primary_message=f"Core subsystems and primary components of {topic}",
            key_takeaway=f"Modular components interact through defined interfaces to sustain {topic} equilibrium.",
            canonical_concepts=domain_info["canonical_concepts"][2:5],
            text_budget=TextBudget(body_words_max=50),
        ),
        # Slide 5: Process Flow
        SlideBlueprint(
            slide_number=5,
            intent=SlideIntent.PROCESS_EXPLANATION,
            narrative_role="process",
            learning_purpose=f"Sequential workflow of {topic}",
            primary_message=domain_info["process_title"],
            key_takeaway=f"Execution progresses through four deterministic stages to complete {topic} workflow.",
            canonical_concepts=domain_info["canonical_concepts"][2:6],
            text_budget=TextBudget(body_words_max=60),
        ),
        # Slide 6: Comparison Table 1
        SlideBlueprint(
            slide_number=6,
            intent=SlideIntent.COMPARISON,
            narrative_role="comparison",
            learning_purpose=f"Primary comparative analysis in {topic}",
            primary_message=domain_info["comparison_title_1"],
            key_takeaway=f"Contrasting primary models highlights critical operational tradeoffs in {topic}.",
            canonical_concepts=domain_info["canonical_concepts"][:4],
            text_budget=TextBudget(body_words_max=60),
        ),
        # Slide 7: Misconception
        SlideBlueprint(
            slide_number=7,
            intent=SlideIntent.MISCONCEPTION,
            narrative_role="misconception",
            learning_purpose=f"Debunking errors in {topic}",
            primary_message=f"Common misconceptions and clarified realities in {topic}",
            key_takeaway=f"Clarifying core mechanisms prevents flawed operational assumptions in {topic}.",
            canonical_concepts=domain_info["canonical_concepts"][1:4],
            text_budget=TextBudget(body_words_max=50),
        ),
        # Slide 8: Comparison Table 2
        SlideBlueprint(
            slide_number=8,
            intent=SlideIntent.COMPARISON,
            narrative_role="comparison",
            learning_purpose=f"Tradeoff analysis in {topic}",
            primary_message=domain_info["comparison_title_2"],
            key_takeaway=f"Evaluating implementation models reveals distinct structural performance boundaries.",
            canonical_concepts=domain_info["canonical_concepts"][3:7],
            text_budget=TextBudget(body_words_max=60),
        ),
        # Slide 9: Tradeoffs / Contrast
        SlideBlueprint(
            slide_number=9,
            intent=SlideIntent.TRADEOFF,
            narrative_role="tradeoffs",
            learning_purpose=f"System constraints in {topic}",
            primary_message=f"Key tradeoffs and decision factors in {topic}",
            key_takeaway=f"Balancing throughput against resource overhead requires explicit threshold governance.",
            canonical_concepts=domain_info["canonical_concepts"][:3],
            text_budget=TextBudget(body_words_max=50),
        ),
        # Slide 10: Summary
        SlideBlueprint(
            slide_number=10,
            intent=SlideIntent.SUMMARY,
            narrative_role="summary",
            learning_purpose=f"Synthesis of {topic}",
            primary_message=domain_info["summary_title"],
            key_takeaway=f"Unified synthesis integrates foundational principles, component interactions, and operational safeguards across {topic}.",
            canonical_concepts=domain_info["canonical_concepts"][:2],
            text_budget=TextBudget(body_words_max=50),
        ),
    ]

    deck_memory = DeckContentMemory()
    structured_slides = []

    for bp in blueprints:
        packet = SlideConceptPacket(
            primary_concept=bp.canonical_concepts[0] if bp.canonical_concepts else topic,
            supporting_concepts=domain_info["canonical_concepts"],
            process_stages=domain_info["stages"],
            comparison_dimensions=domain_info["dims"],
        )
        content = _synthesize_dynamic_slide_content(
            blueprint=bp,
            brief=brief,
            topic_intelligence={},
            deck_memory=deck_memory,
            slide_no=bp.slide_number,
            total_slides=len(blueprints),
            source_context="",
            concept_packet=packet,
        )
        slide_dict = _synchronize_slidecontent_to_dict(
            content=content,
            blueprint=bp,
            quality_scores=ContentQualityScores(),
            slide_no=bp.slide_number,
        )

        vspec = VisualSpec(
            kind=VisualKind.NONE,
            asset_required=False,
            image_prompt="",
            image_bytes=None,
        )
        slide_obj = SlideSpec(
            slide_no=bp.slide_number,
            type=slide_dict.get("type", SlideType.CONCEPT),
            title=slide_dict.get("title", ""),
            subtitle=slide_dict.get("subtitle", ""),
            key_message=slide_dict.get("key_message", ""),
            body_bullets=slide_dict.get("body_bullets", []),
            example=slide_dict.get("example", ""),
            speaker_notes=slide_dict.get("speaker_notes", ""),
            content_pattern=slide_dict.get("content_pattern"),
            section_label=slide_dict.get("section_label"),
            visual=vspec,
            layers=slide_dict.get("layers", []),
            steps=slide_dict.get("steps", []),
            milestones=slide_dict.get("milestones", []),
            columns=slide_dict.get("columns", []),
            metrics=slide_dict.get("metrics", []),
            content=slide_dict.get("content"),
        )
        structured_slides.append(slide_obj)

    spec = PresentationSpec(
        title=f"{topic}: Academic Overview",
        subtitle="Principles and Comparative Analysis",
        config=cfg,
        key_takeaways=[s.key_message for s in structured_slides if s.key_message],
        slides=structured_slides,
        expansion_reason="",
    )

    # 1. Content Completeness Gate
    audit_res = audit_deck_content_completeness(spec)
    assert audit_res.passed, f"Completeness gate failed for '{topic}': {audit_res.violations}"
    assert audit_res.error_count == 0

    # 2. Comparison Table Population Verification (Slides 6 and 8)
    for comp_idx in [5, 7]:
        comp_slide = structured_slides[comp_idx]
        assert comp_slide.columns and len(comp_slide.columns) == 2, f"Slide {comp_idx+1} should have 2 columns for {topic}"
        col_a, col_b = comp_slide.columns[0], comp_slide.columns[1]
        assert col_a.get("heading") and col_b.get("heading"), f"Columns missing headings in slide {comp_idx+1} for {topic}"
        assert "column a" not in col_a.get("heading").lower(), f"Generic column heading in slide {comp_idx+1} for {topic}"
        assert len(col_a.get("points", [])) >= 3, f"Column A has fewer than 3 points in slide {comp_idx+1} for {topic}"
        assert len(col_b.get("points", [])) >= 3, f"Column B has fewer than 3 points in slide {comp_idx+1} for {topic}"

    # 3. Process Flow Consistency Verification (Slide 5)
    proc_slide = structured_slides[4]
    assert len(proc_slide.steps) >= 3, f"Process slide steps count < 3 in {topic}"
    for step in proc_slide.steps:
        assert step.get("title") and step.get("description"), f"Step missing title or description in {topic}"

    # 4. Notes Alignment Verification
    seen_notes = set()
    for s in structured_slides:
        assert s.speaker_notes, f"Slide {s.slide_no} missing speaker notes in {topic}"
        words = s.speaker_notes.split()
        assert len(words) >= 30, f"Notes too short ({len(words)} words) on slide {s.slide_no} in {topic}"
        norm_note = re.sub(r"[^\w\s]", "", s.speaker_notes[:50]).lower().strip()
        assert norm_note not in seen_notes, f"Speaker note cross-slide duplication on slide {s.slide_no} in {topic}"
        seen_notes.add(norm_note)

    # 5. PPTX Serialization and Reopening Verification
    pptx_bytes = build_presentation_spec(spec)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 50000, f"PPTX bytes abnormally small ({len(pptx_bytes)}) for {topic}"

    prs = Presentation(io.BytesIO(pptx_bytes))
    assert len(prs.slides) == 10, f"Reopened PPTX has {len(prs.slides)} slides, expected 10 for {topic}"

    # Verify table in slide 6
    slide6 = prs.slides[5]
    tables_found = [shape.table for shape in slide6.shapes if shape.has_table]
    assert len(tables_found) >= 1, f"No table found on comparison slide 6 in {topic}"
    tbl = tables_found[0]
    assert len(tbl.columns) == 2, f"Expected 2 columns in reopened table for {topic}"
    assert len(tbl.rows) >= 4, f"Expected at least 4 rows in reopened table for {topic}"
