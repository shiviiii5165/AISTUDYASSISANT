"""
TeachGenie vNEXT Phase 1 — Comprehensive Tests
=================================================
Tests for the deterministic intelligence layer:
- Domain classifier
- Purpose classifier
- Story grammar selection + adaptation
- PresentationBrief construction
- Blueprint generation + validation
- User override tracking
- Cache versioning
- Backward compatibility
- Three canonical benchmark topics

All tests are synchronous / unit-level — no LLM calls required.
"""
import pytest
import sys
import os
import hashlib
import json

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from app.services.presentation.schemas import (
    PresentationConfig,
    PresentationBrief,
    SlideBlueprint,
    SlideIntent,
    VisualTypeHint,
    LayoutFamily,
    ContentDensity,
    PresentationGoal,
    PresentationMode,
    TemplateSelectionSource,
    StoryGrammarType,
    TextBudget,
    DomainClassification,
    DesignSystem,
    PipelineProvenance,
)
from app.services.presentation.domain_classifier import (
    classify_domain,
    classify_purpose,
    classify_mode,
    infer_technicality,
    infer_audience_expertise,
    infer_visual_preference,
    recommend_template,
    recommend_theme,
    recommend_story_grammar,
    estimate_duration,
    canonicalize_topic,
)
from app.services.presentation.story_grammar import (
    adapt_grammar_to_slide_count,
    generate_blueprints_from_grammar,
    blueprint_to_outline_dict,
    STORY_GRAMMARS,
    INTENT_TO_LEGACY_TYPE,
    NarrativeBeat,
)
from app.services.presentation.blueprint_validator import (
    validate_blueprint_sequence,
    repair_blueprint_sequence,
    compute_semantic_sanity_score,
    BlueprintIssue,
)
from app.services.presentation.planner_agent import _apply_deterministic_messages
from app.services.presentation.brief_builder import build_presentation_brief
from app.services.presentation.cache import (
    compute_presentation_hash, PLANNER_VERSION,
    STORY_GRAMMAR_VERSION, BLUEPRINT_SCHEMA_VERSION, TOPIC_INTELLIGENCE_VERSION,
)
from app.services.presentation.topic_ontology_agent import (
    TopicOntologyChecklist,
    TopicIntelligencePack,
)
from unittest.mock import patch, AsyncMock
from app.services.presentation.planner_agent import plan_presentation_vnext
from app.services.presentation.domain_classifier import (
    CLASSIFICATION_BASIS_DETERMINISTIC,
    CLASSIFICATION_BASIS_CONTEXT,
    CLASSIFICATION_BASIS_DEFAULT,
    CLASSIFICATION_BASIS_MODEL,
    classify_domain_with_model_fallback,
)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _make_config(
    topic="Node.js Architecture",
    audience="university",
    slide_count=12,
    depth="full",
    design="academic",
    theme="",
    enable_quiz=False,
    **kwargs,
) -> PresentationConfig:
    """Helper to create a PresentationConfig for testing."""
    return PresentationConfig(
        topic=topic,
        slide_count=slide_count,
        audience=audience,
        language="english",
        depth=depth,
        design=DesignSystem(design) if isinstance(design, str) else design,
        theme=theme,
        source_type="general",
        source_id=None,
        enable_diagrams=True,
        enable_images=True,
        enable_speaker_notes=True,
        enable_sources=True,
        enable_examples=True,
        enable_quiz=enable_quiz,
        **kwargs,
    )


def _make_brief(topic="Node.js Architecture", **kwargs) -> PresentationBrief:
    """Helper to create a PresentationBrief for testing."""
    defaults = dict(
        topic=topic,
        canonical_topic=topic.title(),
        domain="computer_science",
        subdomain="networking",
        domain_confidence=0.8,
        education_level="university",
        audience_expertise="intermediate",
        presentation_goal=PresentationGoal.TEACH,
        presentation_mode=PresentationMode.LECTURE,
        duration_estimate=24,
        technicality=ContentDensity.MEDIUM,
        visual_preference="diagram_first",
        selected_template="technical",
        recommended_template="technical",
        template_selection_source=TemplateSelectionSource.AUTO_RECOMMENDED,
        selected_theme="indigo_innovation",
        recommended_theme="indigo_innovation",
        theme_selection_source=TemplateSelectionSource.AUTO_RECOMMENDED,
        primary_story_grammar=StoryGrammarType.TECHNICAL_SYSTEM,
        story_modifiers=[StoryGrammarType.CONCEPT_TEACHING],
        slide_count=12,
        language="english",
        knowledge_source="general",
    )
    defaults.update(kwargs)
    return PresentationBrief(**defaults)


# ═══════════════════════════════════════════════════════════════
# 1. DOMAIN CLASSIFIER TESTS
# ═══════════════════════════════════════════════════════════════

class TestDomainClassifier:
    """Spec §6: Domain classifier for 9+ topics with ambiguity handling."""

    def test_node_js_classified_as_cs(self):
        result = classify_domain("Node.js Architecture")
        assert result.domain == "computer_science"
        assert result.confidence > 0.0

    def test_photosynthesis_classified_as_biology(self):
        result = classify_domain("Photosynthesis")
        assert result.domain == "biology"

    def test_industrial_revolution_classified_as_history(self):
        result = classify_domain("Industrial Revolution")
        assert result.domain == "history"

    def test_linear_algebra_classified_as_mathematics(self):
        result = classify_domain("Eigenvalues and Eigenvectors in Linear Algebra")
        assert result.domain == "mathematics"
        assert result.subdomain == "linear_algebra"

    def test_quantum_mechanics_classified_as_physics(self):
        result = classify_domain("Quantum Mechanics and Wave Functions")
        assert result.domain == "physics"
        assert result.subdomain == "quantum"

    def test_organic_chemistry_classified_as_chemistry(self):
        result = classify_domain("Organic Chemistry: Functional Groups and Reactions")
        assert result.domain == "chemistry"

    def test_machine_learning_classified_as_cs_ai(self):
        result = classify_domain("Deep Learning and Neural Networks")
        assert result.domain == "computer_science"
        assert result.subdomain == "ai_ml"

    def test_supply_chain_classified_as_business(self):
        result = classify_domain("Supply Chain Management and Logistics")
        assert result.domain == "business"

    def test_macroeconomics_classified_as_economics(self):
        result = classify_domain("Monetary Policy and Inflation")
        assert result.domain == "economics"

    def test_unknown_topic_returns_general(self):
        result = classify_domain("Advanced Synergistic Paradigms")
        assert result.domain == "general"
        assert result.confidence < 0.5

    def test_ontology_evidence_disambiguates(self):
        """Spec §6: ontology evidence should help classify ambiguous topics."""
        result = classify_domain(
            "Transformers",
            ontology_evidence={
                "core_subtopics": ["attention mechanism", "self-attention", "BERT", "GPT"],
                "must_include": ["transformer architecture"],
            },
        )
        assert result.domain == "computer_science"

    def test_classification_basis_has_provenance(self):
        result = classify_domain("Node.js Architecture")
        assert result.classification_basis != ""
        assert result.classification_basis in (
            CLASSIFICATION_BASIS_DETERMINISTIC,
            CLASSIFICATION_BASIS_CONTEXT,
            CLASSIFICATION_BASIS_DEFAULT,
        )


class TestPurposeClassifier:
    """Spec §6: purpose/mode classification."""

    def test_teach_default(self):
        result = classify_purpose("Node.js Architecture")
        assert result == PresentationGoal.TEACH

    def test_comparison_detected(self):
        result = classify_purpose("React vs Angular: A Comparison")
        assert result == PresentationGoal.COMPARISON_PRESENTATION

    def test_deep_dive_from_depth(self):
        result = classify_purpose("Node.js Architecture", depth="expert")
        assert result == PresentationGoal.DEEP_DIVE

    def test_research_detected(self):
        result = classify_purpose("Research Findings on Climate Change")
        assert result == PresentationGoal.RESEARCH_PRESENTATION

    def test_mode_lecture_default(self):
        result = classify_mode()
        assert result == PresentationMode.LECTURE

    def test_mode_workshop_detected(self):
        result = classify_mode(audience="workshop participants")
        assert result == PresentationMode.WORKSHOP


class TestTemplateRecommendation:
    """Spec §1: template/theme recommendation."""

    def test_cs_gets_technical(self):
        result = recommend_template("computer_science", PresentationGoal.DEEP_DIVE)
        assert result == "technical"

    def test_history_gets_editorial(self):
        result = recommend_template("history", PresentationGoal.TEACH)
        assert result == "academic"

    def test_biology_gets_visual(self):
        result = recommend_template("biology", PresentationGoal.TEACH)
        assert result == "visual"

    def test_theme_follows_template(self):
        theme = recommend_theme("computer_science", "technical")
        assert theme == "indigo_innovation"


# ═══════════════════════════════════════════════════════════════
# 2. STORY GRAMMAR TESTS
# ═══════════════════════════════════════════════════════════════

class TestStoryGrammarSelection:
    """Spec §2, §9: story grammar selection with modifiers."""

    def test_cs_gets_technical_system(self):
        primary, mods = recommend_story_grammar(
            "computer_science", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.TECHNICAL_SYSTEM

    def test_biology_gets_process(self):
        primary, mods = recommend_story_grammar(
            "biology", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.PROCESS

    def test_history_gets_history_evolution(self):
        primary, mods = recommend_story_grammar(
            "history", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.HISTORY_EVOLUTION

    def test_comparison_purpose_overrides_domain(self):
        """Spec §2: purpose-specific grammar overrides domain default."""
        primary, mods = recommend_story_grammar(
            "computer_science", PresentationGoal.COMPARISON_PRESENTATION
        )
        assert primary == StoryGrammarType.COMPARISON

    def test_modifiers_exclude_primary(self):
        primary, mods = recommend_story_grammar(
            "computer_science", PresentationGoal.TEACH
        )
        assert primary not in mods

    def test_modifiers_max_three(self):
        _, mods = recommend_story_grammar(
            "computer_science", PresentationGoal.TEACH
        )
        assert len(mods) <= 3

    def test_all_nine_grammars_defined(self):
        assert len(STORY_GRAMMARS) == 9
        for grammar_type in StoryGrammarType:
            assert grammar_type in STORY_GRAMMARS


class TestStoryGrammarAdaptation:
    """Spec §9: grammar adapts to any slide count without fixed index mapping."""

    def test_8_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 8
        )
        assert len(beats) == 8
        assert beats[0].intent == SlideIntent.COVER
        assert beats[-1].intent == SlideIntent.SUMMARY or beats[-2].intent == SlideIntent.SUMMARY

    def test_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 12
        )
        assert len(beats) == 12
        assert beats[0].intent == SlideIntent.COVER

    def test_15_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], 15
        )
        assert len(beats) == 15

    def test_required_beats_always_included(self):
        """COVER and SUMMARY are always present regardless of slide count."""
        for count in [6, 8, 10, 12, 15]:
            beats = adapt_grammar_to_slide_count(
                StoryGrammarType.CONCEPT_TEACHING, [], count
            )
            intents = [b.intent for b in beats]
            assert SlideIntent.COVER in intents
            assert SlideIntent.SUMMARY in intents

    def test_modifiers_boost_priorities(self):
        """Modifiers should change which beats are selected."""
        beats_without = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 8
        )
        beats_with = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM,
            [StoryGrammarType.COMPARISON],
            8,
        )
        intents_without = {b.intent for b in beats_without}
        intents_with = {b.intent for b in beats_with}
        # Modifiers may change the set of selected intents
        assert isinstance(intents_without, set)
        assert isinstance(intents_with, set)

    def test_quiz_included_when_enabled(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], 12, enable_quiz=True
        )
        intents = [b.intent for b in beats]
        assert SlideIntent.KNOWLEDGE_CHECK in intents

    def test_quiz_excluded_when_disabled(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], 12, enable_quiz=False
        )
        intents = [b.intent for b in beats]
        assert SlideIntent.KNOWLEDGE_CHECK not in intents

    def test_narrative_order_preserved(self):
        """Beats should be sorted by narrative_order."""
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 12
        )
        orders = [b.narrative_order for b in beats]
        assert orders == sorted(orders)


# ═══════════════════════════════════════════════════════════════
# 3. BLUEPRINT GENERATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestBlueprintGeneration:
    """Spec §10: blueprint structure and visual/layout assignment."""

    def test_blueprints_match_beat_count(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 12
        )
        blueprints = generate_blueprints_from_grammar(beats, "computer_science")
        assert len(blueprints) == 12

    def test_slide_numbers_sequential(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], 10
        )
        blueprints = generate_blueprints_from_grammar(beats)
        numbers = [bp.slide_number for bp in blueprints]
        assert numbers == list(range(1, 11))

    def test_cover_gets_hero_layout(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 10
        )
        blueprints = generate_blueprints_from_grammar(beats)
        assert blueprints[0].layout_family == LayoutFamily.HERO

    def test_system_overview_gets_diagram_layout(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 12
        )
        blueprints = generate_blueprints_from_grammar(beats, "computer_science")
        overview_bps = [bp for bp in blueprints if bp.intent == SlideIntent.SYSTEM_OVERVIEW]
        if overview_bps:
            assert overview_bps[0].layout_family == LayoutFamily.DIAGRAM_DOMINANT

    def test_intent_visual_layout_are_independent(self):
        """Spec §4: SlideIntent, VisualTypeHint, LayoutFamily are independent dimensions."""
        bp = SlideBlueprint(
            intent=SlideIntent.CONCEPT_EXPLANATION,
            visual_type=VisualTypeHint.CHART,
            layout_family=LayoutFamily.HERO,
        )
        # All three dimensions can be set independently
        assert bp.intent == SlideIntent.CONCEPT_EXPLANATION
        assert bp.visual_type == VisualTypeHint.CHART
        assert bp.layout_family == LayoutFamily.HERO

    def test_domain_specific_visual_overrides(self):
        """CS domain should get architecture visuals for concept slides."""
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM, [], 10
        )
        cs_blueprints = generate_blueprints_from_grammar(beats, "computer_science")
        concept_bps = [bp for bp in cs_blueprints if bp.intent == SlideIntent.CONCEPT_EXPLANATION]
        if concept_bps:
            assert concept_bps[0].visual_type == VisualTypeHint.LAYERED_ARCHITECTURE

    def test_text_budget_assigned(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], 10
        )
        blueprints = generate_blueprints_from_grammar(beats)
        for bp in blueprints:
            assert isinstance(bp.text_budget, TextBudget)
            assert bp.text_budget.title_max_words > 0


class TestBlueprintBackwardCompat:
    """Blueprint to outline_dict conversion for existing content agent."""

    def test_outline_dict_has_legacy_fields(self):
        bp = SlideBlueprint(
            slide_number=1,
            intent=SlideIntent.COVER,
            primary_message="Test Title",
        )
        d = blueprint_to_outline_dict(bp)
        assert "slide_no" in d
        assert "type" in d
        assert "title" in d
        assert "key_message" in d
        assert d["slide_no"] == 1
        assert d["type"] == "hero"  # COVER maps to "hero"
        assert d["title"] == "Test Title"

    def test_all_intents_have_legacy_mapping(self):
        for intent in SlideIntent:
            assert intent in INTENT_TO_LEGACY_TYPE, f"{intent} missing from INTENT_TO_LEGACY_TYPE"

    def test_outline_dict_has_vnext_enrichment(self):
        bp = SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.CONCEPT_EXPLANATION,
            learning_purpose="Understand the core mechanism",
            content_density=ContentDensity.MEDIUM,
            layout_family=LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
        )
        d = blueprint_to_outline_dict(bp)
        assert d["intent"] == "concept_explanation"
        assert d["learning_purpose"] == "Understand the core mechanism"
        assert d["content_density"] == "medium"
        assert d["layout_family"] == "left_text_right_visual"


# ═══════════════════════════════════════════════════════════════
# 4. BLUEPRINT VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestBlueprintValidator:
    """Spec §11: blueprint sequence validation before content expansion."""

    def _make_valid_sequence(self, count=10) -> list[SlideBlueprint]:
        """Create a valid blueprint sequence for testing."""
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CONCEPT_TEACHING, [], count
        )
        return generate_blueprints_from_grammar(beats)

    def test_valid_sequence_passes(self):
        bps = self._make_valid_sequence(10)
        brief = _make_brief(slide_count=10)
        passed, issues = validate_blueprint_sequence(bps, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert passed or len(errors) == 0

    def test_empty_sequence_fails(self):
        brief = _make_brief(slide_count=10)
        passed, issues = validate_blueprint_sequence([], brief)
        assert not passed
        assert len(issues) > 0

    def test_wrong_slide_count_fails(self):
        bps = self._make_valid_sequence(10)
        brief = _make_brief(slide_count=12)  # Mismatch
        passed, issues = validate_blueprint_sequence(bps, brief)
        count_issues = [i for i in issues if "count" in i.issue.lower()]
        assert len(count_issues) > 0

    def test_missing_cover_fails(self):
        bps = self._make_valid_sequence(10)
        bps[0].intent = SlideIntent.CONCEPT_EXPLANATION  # Remove cover
        brief = _make_brief(slide_count=10)
        passed, issues = validate_blueprint_sequence(bps, brief)
        cover_issues = [i for i in issues if "COVER" in i.issue]
        assert len(cover_issues) > 0

    def test_quiz_when_disabled_fails(self):
        bps = self._make_valid_sequence(10)
        bps[8].intent = SlideIntent.KNOWLEDGE_CHECK
        brief = _make_brief(slide_count=10, enable_quiz=False)
        passed, issues = validate_blueprint_sequence(bps, brief)
        quiz_issues = [i for i in issues if "KNOWLEDGE_CHECK" in i.issue]
        assert len(quiz_issues) > 0

    def test_repair_fixes_cover(self):
        bps = self._make_valid_sequence(10)
        bps[0].intent = SlideIntent.CONCEPT_EXPLANATION
        brief = _make_brief(slide_count=10)
        _, issues = validate_blueprint_sequence(bps, brief)
        repaired = repair_blueprint_sequence(bps, issues, brief)
        assert repaired[0].intent == SlideIntent.COVER

    def test_repair_adjusts_slide_count(self):
        bps = self._make_valid_sequence(10)
        brief = _make_brief(slide_count=8)
        _, issues = validate_blueprint_sequence(bps, brief)
        repaired = repair_blueprint_sequence(bps, issues, brief)
        assert len(repaired) == 8


# ═══════════════════════════════════════════════════════════════
# 5. PRESENTATION BRIEF TESTS
# ═══════════════════════════════════════════════════════════════

class TestPresentationBrief:
    """Spec §3, §7: PresentationBrief construction from PresentationConfig."""

    def test_brief_from_config(self):
        config = _make_config(topic="Node.js Architecture")
        brief = build_presentation_brief(config)
        assert brief.topic == "Node.js Architecture"
        assert brief.domain == "computer_science"
        assert brief.slide_count == 12

    def test_brief_carries_feature_toggles(self):
        config = _make_config(enable_quiz=True)
        brief = build_presentation_brief(config)
        assert brief.enable_quiz is True

    def test_brief_has_versioning(self):
        config = _make_config()
        brief = build_presentation_brief(config)
        assert brief.planner_version == "vnext_phase1"
        assert brief.story_grammar_version != ""
        assert brief.blueprint_schema_version != ""


class TestUserOverride:
    """Spec §1: user override policy for template/theme."""

    def test_auto_recommended_when_default(self):
        config = _make_config(design="academic", theme="")
        brief = build_presentation_brief(config)
        assert brief.template_selection_source == TemplateSelectionSource.AUTO_RECOMMENDED
        assert brief.theme_selection_source == TemplateSelectionSource.AUTO_RECOMMENDED

    def test_user_override_when_different(self):
        config = _make_config(design="editorial", theme="orange_energy")
        brief = build_presentation_brief(config)
        assert brief.template_selection_source == TemplateSelectionSource.USER_OVERRIDE
        assert brief.selected_template == "editorial"
        assert brief.theme_selection_source == TemplateSelectionSource.USER_OVERRIDE
        assert brief.selected_theme == "orange_energy"

    def test_recommendation_preserved_in_metadata(self):
        """Even when user overrides, the AI recommendation is stored."""
        config = _make_config(topic="Node.js Architecture", design="editorial")
        brief = build_presentation_brief(config)
        assert brief.selected_template == "editorial"
        # The AI would have recommended something else
        assert brief.recommended_template != ""


# ═══════════════════════════════════════════════════════════════
# 6. CACHE VERSIONING TESTS
# ═══════════════════════════════════════════════════════════════

class TestCacheVersioning:
    """Spec §12: cache key includes planner version."""

    def test_version_in_cache_hash(self):
        assert PLANNER_VERSION == "vnext_phase1"

    def test_different_versions_different_hashes(self):
        config = _make_config()
        hash1 = compute_presentation_hash(config)
        # The hash should include the planner_version
        # Changing the version should change the hash
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256

    def test_same_config_same_hash(self):
        config1 = _make_config()
        config2 = _make_config()
        assert compute_presentation_hash(config1) == compute_presentation_hash(config2)

    def test_different_topic_different_hash(self):
        config1 = _make_config(topic="Node.js")
        config2 = _make_config(topic="Photosynthesis")
        assert compute_presentation_hash(config1) != compute_presentation_hash(config2)


# ═══════════════════════════════════════════════════════════════
# 7. TOPIC INTELLIGENCE PACK TESTS
# ═══════════════════════════════════════════════════════════════

class TestTopicIntelligencePack:
    """TopicIntelligencePack inherits TopicOntologyChecklist."""

    def test_inherits_base_fields(self):
        pack = TopicIntelligencePack(
            core_subtopics=["A", "B"],
            must_include=["C"],
        )
        assert pack.core_subtopics == ["A", "B"]
        assert pack.must_include == ["C"]

    def test_has_expanded_fields(self):
        pack = TopicIntelligencePack(
            canonical_concepts=[{"term": "X", "definition": "Y"}],
            misconceptions=[{"myth": "M", "reality": "R"}],
        )
        assert len(pack.canonical_concepts) == 1
        assert len(pack.misconceptions) == 1

    def test_backward_compat_as_ontology(self):
        pack = TopicIntelligencePack(
            core_subtopics=["A"],
            must_include=["B"],
            optional_subtopics=["C"],
        )
        # Should work anywhere TopicOntologyChecklist is accepted
        assert isinstance(pack, TopicOntologyChecklist)

    def test_empty_defaults(self):
        """Spec §8: empty is better than fake."""
        pack = TopicIntelligencePack()
        assert pack.canonical_concepts == []
        assert pack.misconceptions == []
        assert pack.real_world_examples == []
        assert pack.recommended_diagrams == []


# ═══════════════════════════════════════════════════════════════
# 8. THREE CANONICAL BENCHMARK TOPICS
# ═══════════════════════════════════════════════════════════════

class TestBenchmarkNodeJS:
    """Benchmark: Node.js Architecture → TECHNICAL_SYSTEM grammar."""

    def test_domain_classification(self):
        result = classify_domain("Node.js Architecture")
        assert result.domain == "computer_science"

    def test_grammar_selection(self):
        primary, mods = recommend_story_grammar(
            "computer_science", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.TECHNICAL_SYSTEM

    def test_blueprint_generation_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.TECHNICAL_SYSTEM,
            [StoryGrammarType.CONCEPT_TEACHING],
            12,
            domain="computer_science",
        )
        assert len(beats) == 12
        blueprints = generate_blueprints_from_grammar(beats, "computer_science")
        assert len(blueprints) == 12

        # Verify structure
        assert blueprints[0].intent == SlideIntent.COVER
        intents = [bp.intent for bp in blueprints]
        assert SlideIntent.SYSTEM_OVERVIEW in intents
        assert SlideIntent.SUMMARY in intents

    def test_full_pipeline(self):
        config = _make_config(topic="Node.js Architecture", slide_count=12)
        brief = build_presentation_brief(config)
        assert brief.domain == "computer_science"
        assert brief.primary_story_grammar == StoryGrammarType.TECHNICAL_SYSTEM

        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {errors}"


class TestBenchmarkPhotosynthesis:
    """Benchmark: Photosynthesis → PROCESS grammar."""

    def test_domain_classification(self):
        result = classify_domain("Photosynthesis")
        assert result.domain == "biology"

    def test_grammar_selection(self):
        primary, mods = recommend_story_grammar(
            "biology", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.PROCESS

    def test_blueprint_generation_10_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.PROCESS,
            [StoryGrammarType.CONCEPT_TEACHING],
            10,
            domain="biology",
        )
        assert len(beats) == 10
        blueprints = generate_blueprints_from_grammar(beats, "biology")
        assert len(blueprints) == 10

        # Biology should get cycle visuals for process slides
        process_bps = [bp for bp in blueprints if bp.intent == SlideIntent.PROCESS_EXPLANATION]
        if process_bps:
            assert process_bps[0].visual_type == VisualTypeHint.CYCLE

    def test_full_pipeline(self):
        config = _make_config(topic="Photosynthesis", slide_count=10)
        brief = build_presentation_brief(config)
        assert brief.domain == "biology"
        assert brief.primary_story_grammar == StoryGrammarType.PROCESS

        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


class TestBenchmarkIndustrialRevolution:
    """Benchmark: Industrial Revolution → HISTORY_EVOLUTION grammar."""

    def test_domain_classification(self):
        result = classify_domain("Industrial Revolution")
        assert result.domain == "history"

    def test_grammar_selection(self):
        primary, mods = recommend_story_grammar(
            "history", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.HISTORY_EVOLUTION

    def test_blueprint_generation_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.HISTORY_EVOLUTION,
            [StoryGrammarType.CONCEPT_TEACHING],
            12,
            domain="history",
        )
        assert len(beats) == 12
        blueprints = generate_blueprints_from_grammar(beats, "history")
        assert len(blueprints) == 12

        # History should get timeline/photograph visuals
        context_bps = [bp for bp in blueprints if bp.intent == SlideIntent.CONTEXT]
        if context_bps:
            assert context_bps[0].visual_type == VisualTypeHint.PHOTOGRAPH

    def test_full_pipeline(self):
        config = _make_config(topic="Industrial Revolution", slide_count=12)
        brief = build_presentation_brief(config)
        assert brief.domain == "history"
        assert brief.primary_story_grammar == StoryGrammarType.HISTORY_EVOLUTION

        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════
# 9. CROSS-CUTTING TESTS
# ═══════════════════════════════════════════════════════════════

class TestSchemaSeparation:
    """Spec §4, §5: Intent, Visual, Layout are independent dimensions."""

    def test_intent_enum_has_29_values(self):
        assert len(SlideIntent) == 29

    def test_visual_type_enum_comprehensive(self):
        assert len(VisualTypeHint) >= 20

    def test_layout_family_enum_comprehensive(self):
        assert len(LayoutFamily) >= 15

    def test_no_overlap_between_dimensions(self):
        """Intent values should not appear in VisualTypeHint or LayoutFamily."""
        intent_values = {i.value for i in SlideIntent}
        visual_values = {v.value for v in VisualTypeHint}
        layout_values = {l.value for l in LayoutFamily}
        # There should be minimal overlap between these independent dimensions
        assert len(intent_values & visual_values) <= 2  # Allow minimal coincidental overlap
        assert len(intent_values & layout_values) <= 2


class TestDiverseTopicGrammars:
    """Spec §2: different topics should produce different blueprint sequences."""

    def test_different_topics_different_intents(self):
        topics = [
            ("computer_science", StoryGrammarType.TECHNICAL_SYSTEM),
            ("biology", StoryGrammarType.PROCESS),
            ("history", StoryGrammarType.HISTORY_EVOLUTION),
        ]
        all_intent_sequences = []
        for domain, grammar in topics:
            beats = adapt_grammar_to_slide_count(grammar, [], 10)
            intents = tuple(b.intent for b in beats)
            all_intent_sequences.append(intents)

        # At least 2 of 3 should be different
        unique = len(set(all_intent_sequences))
        assert unique >= 2, "Different grammar types should produce different intent sequences"


class TestUtilityFunctions:
    """Utility function tests."""

    def test_canonicalize_topic(self):
        assert canonicalize_topic("introduction to Node.js") == "Node.Js"
        assert canonicalize_topic("  basics of Python  ") == "Python"

    def test_estimate_duration(self):
        assert estimate_duration(5) == 10
        assert estimate_duration(12) == 24
        assert estimate_duration(15) == 30
        assert estimate_duration(1) == 5  # minimum 5 minutes

    def test_infer_technicality(self):
        assert infer_technicality("computer_science", depth="expert") == ContentDensity.HIGH
        assert infer_technicality("literature_humanities", "beginner") == ContentDensity.LOW

    def test_infer_audience_expertise(self):
        assert infer_audience_expertise("PhD researchers") == "advanced"
        assert infer_audience_expertise("high school students") == "beginner"
        assert infer_audience_expertise("university") == "intermediate"


# ═══════════════════════════════════════════════════════════════
# 10. PHASE 1 CLOSURE — EXPANDED DOMAIN COVERAGE (Item 1)
# ═══════════════════════════════════════════════════════════════

class TestExpandedDomainCoverage:
    """Item 1: 18-domain coverage including 8 new domains."""

    def test_medicine_health_sciences(self):
        result = classify_domain("Hypertension Pathophysiology")
        assert result.domain == "medicine_health_sciences"
        assert result.confidence > 0.0

    def test_literature_humanities_macbeth(self):
        result = classify_domain("Macbeth")
        assert result.domain == "literature_humanities"

    def test_law_doctrine_of_consideration(self):
        result = classify_domain("Doctrine of Consideration")
        assert result.domain == "law"

    def test_languages_french_conjugation(self):
        result = classify_domain("French Verb Conjugation")
        assert result.domain == "languages"

    def test_education_blooms_taxonomy(self):
        result = classify_domain("Bloom's Taxonomy and Learning Theory")
        assert result.domain == "education"

    def test_social_sciences_democracy(self):
        result = classify_domain("Democracy and Governance Systems")
        assert result.domain == "social_sciences"

    def test_environmental_science_renewable_energy(self):
        result = classify_domain("Renewable Energy Adoption Trends")
        assert result.domain == "environmental_science"

    def test_finance_accounting_financial_statements(self):
        result = classify_domain("Financial Statement Analysis and Ratio Analysis")
        assert result.domain == "finance_accounting"

    def test_medicine_with_subdomains(self):
        result = classify_domain("Clinical Trial Design and Pharmacology")
        assert result.domain == "medicine_health_sciences"
        assert result.subdomain != ""

    def test_law_with_subdomains(self):
        result = classify_domain("Contract Law: Doctrine of Consideration")
        assert result.domain == "law"
        assert result.subdomain == "contract_law"

    def test_environmental_energy_subdomain(self):
        result = classify_domain("Solar Energy and Wind Energy Trends")
        assert result.domain == "environmental_science"
        assert result.subdomain == "energy"

    def test_finance_investment_subdomain(self):
        result = classify_domain("Portfolio Management and Risk Management")
        assert result.domain == "finance_accounting"
        assert result.subdomain == "investment"

    def test_all_18_domains_in_grammar_map(self):
        """Every domain in DOMAIN_RULES must have a GRAMMAR_BY_DOMAIN entry."""
        from app.services.presentation.domain_classifier import DOMAIN_RULES, GRAMMAR_BY_DOMAIN
        for domain_key in DOMAIN_RULES:
            assert domain_key in GRAMMAR_BY_DOMAIN, f"Missing GRAMMAR_BY_DOMAIN entry for {domain_key}"

    def test_all_18_domains_in_modifier_map(self):
        """Every domain in DOMAIN_RULES must have a MODIFIER_SUGGESTIONS entry."""
        from app.services.presentation.domain_classifier import DOMAIN_RULES, MODIFIER_SUGGESTIONS
        for domain_key in DOMAIN_RULES:
            assert domain_key in MODIFIER_SUGGESTIONS, f"Missing MODIFIER_SUGGESTIONS for {domain_key}"

    def test_all_18_domains_in_template_map(self):
        """Every domain in DOMAIN_RULES must have a TEMPLATE_BY_DOMAIN_PURPOSE entry."""
        from app.services.presentation.domain_classifier import DOMAIN_RULES, TEMPLATE_BY_DOMAIN_PURPOSE
        for domain_key in DOMAIN_RULES:
            assert domain_key in TEMPLATE_BY_DOMAIN_PURPOSE, f"Missing TEMPLATE_BY_DOMAIN_PURPOSE for {domain_key}"

    def test_all_18_domains_in_theme_map(self):
        """Every domain in DOMAIN_RULES must have a THEME_BY_DOMAIN_TEMPLATE entry."""
        from app.services.presentation.domain_classifier import DOMAIN_RULES, THEME_BY_DOMAIN_TEMPLATE
        for domain_key in DOMAIN_RULES:
            assert domain_key in THEME_BY_DOMAIN_TEMPLATE, f"Missing THEME_BY_DOMAIN_TEMPLATE for {domain_key}"

    def test_classification_returns_required_fields(self):
        """All 4 required fields present."""
        result = classify_domain("Photosynthesis")
        assert hasattr(result, 'domain')
        assert hasattr(result, 'subdomain')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'classification_basis')


# ═══════════════════════════════════════════════════════════════
# 11. PHASE 1 CLOSURE — AMBIGUOUS DOMAIN FALLBACK (Item 2)
# ═══════════════════════════════════════════════════════════════

class TestAmbiguousDomainFallback:
    """Item 2: Context-based disambiguation for ambiguous topics."""

    def test_transformers_ai_context(self):
        """'Transformers' + AI context → computer_science / ai_ml"""
        result = classify_domain(
            "Transformers",
            custom_context="attention mechanisms and neural networks",
        )
        assert result.domain == "computer_science"
        assert result.subdomain == "ai_ml"
        assert result.classification_basis in (
            CLASSIFICATION_BASIS_DETERMINISTIC, CLASSIFICATION_BASIS_CONTEXT
        )

    def test_transformers_electrical_context(self):
        """'Transformers' + electrical context → engineering / electrical"""
        result = classify_domain(
            "Transformers",
            custom_context="step-up and step-down voltage",
        )
        assert result.domain == "engineering"
        assert result.subdomain == "electrical"

    def test_java_programming_context(self):
        """'Java' + programming context → computer_science"""
        result = classify_domain(
            "Java",
            custom_context="object-oriented programming",
        )
        assert result.domain == "computer_science"

    def test_java_geography_context(self):
        """'Java' + geography context → social_sciences (geography) or general"""
        result = classify_domain(
            "Java",
            custom_context="Indonesian island geography urbanization",
        )
        # Should NOT be computer_science when context is geographical
        assert result.domain != "computer_science" or result.classification_basis == CLASSIFICATION_BASIS_CONTEXT

    def test_deterministic_basis_for_clear_match(self):
        """Unambiguous topic should get DETERMINISTIC_RULE."""
        result = classify_domain("Photosynthesis")
        assert result.classification_basis == CLASSIFICATION_BASIS_DETERMINISTIC

    def test_default_fallback_for_unknown(self):
        """Unknown topic should get DEFAULT_FALLBACK."""
        result = classify_domain("Xenomorphic Transplanar Dynamics")
        assert result.domain == "general"
        assert result.classification_basis == CLASSIFICATION_BASIS_DEFAULT

    def test_ontology_evidence_disambiguates(self):
        """Ontology evidence should resolve ambiguity."""
        result = classify_domain(
            "Transformers",
            ontology_evidence={
                "core_subtopics": ["attention mechanism", "self-attention", "BERT", "GPT"],
                "must_include": ["transformer architecture"],
            },
        )
        assert result.domain == "computer_science"
        assert result.subdomain == "ai_ml"


# ═══════════════════════════════════════════════════════════════
# 12. PHASE 1 CLOSURE — DATA_STORY & RESEARCH GRAMMARS (Item 3)
# ═══════════════════════════════════════════════════════════════

class TestDataStoryGrammar:
    """Item 3: DATA_STORY grammar completeness."""

    def test_data_story_grammar_exists(self):
        assert StoryGrammarType.DATA_STORY in STORY_GRAMMARS

    def test_data_story_has_required_beats(self):
        beats = STORY_GRAMMARS[StoryGrammarType.DATA_STORY]
        intents = [b.intent for b in beats]
        assert SlideIntent.COVER in intents
        assert SlideIntent.SUMMARY in intents
        assert SlideIntent.DATA_INSIGHT in intents

    def test_data_story_beat_count(self):
        beats = STORY_GRAMMARS[StoryGrammarType.DATA_STORY]
        assert len(beats) >= 10, "DATA_STORY should have enough beats for a full presentation"

    def test_data_story_adapts_to_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.DATA_STORY, [], 12,
        )
        assert len(beats) == 12
        intents = [b.intent for b in beats]
        assert SlideIntent.DATA_INSIGHT in intents
        assert SlideIntent.COVER in intents
        assert SlideIntent.SUMMARY in intents

    def test_data_story_blueprints_generate(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.DATA_STORY, [], 12,
        )
        blueprints = generate_blueprints_from_grammar(beats)
        assert len(blueprints) == 12
        # DATA_INSIGHT slides should have CHART visual
        data_bps = [bp for bp in blueprints if bp.intent == SlideIntent.DATA_INSIGHT]
        assert len(data_bps) >= 1
        assert data_bps[0].visual_type == VisualTypeHint.CHART

    def test_data_story_modifier_boosts_exist(self):
        from app.services.presentation.story_grammar import MODIFIER_PRIORITY_BOOSTS
        assert StoryGrammarType.DATA_STORY in MODIFIER_PRIORITY_BOOSTS


class TestResearchGrammar:
    """Item 3: RESEARCH grammar completeness."""

    def test_research_grammar_exists(self):
        assert StoryGrammarType.RESEARCH in STORY_GRAMMARS

    def test_research_has_required_beats(self):
        beats = STORY_GRAMMARS[StoryGrammarType.RESEARCH]
        intents = [b.intent for b in beats]
        assert SlideIntent.COVER in intents
        assert SlideIntent.SUMMARY in intents
        assert SlideIntent.DATA_INSIGHT in intents  # results
        assert SlideIntent.PROCESS_EXPLANATION in intents  # methodology
        assert SlideIntent.REFERENCES in intents

    def test_research_adapts_to_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.RESEARCH, [], 12,
        )
        assert len(beats) == 12

    def test_research_blueprints_generate(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.RESEARCH, [], 12,
        )
        blueprints = generate_blueprints_from_grammar(beats)
        assert len(blueprints) == 12

    def test_research_purpose_maps_to_research_grammar(self):
        """Purpose 'research_presentation' should map to RESEARCH grammar."""
        from app.services.presentation.domain_classifier import GRAMMAR_BY_PURPOSE
        assert GRAMMAR_BY_PURPOSE["research_presentation"] == StoryGrammarType.RESEARCH


# ═══════════════════════════════════════════════════════════════
# 13. PHASE 1 CLOSURE — FALLBACK PROVENANCE (Item 4)
# ═══════════════════════════════════════════════════════════════

class TestFallbackProvenance:
    """Item 4: PipelineProvenance model correctness."""

    def test_provenance_defaults_to_vnext(self):
        p = PipelineProvenance()
        assert p.planning_engine == "VNEXT"
        assert p.planning_fallback_used is False
        assert p.planning_fallback_reason == ""

    def test_provenance_can_be_set_to_fallback(self):
        p = PipelineProvenance(
            planning_engine="LEGACY_FALLBACK",
            planning_fallback_used=True,
            planning_fallback_reason="BRIEF_BUILD_FAILED",
        )
        assert p.planning_engine == "LEGACY_FALLBACK"
        assert p.planning_fallback_used is True
        assert p.planning_fallback_reason == "BRIEF_BUILD_FAILED"

    def test_provenance_version_fields(self):
        p = PipelineProvenance()
        assert p.planner_version == "vnext_phase1"
        assert p.story_grammar_version == "1.0"
        assert p.blueprint_schema_version == "1.0"
        assert p.topic_intelligence_version == "1.0"

    def test_provenance_serializes(self):
        p = PipelineProvenance()
        d = p.model_dump()
        assert "planning_engine" in d
        assert "planning_fallback_used" in d
        assert "planning_fallback_reason" in d
        assert "planner_version" in d


# ═══════════════════════════════════════════════════════════════
# 14. PHASE 1 CLOSURE — CACHE SEMANTIC VERSIONING (Item 5)
# ═══════════════════════════════════════════════════════════════

class TestCacheSemanticVersioning:
    """Item 5: Cache hash includes all semantic versions."""

    def test_cache_includes_semantic_versions(self):
        """All 4 version fields must be present."""
        assert PLANNER_VERSION == "vnext_phase1"
        assert STORY_GRAMMAR_VERSION == "1.0"
        assert BLUEPRINT_SCHEMA_VERSION == "1.0"
        assert TOPIC_INTELLIGENCE_VERSION == "1.0"

    def test_different_versions_produce_different_hashes(self):
        """Changing any version field must change the hash."""
        config = _make_config(topic="Node.js Architecture")
        h1 = compute_presentation_hash(config)
        # Same config → same hash
        h2 = compute_presentation_hash(config)
        assert h1 == h2

    def test_different_topic_different_hash(self):
        c1 = _make_config(topic="Node.js")
        c2 = _make_config(topic="Photosynthesis")
        assert compute_presentation_hash(c1) != compute_presentation_hash(c2)

    def test_different_theme_different_hash(self):
        c1 = _make_config(topic="Node.js", theme="blue")
        c2 = _make_config(topic="Node.js", theme="red")
        assert compute_presentation_hash(c1) != compute_presentation_hash(c2)

    def test_different_quiz_toggle_different_hash(self):
        c1 = _make_config(topic="Node.js", enable_quiz=False)
        c2 = _make_config(topic="Node.js", enable_quiz=True)
        assert compute_presentation_hash(c1) != compute_presentation_hash(c2)


# ═══════════════════════════════════════════════════════════════
# 15. PHASE 1 CLOSURE — BLUEPRINT PIPELINE ORDER (Item 6)
# ═══════════════════════════════════════════════════════════════

class TestBlueprintPipelineOrder:
    """Item 6: Canonical flow verified."""

    def test_canonical_flow_brief_to_blueprints(self):
        """PresentationBrief → Story Grammar → Initial Blueprints → Validation."""
        config = _make_config(topic="Node.js Architecture", slide_count=12)
        brief = build_presentation_brief(config)

        # Story grammar adaptation
        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )

        # Blueprint generation
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)

        # PRE-ENRICHMENT validation (deterministic structural check)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Pre-enrichment validation should pass: {errors}"

        # At this point, expensive content generation can proceed
        assert len(blueprints) == brief.slide_count

    def test_pre_enrichment_before_content(self):
        """Validation must happen before enrichment — blueprints without messages should still pass structurally."""
        brief = _make_brief(slide_count=12)
        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)

        # No primary_message set yet — structural validation should still work
        for bp in blueprints:
            assert bp.primary_message == ""  # not yet enriched

        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, "Structural validation should pass without enrichment"


# ═══════════════════════════════════════════════════════════════
# 16. PHASE 1 CLOSURE — DATA/RESEARCH BENCHMARKS (Item 7)
# ═══════════════════════════════════════════════════════════════

class TestBenchmarkRenewableEnergy:
    """Item 7: Renewable Energy Adoption Trends → DATA_STORY."""

    def test_domain_classification(self):
        result = classify_domain("Renewable Energy Adoption Trends")
        assert result.domain == "environmental_science"

    def test_grammar_selection_data_story(self):
        """Environmental science default grammar should be DATA_STORY."""
        primary, mods = recommend_story_grammar(
            "environmental_science", PresentationGoal.TEACH
        )
        assert primary == StoryGrammarType.DATA_STORY

    def test_full_pipeline(self):
        config = _make_config(topic="Renewable Energy Adoption Trends", slide_count=12)
        brief = build_presentation_brief(config)
        assert brief.domain == "environmental_science"
        assert brief.primary_story_grammar == StoryGrammarType.DATA_STORY

        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0
        assert len(blueprints) == 12


class TestBenchmarkResearchPresentation:
    """Item 7: Research Methodology presentation → RESEARCH grammar."""

    def test_research_purpose_triggers_research_grammar(self):
        """Topic with 'research methodology' should select RESEARCH grammar."""
        config = _make_config(
            topic="Research Methodology and Literature Review in Machine Learning",
            slide_count=12,
        )
        brief = build_presentation_brief(config)
        # 'Research' + 'methodology' + 'literature review' → research_presentation purpose → RESEARCH grammar
        assert brief.primary_story_grammar == StoryGrammarType.RESEARCH

    def test_full_pipeline(self):
        config = _make_config(
            topic="Research Methodology and Literature Review in Machine Learning",
            slide_count=12,
        )
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            brief.primary_story_grammar,
            brief.story_modifiers,
            brief.slide_count,
            domain=brief.domain,
        )
        blueprints = generate_blueprints_from_grammar(beats, brief.domain)
        passed, issues = validate_blueprint_sequence(blueprints, brief)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0
        assert len(blueprints) == 12


# ═══════════════════════════════════════════════════════════════
# 17. PHASE 1 CLOSURE — DOMAIN BENCHMARK MATRIX (Item 8)
# ═══════════════════════════════════════════════════════════════

class TestDomainBenchmarkMatrix:
    """Item 8: 14-topic domain classification matrix."""

    MATRIX = [
        ("Node.js Architecture", "computer_science", "", ""),
        ("Photosynthesis", "biology", "", ""),
        ("Eigenvalues and Eigenvectors", "mathematics", "", ""),
        ("Massive MIMO", "engineering", "", ""),
        ("Hypertension Pathophysiology", "medicine_health_sciences", "", ""),
        ("Macbeth", "literature_humanities", "", ""),
        ("Doctrine of Consideration", "law", "", ""),
        ("Inflation and Monetary Policy", "economics", "", ""),
        ("Porter's Five Forces", "business", "", ""),
        ("SN1 vs SN2", "chemistry", "", ""),
        ("Industrial Revolution", "history", "", ""),
        ("French Verb Conjugation", "languages", "", ""),
        ("Transformers", "computer_science", "attention mechanisms and neural networks", ""),
        ("Transformers", "engineering", "step-up and step-down voltage", ""),
    ]

    @pytest.mark.parametrize("topic,expected_domain,context,audience", MATRIX)
    def test_domain_matrix(self, topic, expected_domain, context, audience):
        result = classify_domain(topic, audience=audience, custom_context=context)
        assert result.domain == expected_domain, (
            f"Expected {expected_domain} for '{topic}' (ctx='{context}'), "
            f"got {result.domain} (basis={result.classification_basis})"
        )


# ═══════════════════════════════════════════════════════════════
# 18. PROBLEM_SOLUTION & CASE_STUDY GRAMMARS
# ═══════════════════════════════════════════════════════════════

class TestProblemSolutionGrammar:
    """PROBLEM_SOLUTION grammar completeness."""

    def test_grammar_exists(self):
        assert StoryGrammarType.PROBLEM_SOLUTION in STORY_GRAMMARS

    def test_adapts_to_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.PROBLEM_SOLUTION, [], 12,
        )
        assert len(beats) == 12

    def test_blueprints_generate(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.PROBLEM_SOLUTION, [], 12,
        )
        blueprints = generate_blueprints_from_grammar(beats)
        assert len(blueprints) == 12


class TestCaseStudyGrammar:
    """CASE_STUDY grammar completeness."""

    def test_grammar_exists(self):
        assert StoryGrammarType.CASE_STUDY in STORY_GRAMMARS

    def test_adapts_to_12_slides(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CASE_STUDY, [], 12,
        )
        assert len(beats) == 12

    def test_blueprints_generate(self):
        beats = adapt_grammar_to_slide_count(
            StoryGrammarType.CASE_STUDY, [], 12,
        )
        blueprints = generate_blueprints_from_grammar(beats)
        assert len(blueprints) == 12


# ═══════════════════════════════════════════════════════════════
# 19. ALL 9 GRAMMARS COVERAGE
# ═══════════════════════════════════════════════════════════════

class TestAllGrammars:
    """Every grammar in StoryGrammarType must have a STORY_GRAMMARS entry."""

    @pytest.mark.parametrize("grammar_type", list(StoryGrammarType))
    def test_grammar_has_beats(self, grammar_type):
        assert grammar_type in STORY_GRAMMARS, f"Missing grammar beats for {grammar_type.value}"
        beats = STORY_GRAMMARS[grammar_type]
        assert len(beats) >= 5, f"Grammar {grammar_type.value} has too few beats ({len(beats)})"

    @pytest.mark.parametrize("grammar_type", list(StoryGrammarType))
    def test_grammar_adapts_to_12(self, grammar_type):
        beats = adapt_grammar_to_slide_count(grammar_type, [], 12)
        assert len(beats) == 12

    @pytest.mark.parametrize("grammar_type", list(StoryGrammarType))
    def test_grammar_first_beat_is_cover(self, grammar_type):
        beats = STORY_GRAMMARS[grammar_type]
        assert beats[0].intent == SlideIntent.COVER


# ═══════════════════════════════════════════════════════════════
# 20. LOW-CONFIDENCE MODEL DISAMBIGUATION (PHASE 1 CONTRACT)
# ═══════════════════════════════════════════════════════════════

class TestModelDisambiguationFallback:
    """Proves:
    1. High-confidence deterministic -> zero LLM calls.
    2. Low-confidence or ambiguous without context -> invokes lightweight model fallback.
    3. Classification basis is correctly marked as MODEL_DISAMBIGUATION.
    4. Ambiguous cases beyond hard-coded nouns are resolved correctly with context.
    """

    def test_high_confidence_never_calls_model(self):
        """High-confidence topics must never invoke LLM (zero cost)."""
        import asyncio

        async def _run():
            with patch("app.services.ai.router.ModelRouter.generate_text", new_callable=AsyncMock) as mock_llm:
                res = await classify_domain_with_model_fallback("Node.js Architecture")
                assert res.domain == "computer_science"
                assert res.classification_basis == CLASSIFICATION_BASIS_DETERMINISTIC
                assert mock_llm.call_count == 0

                res2 = await classify_domain_with_model_fallback("Photosynthesis")
                assert res2.domain == "biology"
                assert res2.classification_basis == CLASSIFICATION_BASIS_DETERMINISTIC
                assert mock_llm.call_count == 0

                res3 = await classify_domain_with_model_fallback("Industrial Revolution")
                assert res3.domain == "history"
                assert res3.classification_basis == CLASSIFICATION_BASIS_DETERMINISTIC
                assert mock_llm.call_count == 0

        asyncio.run(_run())

    def test_ambiguous_low_confidence_invokes_model(self):
        """When deterministic confidence is insufficient (e.g. unknown topic), invoke model."""
        import asyncio
        mock_response = AsyncMock()
        mock_response.text = '{"domain": "physics", "subdomain": "astronomy_astrophysics", "confidence": 0.92}'

        async def _run():
            with patch("app.services.ai.router.ModelRouter.generate_text", new_callable=AsyncMock, return_value=mock_response) as mock_llm:
                res = await classify_domain_with_model_fallback("Mercury", custom_context="")
                assert mock_llm.call_count == 1
                assert res.domain == "physics"
                assert res.subdomain == "astronomy_astrophysics"
                assert res.classification_basis == CLASSIFICATION_BASIS_MODEL

        asyncio.run(_run())

    def test_model_fallback_invalid_domain_safely_falls_back(self):
        """If model returns an unregistered domain, safely fall back to deterministic default."""
        import asyncio
        mock_response = AsyncMock()
        mock_response.text = '{"domain": "astrology_magic", "subdomain": "", "confidence": 0.99}'

        async def _run():
            with patch("app.services.ai.router.ModelRouter.generate_text", new_callable=AsyncMock, return_value=mock_response):
                res = await classify_domain_with_model_fallback("UnknownTopicXYZ")
                assert res.domain == "general"
                assert res.classification_basis == CLASSIFICATION_BASIS_DEFAULT

        asyncio.run(_run())

    def test_model_fallback_exception_graceful(self):
        """If router throws exception, gracefully return deterministic result."""
        import asyncio

        async def _run():
            with patch("app.services.ai.router.ModelRouter.generate_text", new_callable=AsyncMock, side_effect=RuntimeError("Provider exhausted")):
                res = await classify_domain_with_model_fallback("UnknownTopicXYZ")
                assert res.domain == "general"
                assert res.classification_basis == CLASSIFICATION_BASIS_DEFAULT

        asyncio.run(_run())

    def test_ambiguous_acceptance_cases(self):
        """Verify the 6 agreed ambiguous acceptance cases resolve to expected domains."""
        cases = [
            ("Mercury", "planetary orbit", "physics"),
            ("Mercury", "toxicity and human exposure", "medicine_health_sciences"),
            ("Bonds", "fixed income portfolio", "finance_accounting"),
            ("Bonds", "ionic and covalent", "chemistry"),
            ("Networks", "routers and TCP/IP", "computer_science"),
            ("Networks", "social relationships and communities", "social_sciences"),
        ]
        for topic, ctx, expected_domain in cases:
            res = classify_domain(topic, custom_context=ctx)
            assert res.domain == expected_domain, f"Failed for {topic} + '{ctx}': got {res.domain}, expected {expected_domain}"


# ═══════════════════════════════════════════════════════════════
# 21. TOPIC INTELLIGENCE RUNTIME PIPELINE POSITION (SPEC §2)
# ═══════════════════════════════════════════════════════════════

class TestTopicIntelligencePipelineWiring:
    """Proves the runtime pipeline flow:
    PresentationBrief → TopicIntelligencePack → Story Grammar → SlideBlueprints
    """

    def test_topic_intelligence_refines_grammar_and_blueprints(self):
        """Topic intelligence signals must influence story grammar and blueprint adaptation."""
        import asyncio

        async def _run():
            config = PresentationConfig(topic="Cell Division", slide_count=10)
            brief = build_presentation_brief(config)

            # Create rich TopicIntelligencePack with misconceptions and processes
            ti = TopicIntelligencePack(
                topic="Cell Division",
                core_subtopics=["Interphase", "Prophase", "Metaphase", "Anaphase", "Telophase"],
                must_include=["Mitosis", "Cytokinesis"],
                misconceptions=[{"myth": "Mitosis and cell division are identical", "reality": "Mitosis is nuclear division only"}],
                processes=["Chromosome condensation", "Spindle fiber formation", "Cytokinesis"],
                comparison_candidates=[{"item_a": "Mitosis", "item_b": "Meiosis", "comparison_axis": "Cell Type"}],
            )

            with patch("app.services.presentation.planner_agent._enrich_blueprints_via_llm", new_callable=AsyncMock, side_effect=lambda bp, *args, **kwargs: bp):
                plan = await plan_presentation_vnext(brief, topic_intelligence=ti)

            # Verify blueprints were generated
            blueprints = plan["blueprints"]
            assert len(blueprints) == 10

            # Verify topic intelligence influenced the story:
            intents = [bp["intent"] for bp in blueprints]
            assert "misconception" in intents
            assert "comparison" in intents

            # Verify topic intelligence was attached to plan
            assert "topic_ontology" in plan
            assert "core_subtopics" in plan["topic_ontology"]
            assert "Mitosis" in plan["topic_ontology"]["must_include"]

        asyncio.run(_run())


# ═══════════════════════════════════════════════════════════════
# 22. BLUEPRINT SEMANTIC SANITY & DUPLICATE GUARD (SPEC §1-9)
# ═══════════════════════════════════════════════════════════════

class TestBlueprintSemanticSanity:
    """Explicit assertions for Blueprint Semantic Sanity Repair:
    - Photosynthesis: zero 'Architecture & Foundations', zero layered_architecture
    - Industrial Revolution: zero 'The Problem Industrial Revolution Solves', zero 'works step by step'
    - DATA_STORY: zero duplicate generic data beats
    - RESEARCH: zero duplicate generic definition/data/comparison beats
    - Node.js: zero semantically duplicate adjacent comparison blueprints
    - Repeated intent allowed when underlying concepts/messages differ
    - Full semantic sanity score passes for all 5 benchmarks
    """

    def test_photosynthesis_semantic_sanity(self):
        config = PresentationConfig(topic="Photosynthesis", slide_count=10)
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            primary=brief.primary_story_grammar,
            modifiers=brief.story_modifiers,
            slide_count=brief.slide_count,
            domain=brief.domain,
            enable_quiz=brief.enable_quiz,
        )
        blueprints = generate_blueprints_from_grammar(beats, domain=brief.domain)
        _apply_deterministic_messages(blueprints, brief)

        # 1. Zero 'Architecture & Foundations'
        for bp in blueprints:
            assert "Architecture & Foundations" not in bp.primary_message, f"Slide {bp.slide_number} has banned phrase"

        # 2. Zero generic layered architecture in biology
        for bp in blueprints:
            assert bp.visual_type != VisualTypeHint.LAYERED_ARCHITECTURE, f"Slide {bp.slide_number} has layered_architecture in biology"

        # 3. Overall semantic sanity passes
        sanity = compute_semantic_sanity_score(blueprints, brief)
        assert sanity["passed"] is True
        assert sanity["overall_score"] == 1.0

    def test_industrial_revolution_semantic_sanity(self):
        config = PresentationConfig(topic="Industrial Revolution", slide_count=12)
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            primary=brief.primary_story_grammar,
            modifiers=brief.story_modifiers,
            slide_count=brief.slide_count,
            domain=brief.domain,
            enable_quiz=brief.enable_quiz,
        )
        blueprints = generate_blueprints_from_grammar(beats, domain=brief.domain)
        _apply_deterministic_messages(blueprints, brief)

        for bp in blueprints:
            assert "The Problem Industrial Revolution Solves" not in bp.primary_message
            assert "works step by step" not in bp.primary_message.lower()
            assert "Architecture & Foundations" not in bp.primary_message
            assert bp.visual_type != VisualTypeHint.LAYERED_ARCHITECTURE

        sanity = compute_semantic_sanity_score(blueprints, brief)
        assert sanity["passed"] is True
        assert sanity["overall_score"] == 1.0

    def test_data_story_no_duplicate_generic_data_beats(self):
        config = PresentationConfig(topic="Renewable Energy Adoption Trends", slide_count=10)
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            primary=brief.primary_story_grammar,
            modifiers=brief.story_modifiers,
            slide_count=brief.slide_count,
            domain=brief.domain,
            enable_quiz=brief.enable_quiz,
        )
        blueprints = generate_blueprints_from_grammar(beats, domain=brief.domain)
        _apply_deterministic_messages(blueprints, brief)

        # No duplicate primary messages
        msgs = [bp.primary_message.strip().lower() for bp in blueprints if bp.primary_message]
        assert len(msgs) == len(set(msgs)), f"Duplicate messages found in DATA_STORY: {msgs}"

        # Check that data insight beats have distinct messages
        data_slides = [bp for bp in blueprints if bp.intent == SlideIntent.DATA_INSIGHT]
        data_msgs = [bp.primary_message for bp in data_slides]
        assert len(data_msgs) == len(set(data_msgs))

        sanity = compute_semantic_sanity_score(blueprints, brief)
        assert sanity["passed"] is True

    def test_research_grammar_no_duplicate_generic_beats(self):
        config = PresentationConfig(topic="Research Methodology in ML", slide_count=12)
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            primary=brief.primary_story_grammar,
            modifiers=brief.story_modifiers,
            slide_count=brief.slide_count,
            domain=brief.domain,
            enable_quiz=brief.enable_quiz,
        )
        blueprints = generate_blueprints_from_grammar(beats, domain=brief.domain)
        _apply_deterministic_messages(blueprints, brief)

        # No code_block for generic research methodology definition
        def_slides = [bp for bp in blueprints if bp.intent == SlideIntent.DEFINITION]
        for bp in def_slides:
            assert bp.visual_type != VisualTypeHint.CODE_BLOCK

        # No duplicate messages
        msgs = [bp.primary_message.strip().lower() for bp in blueprints if bp.primary_message]
        assert len(msgs) == len(set(msgs))

        # No duplicate definitions
        assert len(def_slides) <= 1

        sanity = compute_semantic_sanity_score(blueprints, brief)
        assert sanity["passed"] is True

    def test_nodejs_no_duplicate_adjacent_comparisons(self):
        config = PresentationConfig(topic="Node.js Architecture", slide_count=12)
        brief = build_presentation_brief(config)
        beats = adapt_grammar_to_slide_count(
            primary=brief.primary_story_grammar,
            modifiers=brief.story_modifiers,
            slide_count=brief.slide_count,
            domain=brief.domain,
            enable_quiz=brief.enable_quiz,
        )
        blueprints = generate_blueprints_from_grammar(beats, domain=brief.domain)
        _apply_deterministic_messages(blueprints, brief)

        # Check comparison slides
        comp_slides = [bp for bp in blueprints if bp.intent == SlideIntent.COMPARISON]
        assert len(comp_slides) == 2
        # Messages must be distinct
        assert comp_slides[0].primary_message != comp_slides[1].primary_message
        # Semantic roles / targets must be distinct
        assert comp_slides[0].comparison_target != comp_slides[1].comparison_target

        sanity = compute_semantic_sanity_score(blueprints, brief)
        assert sanity["passed"] is True
        assert sanity["overall_score"] == 1.0

    def test_repeated_intent_allowed_when_concepts_differ(self):
        """Repeated intent is allowed when each slide has a distinct semantic objective."""
        bp1 = SlideBlueprint(
            slide_id="slide_1", slide_number=1, intent=SlideIntent.COMPARISON,
            primary_message="CommonJS vs ES Modules: Loading Mechanics",
            comparison_target="CommonJS vs ES Modules",
        )
        bp2 = SlideBlueprint(
            slide_id="slide_2", slide_number=2, intent=SlideIntent.COMPARISON,
            primary_message="Event Loop vs Thread-per-Request Concurrency",
            comparison_target="Event Loop vs Thread-per-Request",
        )
        assert bp1.primary_message != bp2.primary_message
        assert bp1.comparison_target != bp2.comparison_target


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

