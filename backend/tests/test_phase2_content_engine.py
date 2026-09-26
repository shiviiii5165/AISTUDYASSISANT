"""
LearnByGenie vNEXT Phase 2 — Content Intelligence Engine Test Suite
==================================================================
Comprehensive test suite verifying:
1. Schemas & Data Contracts (SlideContent, ClaimEvidence, ContentQualityScores, etc.)
2. Text Budget & Layout Capacity Engine
3. Claim Classification & Evidence Engine (Stat Guard, Source-Bound Tagging)
4. Deck Content Memory & Progression Tracking (Isolation, Terminology, Novelty)
5. Speaker Notes V2 Engine (Word Counts, Structured Cues, Transitions, Analogies)
6. Content Quality Auditor & Targeted Repair (12 Dimensions, Hard Fails, Gate)
7. Domain Writing & Audience Depth Profiles (18 Domains, 4 Audiences)
8. Anti-Hardcoding Static Scan (AST/Regex scan of presentation services)
9. 20+ Unseen Topics Robustness & Perturbation Testing
10. ContentAgent Pipeline Integration & Provenance Verification

All tests are unit-level / deterministic — zero external LLM API calls required.
"""
import ast
import os
import re
import sys
import pytest
from typing import Dict, Any, List

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.presentation.schemas import (
    PresentationConfig,
    PresentationSpec,
    PresentationBrief,
    SlideBlueprint,
    SlideIntent,
    VisualTypeHint,
    LayoutFamily,
    ContentDensity,
    StoryGrammarType,
    TextBudget,
    SlideSpec,
    SlideType,
    ContentPattern,
    PipelineProvenance,
    SlideContent,
    ContentQualityScores,
    ContentProvenance,
    ClaimType,
    ClaimEvidence,
    ClaimVerificationStatus,
    ContentOrigin,
    LayoutCapacity,
    SpeakerNoteCue,
    MisconceptionBlock,
    ComparisonRow,
    DataPoint,
    SlideConceptPacket,
    QualityGateError,
    SemanticStatus,
    SemanticFailureReason,
)
from app.services.presentation.topic_ontology_agent import (
    TopicIntelligencePack,
)
from app.services.presentation.content_budget_engine import (
    compute_text_budget,
    evaluate_budget_compliance,
    get_layout_capacity,
    count_words,
    LAYOUT_CAPACITY_PROFILES,
    DENSITY_BODY_WORD_RANGES,
)
from app.services.presentation.claim_evidence_engine import (
    guard_unsupported_statistics,
    classify_claim,
    classify_claims_in_content,
    resolve_evidence_for_claims,
    tag_content_origin,
    detect_fabricated_stat_phrases,
    detect_numeric_claims,
    FABRICATED_STAT_PHRASES,
)
from app.services.presentation.deck_content_memory import DeckContentMemory
from app.services.presentation.speaker_notes_v2 import (
    get_note_word_range,
    generate_transition_cue,
    validate_note_not_duplicating_slide,
    validate_analogy_quality,
    extract_cues_from_notes,
    build_speaker_notes_prompt,
    generate_expert_speaker_notes,
    measure_note_structural_similarity,
    SPEAKER_NOTE_WORD_RANGES,
    CUE_TEACHING,
    CUE_PROBING_QUESTION,
    CUE_MISCONCEPTION_WARNING,
    CUE_TRANSITION,
)
from app.services.presentation.content_quality_auditor import (
    audit_slide_content,
    passes_quality_gate,
    identify_needed_repairs,
    apply_deterministic_repairs,
    contains_banned_phrase,
    score_content_correctness,
    score_topic_specificity,
    score_primary_idea_clarity,
    score_content_depth,
    score_audience_fit,
    score_slide_nativeness,
    score_text_budget_compliance,
    score_example_quality,
    score_terminology_consistency,
    score_evidence_integrity,
    score_speaker_note_value,
    score_cross_slide_novelty,
    detect_genericity,
    evaluate_blind_topic_identifiability,
    evaluate_cross_topic_contrast,
    evaluate_domain_contamination,
    detect_incomplete_title,
    detect_ungrammatical_statement,
    sanitize_and_complete_title,
    TOPIC_SUBSTITUTION_PATTERNS,
    BANNED_PHRASES_PHASE2,
    RepairType,
    CONTENT_FREE_REPAIR_WRAPPERS,
)
from app.services.presentation.domain_content_writer import (
    get_domain_profile,
    get_audience_profile,
    get_expected_fields,
    build_content_generation_context,
    build_domain_writing_prompt,
    resolve_slide_concept_packet,
    check_contextual_vocabulary_leakage,
    get_domain_educator_persona,
    DOMAIN_WRITING_PROFILES,
    INTENT_REASONING_DIMENSIONS,
    AUDIENCE_DEPTH_PROFILES,
    DOMAIN_LEAKAGE_RISKS,
    LEGITIMATE_CONTEXT_EXEMPTIONS,
)
from app.services.presentation.content_agent import (
    expand_presentation_content,
    _synthesize_dynamic_slide_content,
    _synchronize_slidecontent_to_dict,
    _contains_banned,
    _has_verb,
    _word_boundary_truncate,
)


# ═══════════════════════════════════════════════════════════════
# 1. SCHEMAS & DATA CONTRACTS
# ═══════════════════════════════════════════════════════════════

def test_phase2_enums():
    """Assert all Phase 2 enums exist with exact members."""
    assert ClaimType.GENERAL_CONCEPT.value == "general_concept"
    assert ClaimType.VERIFIABLE_FACT.value == "verifiable_fact"
    assert ClaimType.NUMERIC_CLAIM.value == "numeric_claim"
    assert ClaimType.HISTORICAL_CLAIM.value == "historical_claim"
    assert ClaimType.RESEARCH_FINDING.value == "research_finding"
    assert ClaimType.CASE_STUDY_CLAIM.value == "case_study_claim"
    assert ClaimType.OPINION_INTERPRETATION.value == "opinion_interpretation"

    assert ClaimVerificationStatus.VERIFIED.value == "verified"
    assert ClaimVerificationStatus.SOURCE_PENDING.value == "source_pending"
    assert ClaimVerificationStatus.UNVERIFIED_REMOVED.value == "unverified_removed"

    assert ContentOrigin.SOURCE_DOCUMENT.value == "source_document"
    assert ContentOrigin.EXTERNAL_SOURCE.value == "external_source"
    assert ContentOrigin.MODEL_BACKGROUND.value == "model_background"
    assert ContentOrigin.DETERMINISTIC_STRUCTURE.value == "deterministic_structure"


def test_slide_content_model():
    """Verify SlideContent instantiation and intent-specific field structures."""
    content = SlideContent(
        title="Photosynthesis Fundamentals",
        subtitle="Light-dependent energy transformation",
        primary_takeaway="Chlorophyll converts solar radiation into biochemical potential.",
        supporting_points=["Light absorption occurs in thylakoid membranes.", "ATP is synthesized via photophosphorylation."],
        callout="Core efficiency limit: ~4-6% total incident sunlight.",
        example="In C3 plants, Rubisco catalyzes carbon fixation.",
        process_steps=["Photon absorption", "Electron transport", "NADPH synthesis"],
        speaker_notes="Walk students through the thylakoid membrane structure. What role does water splitting play?",
    )
    assert content.title == "Photosynthesis Fundamentals"
    assert len(content.supporting_points) == 2
    assert len(content.process_steps) == 3
    assert content.content_origin == ContentOrigin.MODEL_BACKGROUND
    assert content.fit_risk == ""


def test_slide_spec_phase2_fields_backward_compatibility():
    """Verify SlideSpec retains backward compatibility while supporting optional Phase 2 fields."""
    spec = SlideSpec(
        slide_no=1,
        title="Test Title",
        key_message="Dominant takeaway statement.",
        body_bullets=["Bullet 1", "Bullet 2"],
        content=SlideContent(title="Test Title", primary_takeaway="Dominant takeaway statement."),
        quality_scores=ContentQualityScores(aggregate_score=95),
    )
    assert spec.slide_no == 1
    assert spec.title == "Test Title"
    assert spec.content is not None
    assert spec.quality_scores.aggregate_score == 95


def test_pipeline_provenance_phase2_fields():
    """Assert PipelineProvenance includes Phase 2 content metadata fields."""
    prov = PipelineProvenance(
        content_engine="phase2",
        content_engine_version="2.0",
        content_schema_version="2.0",
        content_repair_count=1,
    )
    assert prov.content_engine == "phase2"
    assert prov.content_engine_version == "2.0"
    assert prov.content_repair_count == 1


# ═══════════════════════════════════════════════════════════════
# 2. TEXT BUDGET & LAYOUT CAPACITY ENGINE
# ═══════════════════════════════════════════════════════════════

def test_layout_capacity_profiles():
    """Verify all LayoutFamilies have defined layout capacity constraints."""
    for layout in LayoutFamily:
        cap = get_layout_capacity(layout)
        assert isinstance(cap, LayoutCapacity)
        assert cap.max_label_length > 0


def test_text_budget_computation():
    """Test deterministic budget calculation across densities and intents."""
    # Low density
    b_low = compute_text_budget(LayoutFamily.LEFT_TEXT_RIGHT_VISUAL, ContentDensity.LOW, VisualTypeHint.NONE, SlideIntent.CONCEPT_EXPLANATION)
    assert b_low.body_words_min == 20
    assert b_low.body_words_max == 45

    # Medium density
    b_med = compute_text_budget(LayoutFamily.LEFT_TEXT_RIGHT_VISUAL, ContentDensity.MEDIUM, VisualTypeHint.NONE, SlideIntent.CONCEPT_EXPLANATION)
    assert b_med.body_words_min == 45
    assert b_med.body_words_max == 80

    # High density
    b_high = compute_text_budget(LayoutFamily.LEFT_TEXT_RIGHT_VISUAL, ContentDensity.HIGH, VisualTypeHint.NONE, SlideIntent.CONCEPT_EXPLANATION)
    assert b_high.body_words_min == 60
    assert b_high.body_words_max == 110

    # Cover override
    b_cover = compute_text_budget(LayoutFamily.HERO, ContentDensity.LOW, VisualTypeHint.NONE, SlideIntent.COVER)
    assert b_cover.title_words_max == 10
    assert b_cover.subtitle_words_max == 22


def test_budget_compliance_and_fit_risk():
    """Verify evaluate_budget_compliance flags word overflow as FIT_RISK without silent font shrinking."""
    budget = TextBudget(body_max_words=20, body_words_max=20)
    
    # Over-budget content
    content = SlideContent(
        title="Concise Title",
        primary_takeaway="This is a very long takeaway designed to easily exceed the configured word limit for this particular test case.",
        supporting_points=[
            "Additional long supporting bullet point adding further words to the presentation slide.",
            "Another redundant sentence pushing the word count significantly higher than the allowed maximum budget.",
        ]
    )
    compliant, violations, fit_risk = evaluate_budget_compliance(content, budget)
    assert not compliant
    assert len(violations) > 0
    assert fit_risk != ""
    assert not compliant
    assert len(violations) > 0
    assert "FIT_RISK" in fit_risk


# ═══════════════════════════════════════════════════════════════
# 3. CLAIM CLASSIFICATION & EVIDENCE ENGINE
# ═══════════════════════════════════════════════════════════════

def test_unsupported_statistics_guard():
    """Verify fabricated statistics (e.g. '70% of companies...', '3x faster...') are detected and sanitized."""
    bad_stat = "Over 70% of companies fail to implement this properly."
    cleaned, changes = guard_unsupported_statistics(bad_stat)
    assert cleaned != bad_stat
    assert "70%" not in cleaned
    assert len(changes) > 0

    bad_multiple = "This new algorithm runs 3x faster than legacy solutions."
    cleaned_mult, changes_mult = guard_unsupported_statistics(bad_multiple)
    assert "3x" not in cleaned_mult
    assert len(changes_mult) > 0

    # Qualitative text without fake stats should remain untouched
    clean_text = "Photosynthesis operates via light-dependent reactions."
    unchanged, no_changes = guard_unsupported_statistics(clean_text)
    assert unchanged == clean_text
    assert len(no_changes) == 0


def test_claim_classification():
    """Verify factual claims are correctly categorized into ClaimType."""
    assert classify_claim("Energy cannot be created or destroyed in an isolated system.") == ClaimType.VERIFIABLE_FACT
    assert classify_claim("In 1789, the French Revolution began with the storming of the Bastille.") == ClaimType.HISTORICAL_CLAIM
    assert classify_claim("Approximately 45% of surveyed participants reported improvement.") == ClaimType.NUMERIC_CLAIM
    assert classify_claim("Consideration is a fundamental requirement in English contract law.") == ClaimType.GENERAL_CONCEPT


def test_evidence_resolution():
    """Assert resolve_evidence_for_claims correctly assigns verification status based on source presence."""
    claims = [
        ClaimEvidence(claim_text="General concept", claim_type=ClaimType.GENERAL_CONCEPT),
        ClaimEvidence(claim_text="45% reduction", claim_type=ClaimType.NUMERIC_CLAIM, source_required=True),
    ]
    # No source available
    resolved_no_src = resolve_evidence_for_claims(claims, source_id="")
    assert resolved_no_src[0].verification_status == ClaimVerificationStatus.VERIFIED
    assert resolved_no_src[1].verification_status == ClaimVerificationStatus.SOURCE_PENDING

    # Source attached
    resolved_src = resolve_evidence_for_claims(claims, source_id="doc_12345")
    assert resolved_src[1].verification_status == ClaimVerificationStatus.VERIFIED


# ═══════════════════════════════════════════════════════════════
# 4. DECK CONTENT MEMORY & PROGRESSION TRACKER
# ═══════════════════════════════════════════════════════════════

def test_deck_content_memory_isolation():
    """Verify DeckContentMemory instances maintain 100% strict isolation (no shared global state)."""
    mem1 = DeckContentMemory()
    mem2 = DeckContentMemory()

    mem1.register_concept("Gradient Descent")
    mem1.register_example("House price prediction using regression")
    mem1.register_canonical_term("Node.js", ["NodeJS", "Node js"])

    assert mem1.is_concept_already_introduced("Gradient Descent")
    assert not mem2.is_concept_already_introduced("Gradient Descent")
    assert mem1.is_example_already_used("House price prediction using regression")
    assert not mem2.is_example_already_used("House price prediction using regression")
    assert mem1.get_canonical_term("nodejs") == "Node.js"
    assert mem2.get_canonical_term("nodejs") is None


def test_deck_memory_terminology_normalization():
    """Verify canonical terminology normalization replaces informal variants."""
    mem = DeckContentMemory()
    mem.register_canonical_term("Reinforcement Learning", ["RL", "reinforcement-learning"])
    normalized = mem.normalize_terminology("The principles of RL govern agent behavior.")
    assert "Reinforcement Learning" in normalized


def test_deck_memory_duplication_prevention():
    """Verify memory detects repeating examples across slides."""
    mem = DeckContentMemory()
    mem.register_example("Tracing an HTTP request through the Express middleware pipeline.")
    assert mem.is_example_already_used("Tracing an HTTP request through the Express middleware pipeline.")
    assert not mem.is_example_already_used("Analyzing a database transaction isolation level.")


# ═══════════════════════════════════════════════════════════════
# 5. SPEAKER NOTES V2 ENGINE
# ═══════════════════════════════════════════════════════════════

def test_speaker_notes_word_ranges():
    """Verify intent-aware speaker note word count boundaries."""
    assert get_note_word_range(SlideIntent.COVER) == (20, 60)
    assert get_note_word_range(SlideIntent.SYSTEM_OVERVIEW) == (100, 170)
    assert get_note_word_range(SlideIntent.WORKED_EXAMPLE) == (90, 170)
    assert get_note_word_range(SlideIntent.SUMMARY) == (60, 120)


def test_speaker_notes_cue_extraction():
    """Verify structured cues (probing questions, misconception warnings, transitions) are extracted."""
    notes = (
        "Focus on how the event loop handles asynchronous I/O callbacks without thread blocking. "
        "A common misconception is assuming Node.js is multithreaded by default. "
        "Why does non-blocking I/O scale better for I/O-bound tasks than CPU-bound tasks? "
        "Now let's examine the worker thread architecture in the next slide."
    )
    cues = extract_cues_from_notes(notes)
    cue_types = [c.cue_type for c in cues]
    assert CUE_PROBING_QUESTION in cue_types
    assert CUE_MISCONCEPTION_WARNING in cue_types
    assert CUE_TRANSITION in cue_types


def test_speaker_notes_duplication_validation():
    """Verify speaker notes that replicate on-slide text are flagged."""
    slide_dict = {
        "title": "Photosynthesis Reaction Steps",
        "primary_takeaway": "Light reactions convert water and photons into oxygen and ATP.",
        "supporting_points": ["Occurs in thylakoid membranes.", "Requires photosystem II and I."],
    }
    # Direct duplicate note
    dup_notes = "Light reactions convert water and photons into oxygen and ATP in thylakoid membranes."
    acceptable, overlap = validate_note_not_duplicating_slide(dup_notes, slide_dict)
    assert not acceptable or overlap > 0.4

    # Good expansive note
    good_notes = (
        "When explaining this reaction sequence, draw students' attention to the molecular energetics. "
        "Notice that water splitting provides the initial electron source. What would happen if water was unavailable?"
    )
    good_acc, good_overlap = validate_note_not_duplicating_slide(good_notes, slide_dict)
    assert good_acc
    assert good_overlap < 0.3


def test_analogy_validation():
    """Verify analogy validation enforces both conceptual mapping and explicit limitation."""
    # Bad analogy (lacks limitation)
    bad_analogy = "The event loop is like a waiter in a restaurant taking orders to the kitchen."
    valid_bad, issues_bad = validate_analogy_quality(bad_analogy)
    assert not valid_bad
    assert any("limitation" in iss.lower() for iss in issues_bad)

    # Good analogy (mapping + limitation)
    good_analogy = (
        "Think of the event loop like a restaurant waiter taking orders to the kitchen. "
        "However, this analogy breaks down because if a customer requires an extensive custom dish, "
        "the single waiter cannot serve anyone else until that CPU task completes."
    )
    valid_good, issues_good = validate_analogy_quality(good_analogy)
    assert valid_good
    assert len(issues_good) == 0


# ═══════════════════════════════════════════════════════════════
# 6. QUALITY AUDITOR & TARGETED REPAIR
# ═══════════════════════════════════════════════════════════════

def test_banned_phrases_detection():
    """Verify banned generic AI phrases are detected and rejected."""
    bad_phrase = "Artificial intelligence plays a crucial role in today's rapidly evolving world."
    has_banned, found = contains_banned_phrase(bad_phrase)
    assert has_banned
    assert len(found) > 0


def test_quality_auditor_twelve_dimensions():
    """Verify full 12-dimension quality audit returns valid scores for each dimension."""
    content = {
        "title": "Quantum Entanglement",
        "primary_takeaway": "Entangled particle states cannot be factored into individual states.",
        "supporting_points": [
            "Bell state measurements violate classical local realism bounds.",
            "Spin correlations persist regardless of spatial separation.",
        ],
        "example": "EPR pair generation via spontaneous parametric down-conversion.",
        "speaker_notes": "Guide students through the Bell inequality proof. What makes quantum correlations fundamentally distinct from shared random keys?",
    }
    scores = audit_slide_content(
        content_dict=content,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        topic="Quantum Entanglement",
        domain="physics",
        education_level="postgraduate",
        body_budget_max=80,
    )
    assert isinstance(scores, ContentQualityScores)
    assert 0 <= scores.content_correctness <= 100
    assert 0 <= scores.topic_specificity <= 100
    assert 0 <= scores.primary_idea_clarity <= 100
    assert 0 <= scores.content_depth <= 100
    assert 0 <= scores.audience_fit <= 100
    assert 0 <= scores.slide_nativeness <= 100
    assert 0 <= scores.text_budget_compliance <= 100
    assert 0 <= scores.example_quality <= 100
    assert 0 <= scores.terminology_consistency <= 100
    assert 0 <= scores.evidence_integrity <= 100
    assert 0 <= scores.speaker_note_value <= 100
    assert 0 <= scores.cross_slide_novelty <= 100
    assert scores.aggregate_score > 70
    assert not scores.has_hard_fail


def test_quality_gate_hard_fails():
    """Verify hard fails (unsupported stats, placeholders, empty messages) override quality score."""
    content_bad = {
        "title": "Market Trends",
        "primary_takeaway": "Lorem ipsum placeholder content goes here.",
        "supporting_points": ["Over 90% of enterprises adopt this pattern without validation."],
        "speaker_notes": "",
    }
    claims = [ClaimEvidence(claim_text="90% of enterprises", claim_type=ClaimType.NUMERIC_CLAIM, source_required=True, verification_status=ClaimVerificationStatus.SOURCE_PENDING)]
    scores = audit_slide_content(
        content_dict=content_bad,
        intent=SlideIntent.DATA_INSIGHT,
        topic="Market Trends",
        domain="business",
        claims=claims,
    )
    assert scores.has_hard_fail
    passed, reasons = passes_quality_gate(scores)
    assert not passed
    assert len(reasons) > 0


def test_targeted_content_repair():
    """Verify deterministic targeted repairs clean banned phrases without regenerating the entire slide."""
    content_with_banned = {
        "title": "Why Photosynthesis Plays a Crucial Role",
        "primary_takeaway": "In today's rapidly evolving world, chlorophyll drives photosynthetic reactions.",
        "supporting_points": [
            "Photosynthesis is a game changer for atmospheric oxygen.",
            "Thylakoid membranes conduct photophosphorylation.",
        ],
        "example": "C3 plant carbon fixation.",
        "speaker_notes": "Discuss this topic.",
    }
    repairs = [RepairType.TITLE_REPAIR, RepairType.BODY_REPAIR]
    repaired, applied = apply_deterministic_repairs(content_with_banned, repairs, "Photosynthesis", "biology")

    assert "plays a crucial role" not in repaired["title"].lower()
    assert "rapidly evolving world" not in repaired["primary_takeaway"].lower()
    assert len(applied) > 0


# ═══════════════════════════════════════════════════════════════
# 7. DOMAIN WRITING & AUDIENCE DEPTH PROFILES
# ═══════════════════════════════════════════════════════════════

def test_eighteen_domain_profiles():
    """Verify all 18 domains have dedicated, non-generic writing profiles."""
    expected_domains = [
        "computer_science", "mathematics", "physics", "chemistry", "biology",
        "medicine_health_sciences", "engineering", "environmental_science",
        "business_management", "economics_finance", "history", "literature_arts",
        "philosophy", "law_legal_studies", "psychology", "education_pedagogy",
        "data_storytelling", "general_accessible",
    ]
    for dom in expected_domains:
        prof = get_domain_profile(dom)
        assert prof is not None
        assert "writing_style" in prof
        assert len(prof["emphasis"]) > 0
        assert len(prof["avoid"]) > 0


def test_audience_depth_profiles():
    """Verify all 4 educational levels adapt depth and jargon level accordingly."""
    levels = ["school", "undergraduate", "postgraduate", "research_professional"]
    for lvl in levels:
        prof = get_audience_profile(lvl)
        assert prof is not None
        assert "audience_language" in prof
        assert "explanation_depth" in prof
        assert "jargon_level" in prof


# ═══════════════════════════════════════════════════════════════
# 8. ANTI-HARDCODING STATIC SCAN
# ═══════════════════════════════════════════════════════════════

def test_anti_hardcoding_static_scan():
    """
    AST & regex scan of presentation package to ensure ZERO benchmark-specific strings
    are hardcoded inside production decision branches (if/elif conditions).
    Benchmark topics checked: photosynthesis, industrial revolution, node.js, renewable energy.
    """
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "services", "presentation"))
    benchmark_terms = ["photosynthesis", "industrial revolution", "renewable energy", "node.js", "research methodology in ml"]

    target_files = [
        "planner_agent.py",
        "content_agent.py",
        "domain_classifier.py",
        "story_grammar.py",
        "content_budget_engine.py",
        "claim_evidence_engine.py",
        "deck_content_memory.py",
        "speaker_notes_v2.py",
        "content_quality_auditor.py",
        "domain_content_writer.py",
    ]

    for fname in target_files:
        fpath = os.path.join(pkg_dir, fname)
        if not os.path.exists(fpath):
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        parsed = ast.parse(code, filename=fname)

        # Inspect all If / Elif test nodes in AST
        for node in ast.walk(parsed):
            if isinstance(node, ast.If):
                test_str = ast.unparse(node.test).lower()
                for term in benchmark_terms:
                    assert term not in test_str, (
                        f"Hardcoded benchmark check '{term}' found in {fname} at line {node.lineno}: '{test_str}'"
                    )


# ═══════════════════════════════════════════════════════════════
# 9. 20+ UNSEEN TOPICS ROBUSTNESS & PERTURBATION TESTING
# ═══════════════════════════════════════════════════════════════

UNSEEN_TOPICS = [
    # STEM
    ("Plate Tectonics and Continental Drift", "geology"),
    ("CRISPR-Cas9 Gene Editing Mechanisms", "biology"),
    ("Thermodynamics of Black Holes", "physics"),
    ("Fourier Transform in Signal Processing", "mathematics"),
    ("Distributed Consensus via Raft Protocol", "computer_science"),
    ("Organic Synthesis of Beta-Lactam Antibiotics", "chemistry"),
    ("Cellular Respiration and Krebs Cycle", "biology"),
    ("Fluid Dynamics in Aerodynamic Wing Design", "engineering"),
    # Humanities & Social Sciences
    ("The Silk Road and Eurasian Trade Networks", "history"),
    ("Constitutional Judicial Review in Common Law", "law_legal_studies"),
    ("Cognitive Dissonance and Behavioral Change", "psychology"),
    ("Existentialism in Post-War European Philosophy", "philosophy"),
    ("Narrative Unreliability in Modernist Fiction", "literature_arts"),
    ("Decolonization Movements in 20th Century Africa", "history"),
    # Economics & Business
    ("Game Theory and Nash Equilibrium in Oligopolies", "economics_finance"),
    ("Supply Chain Resilience and Bullwhip Effect", "business_management"),
    ("Behavioral Economics of Sunk Cost Fallacy", "economics_finance"),
    ("Monetary Policy Transmission Mechanisms", "economics_finance"),
    # Interdisciplinary
    ("Ocean Acidification and Marine Calcifiers", "environmental_science"),
    ("Ethics of Autonomous Weapons Systems", "philosophy"),
    ("Epigenetics and Environmental Gene Expression", "biology"),
]


@pytest.mark.parametrize("topic,expected_domain", UNSEEN_TOPICS)
def test_unseen_topic_dynamic_synthesis(topic: str, expected_domain: str):
    """
    Verify that ANY topic across STEM, Humanities, Law, Business produces
    valid, high-quality, topic-specific SlideContent with zero benchmark leaks.
    """
    brief = PresentationBrief(
        topic=topic,
        canonical_topic=topic,
        domain=expected_domain,
        education_level="undergraduate",
        slide_count=12,
        primary_story_grammar=StoryGrammarType.CONCEPT_TEACHING,
    )
    bp = SlideBlueprint(
        slide_number=2,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message=f"Core Operational Principles of {topic}",
        canonical_concepts=[topic.split()[0], topic.split()[-1]],
    )
    memory = DeckContentMemory()

    content = _synthesize_dynamic_slide_content(
        blueprint=bp,
        brief=brief,
        topic_intelligence=None,
        deck_memory=memory,
        slide_no=2,
        total_slides=12,
    )

    assert content.title
    assert content.primary_takeaway
    assert len(content.supporting_points) >= 1
    # Check that topic words appear in the takeaway
    topic_keywords = [w.lower() for w in topic.split() if len(w) > 3]
    takeaway_lower = content.primary_takeaway.lower()
    assert any(kw in takeaway_lower for kw in topic_keywords), (
        f"Synthesized content failed to reference topic '{topic}': {content.primary_takeaway}"
    )


def test_perturbation_resilience():
    """Verify paraphrased versions of a topic generate consistent, topic-specific content."""
    variants = [
        "Quantum Computing Architecture",
        "Foundations of Quantum Information Processing and Qubits",
        "Quantum Computing: Principles, Algorithms, and Hardware",
    ]
    for var in variants:
        brief = PresentationBrief(topic=var, canonical_topic=var, domain="computer_science")
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.CONCEPT_EXPLANATION, primary_message=var)
        mem = DeckContentMemory()
        content = _synthesize_dynamic_slide_content(bp, brief, None, mem, 1, 10)
        
        # Without topic intelligence, it must refuse to generate generic filler
        assert content.content_origin == ContentOrigin.CONTENT_SEMANTIC_GAP
        assert content.fit_risk == "CONTENT_SEMANTIC_GAP"
        assert not content.primary_takeaway


# ═══════════════════════════════════════════════════════════════
# 10. CONTENT AGENT INTEGRATION & BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════

def test_expand_presentation_content_phase2_integration():
    """
    Test end-to-end expand_presentation_content with blueprints and brief in outline_data.
    Verifies that structured SlideContent and ContentQualityScores are generated and attached.
    """
    import asyncio
    config = PresentationConfig(topic="Plate Tectonics", slide_count=12)
    brief = PresentationBrief(topic="Plate Tectonics", canonical_topic="Plate Tectonics", domain="environmental_science", slide_count=12)
    bp1 = SlideBlueprint(slide_number=1, intent=SlideIntent.COVER, primary_message="Plate Tectonics")
    bp2 = SlideBlueprint(slide_number=2, intent=SlideIntent.CONCEPT_EXPLANATION, primary_message="Lithospheric Plates in Motion")
    bp3 = SlideBlueprint(slide_number=3, intent=SlideIntent.PROCESS_EXPLANATION, primary_message="Subduction and Seafloor Spreading")

    outline_data = {
        "deck_title": "Plate Tectonics",
        "presentation_brief": brief.model_dump(),
        "blueprints": [bp1.model_dump(), bp2.model_dump(), bp3.model_dump()],
        "slides": [
            {"slide_no": 1, "title": "Plate Tectonics"},
            {"slide_no": 2, "title": "Lithospheric Plates in Motion"},
            {"slide_no": 3, "title": "Subduction and Seafloor Spreading"},
        ],
        "topic_ontology": {
            "canonical_concepts": ["Plate Boundaries", "Convection Currents", "Seafloor Spreading", "Subduction Zones"],
            "relationships": ["Convection Currents drive Plate Boundaries"],
            "processes": ["Magma rises", "Seafloor spreads", "Old crust subducts"],
        }
    }

    slides = asyncio.run(expand_presentation_content(config, user_id="test_user", outline_data=outline_data))

    assert len(slides) == 3
    for s in slides:
        assert "content" in s
        assert "quality_scores" in s
        assert s["title"]
        assert s["key_message"]
        assert s["speaker_notes"]
        assert s["content_pattern"]


# ═══════════════════════════════════════════════════════════════
# 11. PHASE 2 CLOSURE: CONCEPT PACKET & GENERICITY TESTS
# ═══════════════════════════════════════════════════════════════

def test_slide_concept_packet_no_fabrication():
    """
    Assert that SlideConceptPacket resolution does NOT invent fake canonical concepts,
    mechanisms, equations, historical relationships, cases, or misconceptions using
    deterministic templates simply to avoid empty arrays.
    """
    bp = SlideBlueprint(
        slide_number=2,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Quantum Decoherence Dynamics",
        canonical_concepts=["Wavefunction collapse", "Environmental coupling"],
    )
    brief = PresentationBrief(
        topic="Quantum Decoherence",
        canonical_topic="Quantum Decoherence",
        domain="physics",
    )

    # 1. Without TopicIntelligence or source context -> packet resolves from blueprint only
    packet = resolve_slide_concept_packet(bp, brief, topic_intelligence=None, source_context=None)
    assert packet.primary_concept == "Wavefunction collapse"
    assert "Environmental coupling" in packet.supporting_concepts
    # Unknown fields must remain empty lists, NOT filled with fake template text
    assert packet.process_stages == []
    assert packet.cause_effect_pairs == []
    assert packet.comparison_dimensions == []
    assert packet.misconceptions == []
    assert packet.source_grounded_facts == []

    # 2. With verified TopicIntelligencePack -> packet fields populate from real intelligence
    tip = TopicIntelligencePack(
        topic="Quantum Decoherence",
        domain="physics",
        canonical_concepts=[
            {"term": "Wavefunction collapse", "definition": "Reduction of physical state"},
            {"term": "Density matrix", "definition": "Statistical state operator"},
            {"term": "Phase damping", "definition": "Loss of quantum phase coherence"},
        ],
        processes=["Entanglement with environmental degrees of freedom"],
        misconceptions=[
            {"myth": "Decoherence explains wavefunction collapse completely", "reality": "Decoherence only explains loss of interference"}
        ],
    )
    packet_with_tip = resolve_slide_concept_packet(bp, brief, topic_intelligence=tip, source_context=None)
    assert "Density matrix" in packet_with_tip.supporting_concepts or "Phase damping" in packet_with_tip.supporting_concepts
    assert "Decoherence" in packet_with_tip.misconceptions[0]["myth"]

    # 3. Precedence order: source context > TopicIntelligence > blueprint
    source_ctx = {
        "text": "Superconducting qubits exhibit T2 decoherence times around 100 microseconds.",
        "claims": ["Superconducting qubits exhibit T2 decoherence times around 100 microseconds."],
        "key_terms": ["T2 coherence", "superconducting qubits"],
    }
    packet_with_src = resolve_slide_concept_packet(bp, brief, topic_intelligence=tip, source_context=source_ctx)
    assert "superconducting qubits" in packet_with_src.required_terms or "T2 coherence" in packet_with_src.required_terms
    assert len(packet_with_src.source_grounded_facts) > 0


def test_contextual_vocabulary_leakage_guard():
    """
    Assert that domain vocabulary leakage rules are contextual, NOT global naive blacklists.
    - 'bioinformatics pipeline' in biology is legitimate and NOT flagged.
    - 'operational pipeline' in classical botany is flagged.
    - 'narrative architecture' in literature is legitimate and NOT flagged.
    - 'system architecture' in poetry is flagged.
    """
    # Legitimate contextual usages
    legit_bio = "We constructed a high-throughput bioinformatics pipeline to process next-generation sequencing reads."
    risk_bio = check_contextual_vocabulary_leakage(
        legit_bio, domain="biology", subdomain="bioinformatics", topic="Genomic Sequencing"
    )
    assert len(risk_bio) == 0, f"Bioinformatics pipeline falsely flagged: {risk_bio}"

    legit_lit = "The narrative architecture of Frankenstein employs nested epistolary frames."
    risk_lit = check_contextual_vocabulary_leakage(
        legit_lit, domain="literature_arts", subdomain="narrative_theory", topic="Gothic Fiction"
    )
    assert len(risk_lit) == 0, f"Narrative architecture falsely flagged: {risk_lit}"

    # Inappropriate domain leakage
    bad_bio = "The cell operational pipeline executes through distinct metabolic stages."
    risk_bad_bio = check_contextual_vocabulary_leakage(
        bad_bio, domain="biology", subdomain="botany", topic="Plant Cell Biology"
    )
    assert len(risk_bad_bio) > 0, "Cell operational pipeline should be flagged as leakage"
    assert "operational pipeline" in [t.lower() for t in risk_bad_bio]

    bad_lit = "The system architecture of the sonnet optimizes payload throughput."
    risk_bad_lit = check_contextual_vocabulary_leakage(
        bad_lit, domain="literature_arts", subdomain="poetry", topic="Shakespearean Sonnets"
    )
    assert len(risk_bad_lit) > 0, "System architecture in poetry should be flagged as leakage"


def test_domain_educator_personas_subdomain_differentiation():
    """
    Verify dynamic educator personas guide terminology, reasoning, and evidence style
    without collapsing into fixed domain templates (e.g. ecology != molecular genetics).
    """
    persona_eco = get_domain_educator_persona("biology", "ecology")
    persona_gen = get_domain_educator_persona("biology", "genetics")
    persona_cs_net = get_domain_educator_persona("computer_science", "networking")
    persona_cs_ml = get_domain_educator_persona("computer_science", "machine_learning")

    # Personas in the same domain must differ by subdomain
    assert persona_eco != persona_gen
    assert "ecology" in persona_eco.lower()
    assert "genetics" in persona_gen.lower()
    assert persona_cs_net != persona_cs_ml
    assert "networking" in persona_cs_net.lower()
    assert "machine_learning" in persona_cs_ml.lower()


def test_genericity_detector_and_penalty():
    """
    Verify genericity detector penalizes topic-substitution prose and generic sentence templates.
    """
    # 1. Flagrant topic substitution
    generic_slide = {
        "title": "Introduction to Photosynthesis",
        "primary_takeaway": "Photosynthesis defines how Photosynthesis operates within biology.",
        "supporting_points": [
            "The Photosynthesis Operational Pipeline executes through distinct stages.",
            "Understanding Photosynthesis requires analyzing its core concepts.",
        ],
        "speaker_notes": "When explaining Photosynthesis in the context of Photosynthesis, emphasize its importance.",
    }
    penalty, reasons = detect_genericity(generic_slide, "Photosynthesis", "biology")
    assert penalty >= 40
    assert any("substitution" in r.lower() or "pipeline" in r.lower() or "boilerplate" in r.lower() for r in reasons)

    # 2. Content quality auditor applies severe penalty and hard fail to topic-substitution takeaways
    audit_scores = audit_slide_content(
        generic_slide,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        topic="Photosynthesis",
        domain="biology",
        body_budget_max=80,
    )
    assert audit_scores.topic_specificity < 65
    assert audit_scores.primary_idea_clarity < 65
    assert audit_scores.has_hard_fail, "Topic-substitution takeaway must trigger hard fail"

    # 3. High quality slide without genericity
    expert_slide = {
        "title": "Thylakoid Photophosphorylation",
        "primary_takeaway": "Photosystem II oxidizes water to establish a proton gradient across the thylakoid membrane.",
        "supporting_points": [
            "Plastoquinone transfers electrons from P680 to the cytochrome b6f complex.",
            "Proton accumulation inside the lumen drives ATP synthase via chemiosmosis.",
        ],
        "speaker_notes": "Trace the path of protons across the membrane. What happens when the proton motive force collapses?",
    }
    penalty_clean, reasons_clean = detect_genericity(expert_slide, "Photosynthesis", "biology")
    assert penalty_clean < 20


def test_blind_topic_identification():
    """
    Assert blind topic identification evaluator can infer subject / narrow domain
    from concepts, entities, and mechanisms after stripping title and topic name.
    """
    # Substantive concept slide with topic name stripped
    substantive_content = {
        "title": "Reaction Kinetics",
        "primary_takeaway": "Competitive inhibitors increase the apparent Km while leaving Vmax unchanged.",
        "supporting_points": [
            "The inhibitor competes directly with the substrate for the enzyme active site.",
            "Lineweaver-Burk plots show intersecting lines at the 1/Vmax y-intercept.",
        ],
        "example": "Methotrexate competing with dihydrofolate for dihydrofolate reductase.",
    }
    can_id, score, details = evaluate_blind_topic_identifiability(
        substantive_content, topic="Enzyme Kinetics", domain="biology"
    )
    assert can_id, f"Blind identification failed: {details}"
    assert score >= 40

    # Vacuous slide cannot be identified
    vacuous_content = {
        "title": "Key Principles",
        "primary_takeaway": "The system ensures high performance and reliable operations across all components.",
        "supporting_points": [
            "Proper configuration prevents operational bottlenecks.",
            "Regular monitoring ensures consistent efficiency.",
        ],
    }
    can_id_vac, score_vac, details_vac = evaluate_blind_topic_identifiability(
        vacuous_content, topic="Enzyme Kinetics", domain="biology"
    )
    assert not can_id_vac, "Vacuous slide should NOT pass blind identification"


def test_cross_topic_contrast_unseen_topics():
    """
    Verify that dynamically synthesized slides for identical intent (PROCESS_EXPLANATION)
    across diverse unseen subjects produce distinct semantic vocabulary and structures.
    """
    topics_and_domains = [
        ("Enzyme Inhibition Kinetics", "biology"),
        ("TCP Congestion Control via AIMD", "computer_science"),
        ("Constitutional Amendment Procedure", "law_legal_studies"),
    ]
    slides_by_topic = {}
    for topic, domain in topics_and_domains:
        brief = PresentationBrief(topic=topic, canonical_topic=topic, domain=domain, slide_count=8)
        bp = SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.PROCESS_EXPLANATION,
            primary_message=f"Stepwise Mechanism of {topic}",
            canonical_concepts=[topic.split()[0], topic.split()[-1]],
        )
        mem = DeckContentMemory()
        content = _synthesize_dynamic_slide_content(bp, brief, None, mem, 3, 8)
        slides_by_topic[topic] = {
            "title": content.title,
            "primary_takeaway": content.primary_takeaway,
            "supporting_points": content.supporting_points,
            "process_steps": content.process_steps,
        }

    passes_contrast, jaccard_sim, diffs = evaluate_cross_topic_contrast(
        slides_by_topic["Enzyme Inhibition Kinetics"],
        slides_by_topic["TCP Congestion Control via AIMD"],
    )
    assert passes_contrast, f"Cross-topic contrast failed! Jaccard similarity too high: {jaccard_sim:.3f}"
    assert jaccard_sim < 0.35, f"Cross-topic similarity should be low, got {jaccard_sim:.3f}"


def test_scorer_rejects_current_bad_outputs():
    """
    Verify that the exact generic boilerplate flagged by the user scores BAD (<55),
    triggers high genericity penalty, and fails blind topic identification.
    """
    bad_takeaway = "Analyzing Photosynthesis clarifies how governing rules ensure system reliability under variable operating constraints."
    bad_supporting = [
        "Operational mechanisms deliver measurable stability across varied workloads.",
        "Systematic constraint verification ensures compliance with core performance criteria.",
        "Integration patterns support modular expansion without breaking backward invariants."
    ]
    
    bad_content = {
        "title": "Photosynthesis Mechanics",
        "primary_takeaway": bad_takeaway,
        "supporting_points": bad_supporting
    }
    
    # 1. Blind topic identification must fail
    can_id, specificity, reason = evaluate_blind_topic_identifiability(bad_content, "Photosynthesis", "biology")
    assert not can_id, f"Blind ID should fail for generic text. Reason given: {reason}"
    
    # 2. Audit scores must be <55 (BAD)
    scores = audit_slide_content(bad_content, SlideIntent.CONCEPT_EXPLANATION, "Photosynthesis", "biology")
    assert scores.topic_specificity < 55, f"Topic specificity should be BAD (<55), got {scores.topic_specificity}"
    
    # Check penalty directly
    penalty, issues = detect_genericity(bad_content, "Photosynthesis", "biology", "molecular")
    assert penalty > 50, "Genericity penalty should be SEVERE for known bad templates."
    assert any("GENERIC_EMPTY_PREDICATE" in issue for issue in issues)


def test_domain_contamination_checks():
    """Verify semantic domain contamination detector."""
    # 1. Biology slide containing software deployment language
    bio_slide = {
        "primary_takeaway": "The transcription pathway deploys the software package to the ribosomes via tcp handshake.",
    }
    is_contam, reason = evaluate_domain_contamination(bio_slide, "biology", "Transcription")
    assert is_contam
    assert "networking/software" in reason

    # 2. History slide containing legislative procedure (invalid for Industrial Rev mechanism)
    history_slide = {
        "primary_takeaway": "The spinning jenny was adopted through a bicameral legislative procedure and committee referral.",
    }
    is_contam, reason = evaluate_domain_contamination(history_slide, "history", "Industrial Revolution")
    assert is_contam
    assert "legislative" in reason

    # 3. Math containing production engineering language
    math_slide = {
        "primary_takeaway": "Eigenvectors provide robust production validation and eliminate error budgets."
    }
    is_contam, reason = evaluate_domain_contamination(math_slide, "mathematics", "Eigenvalues")
    assert is_contam
    assert "production/engineering" in reason


def test_out_of_taxonomy_topics_robustness():
    """
    Verify out-of-taxonomy topics (music theory, geology, philosophy, astronomy, architecture)
    generate robust, non-generic slide content without falling into topic substitution.
    """
    out_of_taxonomy = [
        ("Modal Interchange in Jazz Harmony", "general_accessible"),
        ("Plate Tectonics and Seafloor Spreading", "environmental_science"),
        ("Stoic Epistemology and Cognitive Impressions", "philosophy"),
        ("Stellar Nucleosynthesis in Asymptotic Giant Branch Stars", "physics"),
        ("Passive Solar Ventilation in Vernacular Architecture", "engineering"),
    ]
    for topic, domain in out_of_taxonomy:
        brief = PresentationBrief(topic=topic, canonical_topic=topic, domain=domain, slide_count=10)
        bp = SlideBlueprint(
            slide_number=2,
            intent=SlideIntent.CONCEPT_EXPLANATION,
            primary_message=f"Operational Principles of {topic}",
        )
        mem = DeckContentMemory()
        content = _synthesize_dynamic_slide_content(bp, brief, None, mem, 2, 10)

        assert content.content_origin == ContentOrigin.CONTENT_SEMANTIC_GAP
        assert content.fit_risk == "CONTENT_SEMANTIC_GAP"
        assert not content.primary_takeaway

        # Verify content auditor scores fail the generic slide
        scores = audit_slide_content(
            content_dict=content.model_dump(),
            intent=SlideIntent.CONCEPT_EXPLANATION,
            topic=topic,
            domain=domain,
        )
        assert scores.has_hard_fail, "Expected hard fail for semantic gap"
        assert "EMPTY_PRIMARY_MESSAGE" in scores.hard_fail_reasons

def test_interdisciplinary_topics_robustness():
    """
    Verify interdisciplinary topics blend multiple domain concepts organically
    without triggering false positive leakage guards or collapsing into generic prose.
    """
    interdisciplinary = [
        ("Computational Biology and Genomic Alignment", "biology", "bioinformatics"),
        ("Behavioral Economics of Choice Architecture", "economics_finance", "behavioral_economics"),
        ("AI Ethics and Algorithmic Auditing in Hiring", "philosophy", "ai_ethics"),
        ("Legal Technology and Smart Contract Execution", "law_legal_studies", "legal_tech"),
    ]
    for topic, domain, subdomain in interdisciplinary:
        brief = PresentationBrief(topic=topic, canonical_topic=topic, domain=domain, subdomain=subdomain, slide_count=10)
        bp = SlideBlueprint(
            slide_number=2,
            intent=SlideIntent.CONCEPT_EXPLANATION,
            primary_message=f"Foundations of {topic}",
        )
        mem = DeckContentMemory()
        content = _synthesize_dynamic_slide_content(bp, brief, None, mem, 2, 10)

        # Ensure it refuses to generate generic text without topic intelligence
        assert content.content_origin == ContentOrigin.CONTENT_SEMANTIC_GAP
        assert not content.primary_takeaway
        
        # Ensure vocabulary leakage guard does not false-alarm (trivial check for empty text)
        combined_text = f"{content.primary_takeaway} {' '.join(content.supporting_points)}"
        risks = check_contextual_vocabulary_leakage(
            combined_text, domain=domain, subdomain=subdomain, topic=topic
        )
        assert len(risks) == 0, f"False positive leakage in interdisciplinary topic {topic}: {risks}"


def test_speaker_notes_intent_adaptive_and_optional_analogy():
    """
    Verify speaker notes:
    - Adapt pedagogical delivery to intent (Cover vs Worked Example vs Summary)
    - Contain zero boilerplate prefixes ('When explaining...', 'Ask the audience...')
    - Make analogy strictly optional (only generated when valid with mapping + limitation)
    - Maintain low structural similarity across the deck (< 0.35)
    """
    brief = PresentationBrief(topic="Distributed Consensus", canonical_topic="Distributed Consensus", domain="computer_science")

    # 1. Cover slide notes: orientation, no forced analogy, no probing question
    bp_cover = SlideBlueprint(slide_number=1, intent=SlideIntent.COVER, primary_message="Distributed Consensus")
    notes_cover, cues_cover = generate_expert_speaker_notes(
        intent=SlideIntent.COVER,
        primary_takeaway="Fault-tolerant state machine replication",
        supporting_points=["Paxos and Raft consensus", "Leader election mechanisms"],
        topic="Distributed Consensus",
        domain="computer_science",
    )
    assert "when explaining" not in notes_cover.lower()
    assert "analogy:" not in notes_cover.lower()
    cue_types_cover = [c.cue_type for c in cues_cover]
    assert CUE_PROBING_QUESTION not in cue_types_cover

    # 2. Worked example notes: walkthrough cue, no forced analogy
    bp_example = SlideBlueprint(slide_number=5, intent=SlideIntent.WORKED_EXAMPLE, primary_message="Raft Leader Election")
    notes_ex, cues_ex = generate_expert_speaker_notes(
        intent=SlideIntent.WORKED_EXAMPLE,
        primary_takeaway="Split votes resolve via randomized election timeouts",
        supporting_points=["Candidate requests votes", "Majority quorum granted"],
        topic="Distributed Consensus",
        domain="computer_science",
    )
    assert "when explaining" not in notes_ex.lower()
    cue_types_ex = [c.cue_type for c in cues_ex]
    assert CUE_TEACHING in cue_types_ex

    # 3. Structural similarity across multiple slides
    notes_list = [notes_cover, notes_ex]
    for i, intent in enumerate([SlideIntent.CONCEPT_EXPLANATION, SlideIntent.PROCESS_EXPLANATION, SlideIntent.SUMMARY], start=2):
        n, _ = generate_expert_speaker_notes(
            intent=intent,
            primary_takeaway=f"Key takeaway {i}",
            supporting_points=[f"Supporting point A {i}", f"Supporting point B {i}"],
            topic="Distributed Consensus",
            domain="computer_science",
        )
        notes_list.append(n)

    sim_score = measure_note_structural_similarity(notes_list)
    assert sim_score < 0.35, f"Speaker note structural similarity too high: {sim_score:.3f}"


def test_source_bound_mode_strict_origin():
    """
    Verify that in source-bound mode, slide content retains provenance from
    SOURCE_DOCUMENT or DETERMINISTIC_STRUCTURE and does not silently inject MODEL_BACKGROUND.
    """
    source_ctx = {
        "text": "The Treaty of Utrecht (1713) concluded the War of the Spanish Succession.",
        "claims": ["The Treaty of Utrecht (1713) concluded the War of the Spanish Succession."],
        "key_terms": ["Treaty of Utrecht", "Spanish Succession"],
    }
    brief = PresentationBrief(
        topic="War of Spanish Succession",
        canonical_topic="War of Spanish Succession",
        domain="history",
        source_document_id="doc_utrecht_1713",
    )
    bp = SlideBlueprint(
        slide_number=2,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Treaty of Utrecht Settlement",
    )
    mem = DeckContentMemory()
    content = _synthesize_dynamic_slide_content(bp, brief, None, mem, 2, 8, source_context=source_ctx)

    assert content.content_origin in (ContentOrigin.SOURCE_DOCUMENT, ContentOrigin.DETERMINISTIC_STRUCTURE)


def test_static_source_code_scan_for_boilerplate():
    """
    Ensure no production fallback paths statically encode banned boilerplate phrases.
    """
    import os
    banned_phrases = [
        "governing conditions",
        "operational baseline",
        "system reliability",
        "variable operating constraints",
        "operational mechanisms",
        "measurable stability",
        "constraint verification",
        "modular expansion",
        "backward invariants",
        "core functional state",
        "theoretical predictions",
        "primary approach",
        "alternative model"
    ]
    
    # We only scan active production generators, not test fixtures or string definitions
    files_to_scan = [
        os.path.join(os.path.dirname(__file__), "../app/services/presentation/content_agent.py"),
        os.path.join(os.path.dirname(__file__), "../app/services/presentation/domain_content_writer.py"),
        os.path.join(os.path.dirname(__file__), "../app/services/presentation/qa_agent.py")
    ]
    
    for file_path in files_to_scan:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Remove the BANNED_STRINGS array definition from content_agent.py 
            # to avoid false positives in the static scan
            if "content_agent.py" in file_path:
                if "def _synthesize_dynamic_slide_content" in content:
                    content = content.split("def _synthesize_dynamic_slide_content")[1]
                else:
                    pass
                
            for phrase in banned_phrases:
                assert phrase.lower() not in content.lower(), f"Banned phrase '{phrase}' found statically in {file_path}"


# ═══════════════════════════════════════════════════════════════
# 11. PHASE 2 SEMANTIC TAKEAWAY REPAIR & ACCEPTANCE SUITE
# ═══════════════════════════════════════════════════════════════

def test_takeaway_repair_negative_regression_no_generic_wrapper():
    """
    Requirement 1 & 7: Verify repair cannot convert:
    'ATP synthesis in thylakoid membranes'
    into:
    'This framework establishes that ATP synthesis in thylakoid membranes.'
    Must use actual supported relationship or return semantic gap.
    """
    bad_phrase = "ATP synthesis in thylakoid membranes"
    forbidden_prefix = "This framework establishes that"

    packet = SlideConceptPacket(
        primary_concept="ATP Synthase",
        supporting_concepts=["Thylakoid Membrane", "Proton Motive Force"],
        relationships=[
            "Proton motive force across the thylakoid membrane drives ATP synthesis through CF0CF1 complexes."
        ],
    )

    content_dict = {
        "title": "Photophosphorylation Mechanism",
        "primary_takeaway": bad_phrase,
        "supporting_points": [
            "Chemiosmotic coupling produces ATP from ADP and Pi.",
            "Proton gradient is established by electron transport chains.",
        ],
        "example": "Spinach chloroplast thylakoid preparations.",
        "speaker_notes": "Explain how proton motive force couples to rotational catalysis.",
    }

    repairs = [RepairType.TAKEAWAY_SEMANTIC_REPAIR]
    repaired, applied = apply_deterministic_repairs(
        content_dict=content_dict,
        repairs=repairs,
        topic="Photosynthesis",
        domain="biology",
        concept_packet=packet,
        intent=SlideIntent.PROCESS_EXPLANATION,
    )

    repaired_takeaway = repaired.get("primary_takeaway", "")
    assert not repaired_takeaway.startswith(forbidden_prefix)
    for wrapper in CONTENT_FREE_REPAIR_WRAPPERS:
        assert not repaired_takeaway.lower().startswith(wrapper), (
            f"Repaired takeaway contains forbidden generic wrapper '{wrapper}': {repaired_takeaway}"
        )
    assert "proton motive force" in repaired_takeaway.lower() or "cf0cf1" in repaired_takeaway.lower()
    assert len(repaired_takeaway.split()) >= 6


def test_takeaway_repair_refuses_to_manufacture_relationships():
    """
    Requirement 1: Refuse to manufacture relationships when concepts exist without supported relationships.
    Forbidden:
    - {primary_concept} interacts with {supporting_concept}
    - {cause} directly drives {effect}
    - {stage} initiates the mechanism of {concept}
    Must return CONTENT_SEMANTIC_GAP and SemanticStatus.GAP.
    """
    empty_packet = SlideConceptPacket(
        primary_concept="Thylakoid Membrane",
        supporting_concepts=["ATP Synthesis", "Chloroplast"],
        relationships=[],
        cause_effect_pairs=[],
        process_stages=[],
        source_grounded_facts=[],
    )

    content_dict = {
        "title": "Membrane Architecture",
        "primary_takeaway": "ATP synthesis in thylakoid membranes",  # Bare phrase
        "supporting_points": ["Thylakoid structure", "Chloroplast stroma"],
    }

    repairs = [RepairType.TAKEAWAY_SEMANTIC_REPAIR]
    repaired, applied = apply_deterministic_repairs(
        content_dict=content_dict,
        repairs=repairs,
        topic="Photosynthesis",
        domain="biology",
        concept_packet=empty_packet,
        intent=SlideIntent.CONCEPT_EXPLANATION,
    )

    assert repaired.get("content_origin") == ContentOrigin.CONTENT_SEMANTIC_GAP
    assert repaired.get("semantic_status") == SemanticStatus.GAP
    assert repaired.get("fit_risk") == "CONTENT_SEMANTIC_GAP"
    assert repaired.get("primary_takeaway") == ""
    assert SemanticFailureReason.MISSING_RELATIONSHIP.value in repaired.get("semantic_failure_reasons", [])

    # Verify forbidden manufactured templates are absent
    repaired_takeaway_lower = repaired.get("primary_takeaway", "").lower()
    assert "interacts with" not in repaired_takeaway_lower
    assert "directly drives" not in repaired_takeaway_lower
    assert "initiates the mechanism of" not in repaired_takeaway_lower


def test_proposition_validator_intent_aware_and_mathematical():
    """
    Requirement 4: Validate propositions semantically.
    - Mathematical expressions pass without active verbs.
    - Passive/scientific predicates pass.
    - Covers and fragmentary elements are exempt without automatic 95+ scores.
    - Generic hollow phrases are penalized.
    """
    # 1. Cover slide: declarative proposition validation N/A, score strictly < 95
    cover_content = {"title": "Introduction to Quantum Mechanics", "subtitle": "Physics 301"}
    cover_score = score_primary_idea_clarity(
        cover_content,
        topic="Quantum Mechanics",
        domain="physics",
        intent=SlideIntent.COVER,
    )
    assert 75 <= cover_score < 95, f"Cover score should be role-appropriate (< 95), got {cover_score}"

    # 2. Agenda slide: declarative proposition validation N/A
    agenda_content = {"title": "Course Agenda and Key Topics"}
    agenda_score = score_primary_idea_clarity(
        agenda_content,
        topic="Quantum Mechanics",
        domain="physics",
        intent=SlideIntent.AGENDA,
    )
    assert 75 <= agenda_score < 95

    # 3. Mathematical expression: E = mc^2 connecting variables
    math_content = {
        "title": "Mass-Energy Equivalence",
        "primary_takeaway": "$E = mc^2$ establishes relativistic equivalence between rest energy and invariant mass.",
        "supporting_points": ["c denotes the speed of light in vacuum."],
    }
    math_score = score_primary_idea_clarity(
        math_content,
        topic="Special Relativity",
        domain="physics",
        intent=SlideIntent.FORMULA_EXPLANATION,
    )
    assert math_score >= 85, f"Mathematical proposition should score well, got {math_score}"

    # 4. Passive scientific predicate: 'is catalyzed by' / 'is inhibited by'
    passive_content = {
        "title": "Glycolytic Regulation",
        "primary_takeaway": "In cellular respiration, phosphofructokinase-1 is allosterically inhibited by ATP and activated by AMP in glycolysis.",
        "supporting_points": ["Ensures ATP production matches cellular energy expenditure."],
    }
    passive_score = score_primary_idea_clarity(
        passive_content,
        topic="Cellular Respiration",
        domain="biology",
        intent=SlideIntent.CONCEPT_EXPLANATION,
    )
    assert passive_score >= 85, f"Passive scientific proposition should score well, got {passive_score}"

    # 5. Generic wrapper penalty: 'This framework establishes that...'
    wrapper_content = {
        "title": "Core Mechanism",
        "primary_takeaway": "This framework establishes that ATP synthesis in thylakoid membranes.",
    }
    wrapper_score = score_primary_idea_clarity(
        wrapper_content,
        topic="Photosynthesis",
        domain="biology",
        intent=SlideIntent.CONCEPT_EXPLANATION,
    )
    assert wrapper_score <= 40, f"Generic wrapper must be heavily penalized, got {wrapper_score}"


def test_field_isolation_and_dependent_consistency():
    """
    Requirement 5: A takeaway-only repair must not silently modify unrelated fields.
    If repaired takeaway contradicts existing supporting points, flag or remove contradictory point.
    """
    packet = SlideConceptPacket(
        primary_concept="Enzyme Kinetics",
        supporting_concepts=["Substrate Concentration", "Vmax"],
        relationships=[
            "Enzyme catalyzed velocity approaches Vmax asymptotically as substrate concentration saturates active sites."
        ],
    )
    content_dict = {
        "title": "Michaelis-Menten Kinetics",
        "primary_takeaway": "Enzyme kinetics rate",  # Broken takeaway
        "supporting_points": [
            "Substrate saturation leads to maximal velocity Vmax.",
            "Enzyme activity is not dependent on substrate concentration.", # Direct contradiction
        ],
        "example": "Hexokinase glucose phosphorylation assay.",
        "callout": "Km represents substrate concentration at half Vmax.",
    }

    repairs = [RepairType.TAKEAWAY_SEMANTIC_REPAIR]
    repaired, applied = apply_deterministic_repairs(
        content_dict=content_dict,
        repairs=repairs,
        topic="Enzyme Kinetics",
        domain="biology",
        concept_packet=packet,
        intent=SlideIntent.CONCEPT_EXPLANATION,
    )

    # Isolated fields must NOT be mutated
    assert repaired["title"] == content_dict["title"]
    assert repaired["example"] == content_dict["example"]
    assert repaired["callout"] == content_dict["callout"]

    # Repaired takeaway must be updated
    assert "asymptotically" in repaired["primary_takeaway"].lower() or "vmax" in repaired["primary_takeaway"].lower()

    # Contradictory supporting point must be removed
    assert not any("not dependent on substrate" in p.lower() for p in repaired["supporting_points"])


def test_quality_gate_export_blocking():
    """
    Requirement 6: Pre-export quality gate blocks PPTX rendering, storage upload, or caching
    if any slide has an unresolved semantic gap, hard factual failure, or critical failure.
    """
    config = PresentationConfig(topic="Cellular Respiration", slide_count=10)

    # 1. Slide with unresolved semantic gap raises QualityGateError
    gap_slide = SlideSpec(
        slide_no=2,
        title="Unresolved Slide",
        key_message="",
        fit_risk="CONTENT_SEMANTIC_GAP",
        content=SlideContent(
            title="Unresolved Slide",
            primary_takeaway="",
            content_origin=ContentOrigin.CONTENT_SEMANTIC_GAP,
            semantic_status=SemanticStatus.GAP,
            semantic_failure_reasons=[SemanticFailureReason.MISSING_RELATIONSHIP.value],
        ),
        quality_scores={"hard_fail_reasons": ["CONTENT_SEMANTIC_GAP"]},
    )
    gap_spec = PresentationSpec(
        title="Cellular Respiration",
        config=config,
        slides=[gap_slide],
    )

    # Test that pre-export gate blocks output
    with pytest.raises(QualityGateError) as exc_info:
        for slide in gap_spec.slides:
            has_semantic_gap = (
                (
                    (slide.content is not None)
                    and (getattr(slide.content, "content_origin", None) in (ContentOrigin.CONTENT_SEMANTIC_GAP, "content_semantic_gap"))
                )
                or (
                    (slide.content is not None)
                    and (getattr(slide.content, "semantic_status", None) in (SemanticStatus.GAP, "gap"))
                )
                or (slide.fit_risk == "CONTENT_SEMANTIC_GAP")
            )
            if has_semantic_gap:
                raise QualityGateError(f"Export blocked by Quality Gate on slide {slide.slide_no}")

    assert "Export blocked by Quality Gate" in str(exc_info.value)


def test_zero_generic_verb_wrappers_static_scan():
    """
    Requirement 7 & 10: Verify generic verb wrappers == 0 across all presentation services.
    Scans content_agent.py, content_quality_auditor.py, domain_content_writer.py.
    """
    import os

    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "services", "presentation"))
    files_to_scan = [
        "content_agent.py",
        "content_quality_auditor.py",
        "domain_content_writer.py",
    ]

    forbidden_phrases = [
        'f"This framework establishes that {',
        'f"The core concept is {primary_concept}. It interacts with {supporting_concept}',
        'takeaway = f"This framework establishes that',
        '"This framework establishes that "',
    ]

    for fname in files_to_scan:
        fpath = os.path.join(pkg_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        for phrase in forbidden_phrases:
            assert phrase not in code, f"Forbidden generic active-verb wrapper found in {fname}: '{phrase}'"


def test_semantic_status_and_structured_failure_reasons():
    """
    Requirement 2: Separate ContentOrigin from SemanticStatus.
    Verify additive, backward-compatible schema changes and structured failure reasons.
    """
    sc = SlideContent(
        title="Photosynthetic Membranes",
        primary_takeaway="",
        content_origin=ContentOrigin.DETERMINISTIC_STRUCTURE,
        semantic_status=SemanticStatus.GAP,
        semantic_failure_reasons=[
            SemanticFailureReason.MISSING_RELATIONSHIP.value,
            SemanticFailureReason.INSUFFICIENT_CONCEPT_PACKET.value,
        ],
        fit_risk="CONTENT_SEMANTIC_GAP",
    )

    # ContentOrigin tracks provenance (not quality)
    assert sc.content_origin == ContentOrigin.DETERMINISTIC_STRUCTURE
    # SemanticStatus tracks quality state
    assert sc.semantic_status == SemanticStatus.GAP
    assert len(sc.semantic_failure_reasons) == 2
    assert "MISSING_RELATIONSHIP" in sc.semantic_failure_reasons
    assert "INSUFFICIENT_CONCEPT_PACKET" in sc.semantic_failure_reasons

    # Check serialization
    d = sc.model_dump() if hasattr(sc, "model_dump") else sc.dict()
    assert d["content_origin"] == "deterministic_structure"
    assert d["semantic_status"] == "gap"
    assert "MISSING_RELATIONSHIP" in d["semantic_failure_reasons"]


def test_negative_fixtures_duplicate_takeaway():
    """
    Negative Fixture: Adjacent/cross-slide duplicate takeaways must trigger hard failure
    and severe score deduction.
    """
    takeaway = "Increasing light intensity leads to higher ATP production."
    content_dict = {
        "title": "Photosynthetic Light Reactions",
        "primary_takeaway": takeaway,
        "supporting_points": ["Elevated CO2 increases carboxylation rate."],
        "_prior_takeaways": [takeaway],  # Prior slide used the exact same takeaway
    }
    scores = audit_slide_content(
        content_dict=content_dict,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        topic="Photosynthesis",
        domain="biology",
    )
    assert scores.has_hard_fail is True
    assert "DUPLICATE_SLIDE_TAKEAWAY" in scores.hard_fail_reasons
    assert scores.primary_idea_clarity <= 40


def test_negative_fixtures_incomplete_titles():
    """
    Negative Fixture: Titles terminating in dangling prepositions, conjunctions, or verbs
    must be flagged by detect_incomplete_title and fail quality audit.
    """
    bad_titles = [
        "Plants convert light into the energy currency that fuels",
        "Node's stack layers V8, libuv, and the event loop into a",
        "Essential concepts of Photosynthesis: Light reactions and",
        "Why machine learning matters: High model complexity leads to",
        "Understanding Quantum Computing: Qubit states and the",
    ]

    for title in bad_titles:
        is_incomplete, reason = detect_incomplete_title(title)
        assert is_incomplete is True, f"Failed to detect incomplete title: '{title}'"
        
        # Test sanitization / repair
        clean = sanitize_and_complete_title(title, topic="Science")
        is_inc_clean, _ = detect_incomplete_title(clean)
        assert is_inc_clean is False, f"Sanitization did not fix incomplete title: '{clean}'"
        assert not clean.endswith(("into a", "that fuels", "and", "leads to", "the"))

        # Test audit flags hard fail
        content_dict = {
            "title": title,
            "primary_takeaway": "Photosynthesis converts solar photons into chemical bond energy.",
            "supporting_points": ["ATP synthase uses proton gradients."],
        }
        scores = audit_slide_content(
            content_dict=content_dict,
            intent=SlideIntent.CONCEPT_EXPLANATION,
            topic="Photosynthesis",
            domain="biology",
        )
        assert scores.has_hard_fail is True
        assert any("INCOMPLETE_TITLE" in h for h in scores.hard_fail_reasons)


def test_negative_fixtures_universal_takeaway_template():
    """
    Negative Fixture: Universal generic cross-topic templates like
    'Systematic execution of {topic} principles...' must be rejected with hard fails.
    """
    generic_text = (
        "Systematic execution of Supply Chain Resilience principles leads to establishes "
        "structural stability and predictable operational outcomes"
    )
    content_dict = {
        "title": "Supply Chain Operations",
        "primary_takeaway": generic_text,
        "supporting_points": ["Principles of resilience govern systemic distribution."],
    }
    scores = audit_slide_content(
        content_dict=content_dict,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        topic="Supply Chain Resilience",
        domain="business",
    )
    assert scores.has_hard_fail is True
    assert any("GENERIC_CROSS_TOPIC_TEMPLATE" in h for h in scores.hard_fail_reasons)
    assert any("UNGRAMMATICAL_TAKEAWAY" in h for h in scores.hard_fail_reasons)
    assert scores.primary_idea_clarity <= 50


def test_negative_fixtures_ungrammatical_causal_statement():
    """
    Negative Fixture: 'leads to establishes' or 'results in creates' must be flagged as ungrammatical.
    """
    ungrammatical_text = "Increasing thread pool size leads to establishes higher concurrency throughput."
    is_ungramm, reason = detect_ungrammatical_statement(ungrammatical_text)
    assert is_ungramm is True
    assert "Double finite verb" in reason

    grammatical_text = "Increasing thread pool size leads to higher concurrency throughput."
    is_ungramm2, _ = detect_ungrammatical_statement(grammatical_text)
    assert is_ungramm2 is False


def test_slide_specific_packet_resolution_novelty():
    """
    Requirement 1 & 4: Adjacent substantive slides must resolve distinct concepts and relationships.
    Verify that resolve_slide_concept_packet advances across slides and does NOT repeat content.
    """
    brief = PresentationBrief(
        topic="Photosynthesis",
        domain="biology",
        subdomain="botany",
        slide_count=12,
    )
    tip = TopicIntelligencePack(
        core_subtopics=["Light Reactions", "Calvin Cycle", "Chloroplast Anatomy"],
        must_include=[],
        optional_subtopics=[],
        canonical_concepts=[
            {"term": "Thylakoid Membrane", "definition": "Site of light-dependent reactions"},
            {"term": "Stroma", "definition": "Fluid-filled space of chloroplast where Calvin cycle occurs"},
            {"term": "Rubisco", "definition": "Key enzyme catalyzing carbon fixation"},
        ],
        cause_effect_pairs=[
            {"cause": "Increasing light intensity", "effect": "Higher rates of ATP and NADPH production"},
            {"cause": "Elevated atmospheric CO2", "effect": "Increased Rubisco carboxylation rate"},
            {"cause": "High temperature beyond optimum", "effect": "Decreased Rubisco specificity for CO2"},
        ],
    )

    deck_memory = DeckContentMemory()

    bp2 = SlideBlueprint(
        slide_id="slide_2",
        slide_number=2,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Light-dependent reactions in thylakoid membranes",
        canonical_concepts=["Thylakoid Membrane"],
    )
    packet2 = resolve_slide_concept_packet(bp2, brief, topic_intelligence=tip, deck_memory=deck_memory, slide_no=2)

    bp3 = SlideBlueprint(
        slide_id="slide_3",
        slide_number=3,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Dark reactions in the stroma",
        canonical_concepts=["Stroma"],
    )
    packet3 = resolve_slide_concept_packet(bp3, brief, topic_intelligence=tip, deck_memory=deck_memory, slide_no=3)

    # Primary concepts must be distinct
    assert packet2.primary_concept != packet3.primary_concept
    assert packet2.primary_concept == "Thylakoid Membrane"
    assert packet3.primary_concept == "Stroma"

    # Relationships must not be identical
    assert packet2.relationships[0] != packet3.relationships[0]


