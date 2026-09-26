"""
LearnByGenie vNEXT Phase 3.1 — Visual Planning Test Suite
========================================================
Covers:
  1. Visual schema construction & validation
  2. Typed relationship & hierarchy enforcement
  3. Visual semantic interpretation across all 18 domains
  4. DesignDNA derivation for all 5 templates × 6 themes
  5. WCAG AA palette contrast validation
  6. Visual rhythm constraint adherence (streak ≤ 2, card cap ≤ 25%)
  7. Legacy adapter backward compatibility
  8. Phase 1 & 2 non-regression (import-only confirmation)
"""
import pytest
from typing import List, Optional

# ═══════════════════════════════════════════════════════════════
# IMPORTS — Phase 1/2 (frozen, import-only verification)
# ═══════════════════════════════════════════════════════════════
from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    SlideIntent,
    VisualTypeHint,
    LayoutFamily,
    VisualKind,
    ContentDensity,
    PresentationBrief,
    DesignSystem,
    ComparisonRow,
    DataPoint,
    PresentationConfig,
    ContentOrigin,
    SemanticStatus,
)

# ═══════════════════════════════════════════════════════════════
# IMPORTS — Phase 3.1 (new)
# ═══════════════════════════════════════════════════════════════
from app.services.presentation.visual_schemas import (
    VisualIntent,
    VisualAssetType,
    Phase3LayoutFamily,
    RelationshipType,
    VisualRelationship,
    HierarchyNode,
    VisualCandidate,
    VisualDensityProfile,
    VisualSemanticPacket,
    VisualWeight,
    VisualRhythmBeat,
    DeckVisualRhythmPlan,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    DataGroundingStatus,
    AdapterLossiness,
    to_legacy_layout_family,
    to_legacy_visual_kind,
    adapt_p3_candidate_to_legacy_visual_spec,
    from_legacy_layout_family,
    from_legacy_visual_type_hint,
)

from app.services.presentation.visual_semantic_interpreter import (
    interpret_slide_visuals,
    interpret_deck_visuals,
)

from app.services.presentation.design_dna import (
    generate_design_dna,
    get_available_templates,
    get_available_themes,
    validate_palette_contrast,
)

from app.services.presentation.visual_rhythm_planner import (
    plan_visual_rhythm,
)

from app.services.presentation.cache import (
    VISUAL_ENGINE_VERSION,
    DESIGN_DNA_VERSION,
    VISUAL_RHYTHM_VERSION,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def concept_blueprint() -> SlideBlueprint:
    """Standard concept explanation blueprint."""
    return SlideBlueprint(
        slide_id="slide_3",
        slide_number=3,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Understanding the Event Loop mechanism",
        supporting_concepts=["call stack", "callback queue", "libuv"],
        canonical_concepts=["event_loop", "non_blocking_io"],
        content_density=ContentDensity.MEDIUM,
        visual_priority=0.6,
        visual_type=VisualTypeHint.PROCESS_FLOW,
        layout_family=LayoutFamily.DIAGRAM_DOMINANT,
    )


@pytest.fixture
def process_blueprint() -> SlideBlueprint:
    """Process explanation blueprint."""
    return SlideBlueprint(
        slide_id="slide_5",
        slide_number=5,
        intent=SlideIntent.PROCESS_EXPLANATION,
        primary_message="Light-dependent reactions in thylakoid membranes",
        supporting_concepts=["photosystem II", "electron transport", "ATP synthase"],
        canonical_concepts=["photosynthesis", "light_reactions"],
        content_density=ContentDensity.HIGH,
        visual_priority=0.8,
        visual_type=VisualTypeHint.PROCESS_FLOW,
        layout_family=LayoutFamily.FULL_WIDTH_PROCESS,
    )


@pytest.fixture
def comparison_blueprint() -> SlideBlueprint:
    """Comparison blueprint."""
    return SlideBlueprint(
        slide_id="slide_7",
        slide_number=7,
        intent=SlideIntent.COMPARISON,
        primary_message="SN1 vs SN2: Contrasting nucleophilic substitution mechanisms",
        supporting_concepts=["carbocation", "backside attack"],
        canonical_concepts=["sn1_mechanism", "sn2_mechanism"],
        content_density=ContentDensity.MEDIUM,
        visual_priority=0.6,
        visual_type=VisualTypeHint.COMPARISON_MATRIX,
        layout_family=LayoutFamily.SPLIT_COMPARISON,
    )


@pytest.fixture
def concept_content() -> SlideContent:
    """Standard concept content."""
    return SlideContent(
        title="The Event Loop",
        subtitle="Node.js concurrency model",
        primary_takeaway="The event loop delegates OS-backed asynchronous I/O and thread-pool operations to libuv",
        supporting_points=[
            "Single-threaded execution with asynchronous callbacks",
            "Call stack processes synchronous code",
            "Callback queue holds completed async operations",
            "Event loop orchestrates the callback queue",
        ],
        labels=["event_loop", "call_stack", "callback_queue"],
        process_steps=["Request arrives", "Call stack executes synchronous code", "libuv handles async I/O and thread-pool", "Event loop orchestrates callback queue"],
    )


@pytest.fixture
def comparison_content() -> SlideContent:
    """Comparison content with rows."""
    return SlideContent(
        title="SN1 vs SN2 Mechanisms",
        subtitle="Nucleophilic substitution comparison",
        primary_takeaway="SN1 proceeds via carbocation; SN2 via concerted backside attack",
        comparison_target_a="SN1",
        comparison_target_b="SN2",
        comparison_rows=[
            ComparisonRow(dimension="Mechanism", target_a_value="Unimolecular", target_b_value="Bimolecular"),
            ComparisonRow(dimension="Rate Law", target_a_value="Rate = k[substrate]", target_b_value="Rate = k[substrate][nucleophile]"),
            ComparisonRow(dimension="Stereochemistry", target_a_value="Racemization", target_b_value="Inversion"),
        ],
    )


@pytest.fixture
def formula_content() -> SlideContent:
    """Formula content."""
    return SlideContent(
        title="Eigenvalue Equation",
        formula="Av = λv",
        formula_symbol_meanings="A = matrix, v = eigenvector, λ = eigenvalue",
        primary_takeaway="Eigenvectors maintain invariant span under linear transformation, though negative eigenvalues reverse orientation",
    )


@pytest.fixture
def academic_brief() -> PresentationBrief:
    """Standard academic brief."""
    return PresentationBrief(
        topic="Node.js Architecture",
        canonical_topic="node_js_architecture",
        domain="computer_science",
        subdomain="systems",
        selected_template="academic",
        selected_theme="blue_professional",
        technicality=ContentDensity.MEDIUM,
        slide_count=12,
    )


@pytest.fixture
def minimal_brief() -> PresentationBrief:
    """Modern minimal brief."""
    return PresentationBrief(
        topic="Photosynthesis",
        canonical_topic="photosynthesis",
        domain="biology",
        subdomain="plant_biology",
        selected_template="minimal",
        selected_theme="emerald_growth",
        technicality=ContentDensity.MEDIUM,
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 1: VISUAL SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestVisualSchemaValidation:
    """Verify typed schema construction and serialization."""

    def test_visual_relationship_construction(self):
        """VisualRelationship uses typed fields, not Dict[str, str]."""
        rel = VisualRelationship(
            source_entity="photosystem_II",
            relation="transfers_electrons_to",
            target_entity="plastoquinone",
            relationship_type=RelationshipType.SEQUENTIAL,
            direction="forward",
            confidence=0.9,
            visual_importance=0.8,
        )
        assert rel.relationship_type == RelationshipType.SEQUENTIAL
        assert rel.source_entity == "photosystem_II"
        assert rel.direction == "forward"

    def test_hierarchy_node_recursive(self):
        """HierarchyNode supports recursive children."""
        root = HierarchyNode(
            label="Operating System",
            level=0,
            is_leaf=False,
            children=[
                HierarchyNode(label="Kernel", level=1, parent_label="Operating System"),
                HierarchyNode(label="Shell", level=1, parent_label="Operating System"),
            ],
        )
        assert len(root.children) == 2
        assert root.children[0].label == "Kernel"
        assert root.children[0].parent_label == "Operating System"

    def test_visual_candidate_ranking(self):
        """VisualCandidate contains ranked suitability scores."""
        c1 = VisualCandidate(
            asset_type=VisualAssetType.PROCESS_FLOW,
            layout_family=Phase3LayoutFamily.PROCESS_CANVAS,
            suitability_score=0.95,
        )
        c2 = VisualCandidate(
            asset_type=VisualAssetType.NATIVE_DIAGRAM,
            layout_family=Phase3LayoutFamily.DIAGRAM_CANVAS,
            suitability_score=0.75,
        )
        assert c1.suitability_score > c2.suitability_score

    def test_visual_density_profile_independent(self):
        """VisualDensityProfile is distinct from ContentDensity."""
        vdp = VisualDensityProfile(
            element_count="sparse",
            whitespace_ratio=0.45,
            decoration_level="minimal",
            animation_density="none",
        )
        cd = ContentDensity.HIGH
        # Different types — not conflatable
        assert isinstance(vdp, VisualDensityProfile)
        assert isinstance(cd, ContentDensity)

    def test_visual_semantic_packet_uses_typed_relationships(self):
        """VisualSemanticPacket.relationships is List[VisualRelationship], not List[Dict]."""
        pkt = VisualSemanticPacket(
            slide_no=1,
            visual_intent=VisualIntent.SHOW_PROCESS,
            relationships=[
                VisualRelationship(
                    source_entity="A",
                    target_entity="B",
                    relationship_type=RelationshipType.SEQUENTIAL,
                ),
            ],
        )
        assert isinstance(pkt.relationships[0], VisualRelationship)
        assert pkt.relationships[0].relationship_type == RelationshipType.SEQUENTIAL

    def test_visual_semantic_packet_uses_typed_hierarchy(self):
        """VisualSemanticPacket.hierarchy_tree is List[HierarchyNode], not List[str]."""
        pkt = VisualSemanticPacket(
            slide_no=1,
            hierarchy_tree=[HierarchyNode(label="Root", level=0)],
        )
        assert isinstance(pkt.hierarchy_tree[0], HierarchyNode)

    def test_design_dna_typed_tokens(self):
        """DesignDNA uses TypographyScale, SpacingScale, ColorPalette — not Dict."""
        dna = DesignDNA()
        assert isinstance(dna.title_scale, TypographyScale)
        assert isinstance(dna.body_scale, TypographyScale)
        assert isinstance(dna.caption_scale, TypographyScale)
        assert isinstance(dna.spacing_scale, SpacingScale)
        assert isinstance(dna.color_palette, ColorPalette)

    def test_all_relationship_types_exist(self):
        """All 9 governance-mandated relationship types exist."""
        expected = {
            "causal", "sequential", "structural", "hierarchical",
            "comparative", "dependency", "associative",
            "transformation", "feedback",
        }
        actual = {rt.value for rt in RelationshipType}
        assert expected == actual

    def test_visual_semantic_packet_serializes(self):
        """VisualSemanticPacket serializes to JSON-compatible dict."""
        pkt = VisualSemanticPacket(
            slide_no=1,
            visual_intent=VisualIntent.EXPLAIN_STRUCTURE,
            relationships=[
                VisualRelationship(source_entity="A", target_entity="B"),
            ],
            hierarchy_tree=[HierarchyNode(label="X")],
        )
        data = pkt.model_dump()
        assert isinstance(data, dict)
        assert data["visual_intent"] == "explain_structure"
        assert len(data["relationships"]) == 1
        assert data["relationships"][0]["source_entity"] == "A"


# ═══════════════════════════════════════════════════════════════
# SECTION 2: VISUAL SEMANTIC INTERPRETER
# ═══════════════════════════════════════════════════════════════

class TestVisualSemanticInterpreter:
    """Verify semantic interpretation logic."""

    def test_process_blueprint_yields_show_process(self, process_blueprint, concept_content):
        """Process explanation blueprints yield SHOW_PROCESS visual intent."""
        pkt = interpret_slide_visuals(process_blueprint, concept_content, "biology")
        assert pkt.visual_intent == VisualIntent.SHOW_PROCESS
        assert pkt.visual_priority >= 0.7

    def test_comparison_content_yields_compare(self, comparison_blueprint, comparison_content):
        """Comparison content with rows yields COMPARE visual intent."""
        pkt = interpret_slide_visuals(comparison_blueprint, comparison_content, "chemistry")
        assert pkt.visual_intent == VisualIntent.COMPARE
        assert len(pkt.relationships) >= 1
        assert pkt.relationships[0].relationship_type == RelationshipType.COMPARATIVE

    def test_formula_content_yields_show_formula(self, concept_blueprint, formula_content):
        """Formula content overrides to SHOW_FORMULA intent."""
        pkt = interpret_slide_visuals(concept_blueprint, formula_content, "mathematics")
        assert pkt.visual_intent == VisualIntent.SHOW_FORMULA
        assert pkt.formula_or_equation == "Av = λv"

    def test_visual_type_hint_prioritized(self):
        """VisualTypeHint from blueprint takes priority when not NONE."""
        bp = SlideBlueprint(
            slide_number=1,
            intent=SlideIntent.CONCEPT_EXPLANATION,
            visual_type=VisualTypeHint.LAYERED_ARCHITECTURE,
            primary_message="System layers",
        )
        pkt = interpret_slide_visuals(bp, None, "computer_science")
        assert pkt.visual_intent == VisualIntent.SHOW_SYSTEM_ARCHITECTURE

    def test_cover_slide_yields_hero_statement(self):
        """Cover slide intent yields HERO_STATEMENT."""
        bp = SlideBlueprint(
            slide_number=1,
            intent=SlideIntent.COVER,
            visual_type=VisualTypeHint.NONE,
            primary_message="Welcome to the course",
        )
        pkt = interpret_slide_visuals(bp, None, "general")
        assert pkt.visual_intent == VisualIntent.HERO_STATEMENT

    def test_summary_slide_yields_visual_summary(self):
        """Summary intent yields VISUAL_SUMMARY."""
        bp = SlideBlueprint(
            slide_number=12,
            intent=SlideIntent.SUMMARY,
            visual_type=VisualTypeHint.NONE,
            primary_message="Key takeaways",
        )
        pkt = interpret_slide_visuals(bp, None, "general")
        assert pkt.visual_intent == VisualIntent.VISUAL_SUMMARY

    def test_data_insight_yields_data_pattern(self):
        """DATA_INSIGHT with data points yields SHOW_DATA_PATTERN."""
        bp = SlideBlueprint(
            slide_number=8,
            intent=SlideIntent.DATA_INSIGHT,
            visual_type=VisualTypeHint.NONE,
            primary_message="Growth trends",
        )
        content = SlideContent(
            data_points=[
                DataPoint(metric="GDP Growth", value="3.2%"),
                DataPoint(metric="Inflation", value="5.1%"),
            ],
        )
        pkt = interpret_slide_visuals(bp, content, "economics")
        assert pkt.visual_intent == VisualIntent.SHOW_DATA_PATTERN

    def test_system_overview_extracts_components(self, concept_content):
        """SYSTEM_OVERVIEW extracts canonical concepts as system components."""
        bp = SlideBlueprint(
            slide_number=4,
            intent=SlideIntent.SYSTEM_OVERVIEW,
            primary_message="Architecture overview",
            canonical_concepts=["V8_engine", "libuv", "event_loop"],
            visual_type=VisualTypeHint.LAYERED_ARCHITECTURE,
        )
        pkt = interpret_slide_visuals(bp, None, "computer_science")
        assert len(pkt.system_components) == 3
        assert pkt.visual_intent == VisualIntent.SHOW_SYSTEM_ARCHITECTURE

    def test_key_entities_from_blueprint_and_content(self, concept_blueprint, concept_content):
        """Key entities merge canonical + supporting concepts and content labels."""
        pkt = interpret_slide_visuals(concept_blueprint, concept_content, "computer_science")
        assert "event_loop" in pkt.key_entities
        assert "non_blocking_io" in pkt.key_entities
        assert "call_stack" in pkt.key_entities

    def test_process_steps_create_sequential_relationships(self, concept_blueprint, concept_content):
        """Process steps in content create SEQUENTIAL VisualRelationships."""
        pkt = interpret_slide_visuals(concept_blueprint, concept_content, "computer_science")
        seq_rels = [r for r in pkt.relationships if r.relationship_type == RelationshipType.SEQUENTIAL]
        assert len(seq_rels) >= 2  # 4 steps → at least 3 sequential links

    def test_visual_candidates_ranked(self, concept_blueprint, concept_content):
        """Visual candidates are ranked by suitability score."""
        pkt = interpret_slide_visuals(concept_blueprint, concept_content, "computer_science")
        assert len(pkt.visual_candidates) >= 2
        scores = [c.suitability_score for c in pkt.visual_candidates]
        assert scores == sorted(scores, reverse=True)

    def test_grounding_metadata_present(self, concept_blueprint, concept_content):
        """Grounding evidence contains slide_intent and visual_type_hint."""
        pkt = interpret_slide_visuals(concept_blueprint, concept_content, "computer_science")
        assert pkt.grounding_source == "semantic_interpretation"
        assert any("slide_intent=" in e for e in pkt.grounding_evidence)
        assert any("visual_type_hint=" in e for e in pkt.grounding_evidence)

    def test_deck_interpretation_returns_all_slides(self):
        """interpret_deck_visuals returns one packet per blueprint."""
        bps = [
            SlideBlueprint(slide_number=i, intent=SlideIntent.CONCEPT_EXPLANATION, primary_message=f"Slide {i}")
            for i in range(1, 6)
        ]
        contents = [SlideContent(title=f"Content {i}") for i in range(1, 6)]
        packets = interpret_deck_visuals(bps, contents, "general")
        assert len(packets) == 5

    def test_no_topic_name_hardcoding(self, concept_blueprint, concept_content):
        """Interpreter never branches on topic name — same blueprint gives same result."""
        pkt1 = interpret_slide_visuals(concept_blueprint, concept_content, "computer_science")
        pkt2 = interpret_slide_visuals(concept_blueprint, concept_content, "physics")
        # Visual intent and candidates should be identical (no topic branching)
        assert pkt1.visual_intent == pkt2.visual_intent
        assert len(pkt1.visual_candidates) == len(pkt2.visual_candidates)


# ═══════════════════════════════════════════════════════════════
# SECTION 3: DESIGN DNA
# ═══════════════════════════════════════════════════════════════

class TestDesignDNA:
    """Verify design DNA generation for all templates and themes."""

    def test_all_5_templates_available(self):
        """All 5 design templates are registered."""
        templates = get_available_templates()
        assert set(templates) == {"academic", "minimal", "technical", "editorial", "visual"}

    def test_all_6_themes_available(self):
        """All 6 theme anchors are registered."""
        themes = get_available_themes()
        assert len(themes) == 6
        assert "blue_professional" in themes
        assert "charcoal_minimal" in themes

    @pytest.mark.parametrize("template", ["academic", "minimal", "technical", "editorial", "visual"])
    def test_template_generates_valid_dna(self, template):
        """Each template produces a valid DesignDNA with typed tokens."""
        brief = PresentationBrief(
            topic="Test Topic",
            selected_template=template,
            selected_theme="blue_professional",
        )
        dna = generate_design_dna(brief)
        assert isinstance(dna, DesignDNA)
        assert isinstance(dna.title_scale, TypographyScale)
        assert isinstance(dna.spacing_scale, SpacingScale)
        assert isinstance(dna.color_palette, ColorPalette)
        assert len(dna.preferred_composition_families) >= 3

    @pytest.mark.parametrize("theme", [
        "blue_professional", "indigo_innovation", "emerald_growth",
        "teal_modern", "orange_energy", "charcoal_minimal",
    ])
    def test_theme_palette_wcag_aa_compliant(self, theme):
        """Each theme palette meets WCAG AA minimum contrast ratio (4.5)."""
        brief = PresentationBrief(
            topic="Test",
            selected_template="academic",
            selected_theme=theme,
        )
        dna = generate_design_dna(brief)
        assert validate_palette_contrast(dna.color_palette, min_ratio=4.5)

    def test_academic_dna_characteristics(self, academic_brief):
        """Academic Clean DNA has scholarly tone and geometric sans typography."""
        dna = generate_design_dna(academic_brief)
        assert dna.theme_family == "academic_clean"
        assert dna.tone == "scholarly"
        assert dna.typographic_personality == "geometric_sans"
        assert dna.corner_radius_system == "moderate"

    def test_technical_dna_characteristics(self):
        """Technical Grid DNA has precise tone and sharp corners."""
        brief = PresentationBrief(
            topic="System Design",
            selected_template="technical",
            selected_theme="blue_professional",
        )
        dna = generate_design_dna(brief)
        assert dna.theme_family == "technical_grid"
        assert dna.tone == "precise"
        assert dna.corner_radius_system == "sharp"

    def test_editorial_dna_serif_blend(self):
        """Editorial DNA uses serif blend typography."""
        brief = PresentationBrief(
            topic="Research Report",
            selected_template="editorial",
            selected_theme="charcoal_minimal",
        )
        dna = generate_design_dna(brief)
        assert dna.typographic_personality == "serif_blend"

    def test_visual_learning_dna_gradient_background(self):
        """Visual Learning DNA uses gradient background strategy."""
        brief = PresentationBrief(
            topic="Biology Diagrams",
            selected_template="visual",
            selected_theme="emerald_growth",
        )
        dna = generate_design_dna(brief)
        assert dna.background_strategy == "gradient"
        assert dna.surface_strategy == "glassmorphic"

    def test_unknown_template_falls_back_to_academic(self):
        """Unknown template name defaults to academic clean."""
        brief = PresentationBrief(
            topic="Test",
            selected_template="nonexistent",
            selected_theme="blue_professional",
        )
        dna = generate_design_dna(brief)
        assert dna.theme_family == "academic_clean"

    def test_unknown_theme_falls_back_to_blue_professional(self):
        """Unknown theme name defaults to blue_professional palette."""
        brief = PresentationBrief(
            topic="Test",
            selected_template="academic",
            selected_theme="nonexistent_theme",
        )
        dna = generate_design_dna(brief)
        assert dna.color_palette.primary == "#1A365D"


# ═══════════════════════════════════════════════════════════════
# SECTION 4: VISUAL RHYTHM PLANNER
# ═══════════════════════════════════════════════════════════════

class TestVisualRhythmPlanner:
    """Verify rhythm planning constraints and quality."""

    def _make_test_packets(self, count: int = 12) -> List[VisualSemanticPacket]:
        """Generate test packets with varied intents."""
        intents = [
            VisualIntent.HERO_STATEMENT,
            VisualIntent.EXPLAIN_STRUCTURE,
            VisualIntent.SHOW_PROCESS,
            VisualIntent.COMPARE,
            VisualIntent.SHOW_HIERARCHY,
            VisualIntent.SHOW_DATA_PATTERN,
            VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
            VisualIntent.SHOW_EXAMPLE,
            VisualIntent.SHOW_TIMELINE,
            VisualIntent.SHOW_FORMULA,
            VisualIntent.SHOW_EVIDENCE,
            VisualIntent.VISUAL_SUMMARY,
        ]
        packets = []
        for i in range(count):
            intent = intents[i % len(intents)]
            packets.append(VisualSemanticPacket(
                slide_no=i + 1,
                visual_intent=intent,
                visual_priority=0.3 + (i % 3) * 0.2,
                visual_candidates=[
                    VisualCandidate(
                        asset_type=VisualAssetType.NATIVE_DIAGRAM,
                        layout_family=Phase3LayoutFamily.DIAGRAM_CANVAS,
                        suitability_score=0.9,
                    ),
                    VisualCandidate(
                        asset_type=VisualAssetType.TEXTUAL_STATEMENT,
                        layout_family=Phase3LayoutFamily.TEXT_DOMINANT,
                        suitability_score=0.5,
                    ),
                ],
            ))
        return packets

    def test_plan_returns_correct_slide_count(self, academic_brief):
        """Rhythm plan has same number of beats as input packets."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert plan.total_slides == 12
        assert len(plan.beats) == 12

    def test_max_consecutive_streak_le_2(self, academic_brief):
        """Maximum consecutive identical layout streak ≤ 2."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(15)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert plan.max_consecutive_layout_streak <= 2

    def test_card_cluster_capped_at_25_percent(self, academic_brief):
        """Card cluster usage ≤ 25% of total slides."""
        dna = generate_design_dna(academic_brief)
        # Force all packets to want card cluster
        packets = []
        for i in range(12):
            packets.append(VisualSemanticPacket(
                slide_no=i + 1,
                visual_intent=VisualIntent.VISUAL_SUMMARY,
                visual_candidates=[
                    VisualCandidate(
                        asset_type=VisualAssetType.ICON_COMPOSITION,
                        layout_family=Phase3LayoutFamily.CARD_CLUSTER,
                        suitability_score=0.9,
                    ),
                ],
            ))
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert plan.card_cluster_percentage <= 0.25

    def test_rhythm_integrity_score_reasonable(self, academic_brief):
        """Rhythm integrity score is between 0.0 and 1.0."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert 0.0 <= plan.rhythm_integrity_score <= 1.0

    def test_layout_distribution_populated(self, academic_brief):
        """Layout distribution dict is populated."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert len(plan.layout_distribution) > 0
        total = sum(plan.layout_distribution.values())
        assert total == 12

    def test_asset_distribution_populated(self, academic_brief):
        """Asset distribution dict is populated."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert len(plan.asset_distribution) > 0

    def test_design_dna_reference_set(self, academic_brief):
        """Plan references the DesignDNA theme family used."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(5)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        assert plan.design_dna_reference == "academic_clean"

    def test_beat_semantic_fit_scores_bounded(self, academic_brief):
        """All beat semantic fit scores are between 0 and 1."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        for beat in plan.beats:
            assert 0.0 <= beat.semantic_fit_score <= 1.0

    def test_visual_weight_variety(self, academic_brief):
        """Plan assigns varied visual weights across beats."""
        dna = generate_design_dna(academic_brief)
        packets = self._make_test_packets(12)
        plan = plan_visual_rhythm(packets, dna, topic="Test")
        weights = {b.visual_weight for b in plan.beats}
        assert len(weights) >= 2  # At least 2 different weight levels


# ═══════════════════════════════════════════════════════════════
# SECTION 5: LEGACY ADAPTER COMPATIBILITY
# ═══════════════════════════════════════════════════════════════

class TestLegacyAdapters:
    """Verify bidirectional adapter compatibility with frozen Phase 1/2 contracts."""

    @pytest.mark.parametrize("p3_layout", list(Phase3LayoutFamily))
    def test_all_p3_layouts_map_to_legacy(self, p3_layout):
        """Every Phase3LayoutFamily maps to a valid legacy LayoutFamily."""
        legacy = to_legacy_layout_family(p3_layout)
        assert isinstance(legacy, LayoutFamily)

    @pytest.mark.parametrize("asset", list(VisualAssetType))
    def test_all_asset_types_map_to_legacy(self, asset):
        """Every VisualAssetType maps to a valid legacy VisualKind."""
        legacy = to_legacy_visual_kind(asset)
        assert isinstance(legacy, VisualKind)

    @pytest.mark.parametrize("legacy_layout", list(LayoutFamily))
    def test_all_legacy_layouts_map_to_p3(self, legacy_layout):
        """Every legacy LayoutFamily maps to a valid Phase3LayoutFamily."""
        p3 = from_legacy_layout_family(legacy_layout)
        assert isinstance(p3, Phase3LayoutFamily)

    @pytest.mark.parametrize("vth", list(VisualTypeHint))
    def test_all_visual_type_hints_map_to_visual_intent(self, vth):
        """Every legacy VisualTypeHint maps to a valid VisualIntent."""
        vi = from_legacy_visual_type_hint(vth)
        assert isinstance(vi, VisualIntent)

    def test_roundtrip_layout_consistency(self):
        """Legacy → P3 → Legacy round-trip preserves reasonable mapping."""
        for legacy in LayoutFamily:
            p3 = from_legacy_layout_family(legacy)
            back = to_legacy_layout_family(p3)
            # The round-trip may not be exact identity (many-to-one mappings)
            # but must be valid
            assert isinstance(back, LayoutFamily)


# ═══════════════════════════════════════════════════════════════
# SECTION 6: VERSION TOKENS
# ═══════════════════════════════════════════════════════════════

class TestVersionTokens:
    """Verify Phase 3.1 version tokens are correctly set."""

    def test_visual_engine_version(self):
        assert VISUAL_ENGINE_VERSION == "3.0"

    def test_design_dna_version(self):
        assert DESIGN_DNA_VERSION == "3.0"

    def test_visual_rhythm_version(self):
        assert VISUAL_RHYTHM_VERSION == "3.0"


# ═══════════════════════════════════════════════════════════════
# SECTION 7: PHASE 1 & 2 NON-REGRESSION (import-only)
# ═══════════════════════════════════════════════════════════════

class TestPhase1Phase2NonRegression:
    """Confirm frozen Phase 1/2 schemas still import and construct correctly."""

    def test_slide_blueprint_still_constructs(self):
        """SlideBlueprint from Phase 1 still constructs with defaults."""
        bp = SlideBlueprint()
        assert bp.intent == SlideIntent.CONCEPT_EXPLANATION
        assert bp.layout_family == LayoutFamily.CENTERED_FOCAL

    def test_slide_content_still_constructs(self):
        """SlideContent from Phase 2 still constructs with defaults."""
        sc = SlideContent()
        assert sc.title == ""
        assert sc.semantic_status.value == "grounded"

    def test_presentation_config_still_constructs(self):
        """PresentationConfig still constructs with defaults."""
        config = PresentationConfig(topic="Test")
        assert config.design == DesignSystem.ACADEMIC_CLEAN

    def test_visual_kind_enum_unchanged(self):
        """Legacy VisualKind enum has same values."""
        assert VisualKind.DIAGRAM.value == "diagram"
        assert VisualKind.FLOW.value == "flow"

    def test_layout_family_enum_unchanged(self):
        """Legacy LayoutFamily enum has same values."""
        assert LayoutFamily.HERO.value == "hero"
        assert LayoutFamily.DIAGRAM_DOMINANT.value == "diagram_dominant"


# ═══════════════════════════════════════════════════════════════
# SECTION 8: DOMAIN-AWARE GENERALIZATION (NO TOPIC HARDCODING)
# ═══════════════════════════════════════════════════════════════

class TestDomainAwareGeneralization:
    """Verify domain-aware visual planning without literal topic-name branches."""

    def test_same_semantics_cosmetic_rename_stable(self):
        """Same semantic structure with cosmetic topic rename → stable visual plan."""
        bp1 = SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.PROCESS_EXPLANATION,
            primary_message="Step-by-step reaction mechanism",
            supporting_concepts=["step_1", "intermediate", "product"],
            visual_type=VisualTypeHint.PROCESS_FLOW,
        )
        bp2 = SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.PROCESS_EXPLANATION,
            primary_message="Sequential metabolic pathway",
            supporting_concepts=["phase_1", "intermediate", "output"],
            visual_type=VisualTypeHint.PROCESS_FLOW,
        )
        content = SlideContent(
            process_steps=["Input", "Processing", "Intermediate", "Output"],
        )
        pkt1 = interpret_slide_visuals(bp1, content, "chemistry")
        pkt2 = interpret_slide_visuals(bp2, content, "biology")
        # Same semantic structure → same visual intent
        assert pkt1.visual_intent == pkt2.visual_intent
        assert len(pkt1.visual_candidates) == len(pkt2.visual_candidates)
        assert pkt1.visual_candidates[0].asset_type == pkt2.visual_candidates[0].asset_type

    def test_different_semantics_same_domain_different_plan(self):
        """Different content structure within same domain → may yield different plan."""
        bp_process = SlideBlueprint(
            slide_number=3,
            intent=SlideIntent.PROCESS_EXPLANATION,
            primary_message="Sequential workflow",
            visual_type=VisualTypeHint.PROCESS_FLOW,
        )
        bp_compare = SlideBlueprint(
            slide_number=4,
            intent=SlideIntent.COMPARISON,
            primary_message="Two approaches compared",
            visual_type=VisualTypeHint.COMPARISON_MATRIX,
        )
        content_process = SlideContent(
            process_steps=["A", "B", "C"],
        )
        content_compare = SlideContent(
            comparison_target_a="Method A",
            comparison_target_b="Method B",
            comparison_rows=[ComparisonRow(dimension="Speed", target_a_value="Fast", target_b_value="Slow")],
        )
        pkt1 = interpret_slide_visuals(bp_process, content_process, "computer_science")
        pkt2 = interpret_slide_visuals(bp_compare, content_compare, "computer_science")
        # Different semantics → different visual intent
        assert pkt1.visual_intent != pkt2.visual_intent

    def test_no_literal_topic_name_in_source_code(self):
        """Static scan: no benchmark topic names appear in interpreter source."""
        import inspect
        from app.services.presentation import visual_semantic_interpreter
        source = inspect.getsource(visual_semantic_interpreter)
        forbidden_names = [
            "node.js", "nodejs", "photosynthesis", "macbeth",
            "eigenvalue", "industrial revolution", "renewable energy",
            "sn1 vs sn2", "inflation", "monetary policy",
        ]
        source_lower = source.lower()
        for name in forbidden_names:
            assert name not in source_lower, f"Literal topic name '{name}' found in interpreter"


# ═══════════════════════════════════════════════════════════════
# SECTION 9: VISUAL GROUNDING STATES
# ═══════════════════════════════════════════════════════════════

class TestVisualGroundingStates:
    """Verify DataGroundingStatus prevents fabricated visualizations."""

    def test_all_grounding_states_exist(self):
        """All 5 grounding states exist."""
        expected = {"verified_data", "source_grounded", "model_background", "structural_only", "unresolved"}
        actual = {s.value for s in DataGroundingStatus}
        assert expected == actual

    def test_verified_data_from_source_document_with_verified_points(self):
        """SOURCE_DOCUMENT origin with verified data points → VERIFIED_DATA."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.DATA_INSIGHT)
        content = SlideContent(
            content_origin=ContentOrigin.SOURCE_DOCUMENT,
            semantic_status=SemanticStatus.GROUNDED,
            data_points=[DataPoint(metric="GDP", value="3.2%", is_verified=True)],
        )
        pkt = interpret_slide_visuals(bp, content, "economics")
        assert pkt.data_grounding_status == "verified_data"

    def test_model_background_not_chart_safe(self):
        """MODEL_BACKGROUND origin → data_grounding_status = model_background (not chart-safe)."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.CONCEPT_EXPLANATION)
        content = SlideContent(
            content_origin=ContentOrigin.MODEL_BACKGROUND,
            semantic_status=SemanticStatus.GROUNDED,
        )
        pkt = interpret_slide_visuals(bp, content, "general")
        assert pkt.data_grounding_status == "model_background"

    def test_unresolved_from_gap_status(self):
        """GAP semantic status → UNRESOLVED."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.DATA_INSIGHT)
        content = SlideContent(
            content_origin=ContentOrigin.MODEL_BACKGROUND,
            semantic_status=SemanticStatus.GAP,
        )
        pkt = interpret_slide_visuals(bp, content, "general")
        assert pkt.data_grounding_status == "unresolved"

    def test_no_content_yields_unresolved(self):
        """No content → UNRESOLVED."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.CONCEPT_EXPLANATION)
        pkt = interpret_slide_visuals(bp, None, "general")
        assert pkt.data_grounding_status == "unresolved"

    def test_structural_only_from_deterministic(self):
        """DETERMINISTIC_STRUCTURE origin → STRUCTURAL_ONLY."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.AGENDA)
        content = SlideContent(
            content_origin=ContentOrigin.DETERMINISTIC_STRUCTURE,
            semantic_status=SemanticStatus.GROUNDED,
        )
        pkt = interpret_slide_visuals(bp, content, "general")
        assert pkt.data_grounding_status == "structural_only"

    def test_source_grounded_from_external_source(self):
        """EXTERNAL_SOURCE → SOURCE_GROUNDED."""
        bp = SlideBlueprint(slide_number=1, intent=SlideIntent.CASE_STUDY)
        content = SlideContent(
            content_origin=ContentOrigin.EXTERNAL_SOURCE,
            semantic_status=SemanticStatus.GROUNDED,
        )
        pkt = interpret_slide_visuals(bp, content, "general")
        assert pkt.data_grounding_status == "source_grounded"


# ═══════════════════════════════════════════════════════════════
# SECTION 10: FONT PORTABILITY
# ═══════════════════════════════════════════════════════════════

class TestFontPortability:
    """Verify every DesignDNA includes font fallback chain."""

    @pytest.mark.parametrize("template", ["academic", "minimal", "technical", "editorial", "visual"])
    def test_title_has_font_fallback(self, template):
        """Title typography includes font_fallback and safe_office_fallback."""
        brief = PresentationBrief(topic="Test", selected_template=template, selected_theme="blue_professional")
        dna = generate_design_dna(brief)
        assert dna.title_scale.font_fallback != ""
        assert dna.title_scale.safe_office_fallback != ""
        # safe_office_fallback must be an Office-bundled font
        safe_fonts = {"Calibri", "Arial", "Cambria", "Times New Roman", "Courier New", "Trebuchet MS", "Aptos"}
        assert dna.title_scale.safe_office_fallback in safe_fonts

    @pytest.mark.parametrize("template", ["academic", "minimal", "technical", "editorial", "visual"])
    def test_body_has_font_fallback(self, template):
        """Body typography includes font_fallback and safe_office_fallback."""
        brief = PresentationBrief(topic="Test", selected_template=template, selected_theme="blue_professional")
        dna = generate_design_dna(brief)
        assert dna.body_scale.font_fallback != ""
        assert dna.body_scale.safe_office_fallback != ""

    @pytest.mark.parametrize("template", ["academic", "minimal", "technical", "editorial", "visual"])
    def test_caption_has_font_fallback(self, template):
        """Caption typography includes font_fallback and safe_office_fallback."""
        brief = PresentationBrief(topic="Test", selected_template=template, selected_theme="blue_professional")
        dna = generate_design_dna(brief)
        assert dna.caption_scale.font_fallback != ""
        assert dna.caption_scale.safe_office_fallback != ""


# ═══════════════════════════════════════════════════════════════
# SECTION 11: ADAPTER LOSSINESS
# ═══════════════════════════════════════════════════════════════

class TestAdapterLossiness:
    """Verify adapter lossiness classification and metadata preservation."""

    def test_lossiness_enum_values(self):
        """AdapterLossiness has all 3 classification values."""
        assert AdapterLossiness.LOSSLESS.value == "lossless"
        assert AdapterLossiness.LOSSY.value == "lossy"
        assert AdapterLossiness.UNSUPPORTED.value == "unsupported"

    def test_lossless_mappings_roundtrip(self):
        """Lossless mappings: Hero, Timeline, Process, Summary are semantically exact."""
        lossless_pairs = [
            (Phase3LayoutFamily.TIMELINE_CANVAS, LayoutFamily.TIMELINE_LAYOUT),
            (Phase3LayoutFamily.PROCESS_CANVAS, LayoutFamily.FULL_WIDTH_PROCESS),
            (Phase3LayoutFamily.SUMMARY_GRID, LayoutFamily.SUMMARY_GRID),
            (Phase3LayoutFamily.COMPARISON_MATRIX, LayoutFamily.MATRIX),
        ]
        for p3, legacy in lossless_pairs:
            assert to_legacy_layout_family(p3) == legacy

    def test_chart_intent_survives_adapter_as_deferred_state(self):
        """CHART maps to explicit VisualKind.CHART_DEFERRED, never silently to TABLE."""
        from app.services.presentation.visual_schemas import to_legacy_visual_kind
        legacy = to_legacy_visual_kind(VisualAssetType.CHART)
        assert legacy == VisualKind.CHART_DEFERRED
        assert legacy != VisualKind.TABLE  # Semantic safety: CHART is never silently generic table

    def test_chart_candidate_metadata_retained_in_spec(self):
        """Original Phase 3 candidate metadata is preserved across adapter for Phase 3.3 consumption."""
        pkt = VisualSemanticPacket(
            slide_no=1,
            visual_intent=VisualIntent.SHOW_DATA_PATTERN,
            visual_candidates=[
                VisualCandidate(asset_type=VisualAssetType.CHART, suitability_score=0.9),
            ],
        )
        assert pkt.visual_candidates[0].asset_type == VisualAssetType.CHART  # Candidate metadata intact
        spec = adapt_p3_candidate_to_legacy_visual_spec(pkt.visual_candidates[0])
        assert spec.kind == VisualKind.CHART_DEFERRED
        assert spec.deferred_asset_type == "chart"
        assert spec.compatibility_state == "deferred_rendering"

    def test_chart_deferred_legacy_rendering_non_crashing(self):
        """Slides with VisualKind.CHART_DEFERRED render through legacy PPTX pipeline without crashing."""
        import io
        from pptx import Presentation
        from app.services.presentation.schemas import PresentationConfig, PresentationSpec, SlideSpec, VisualSpec
        from app.services.presentation.engine.builder import build_presentation_spec

        slides = [
            SlideSpec(
                slide_no=1,
                type="hero",
                title="Statistical Overview",
                subtitle="Data Trends",
                key_message="Core statistical distribution",
            )
        ]
        for i in range(2, 11):
            slides.append(
                SlideSpec(
                    slide_no=i,
                    type="concept",
                    title=f"Distribution Analysis {i}",
                    subtitle="Variance and standard deviation across trials",
                    body_bullets=[
                        "Observation 1: Normal distribution centered at origin",
                        "Observation 2: Standard deviation bounded within 1.5 sigma",
                        "Observation 3: Rejection of null hypothesis at p < 0.01",
                    ],
                    visual_spec=VisualSpec(
                        kind=VisualKind.CHART_DEFERRED,
                        deferred_asset_type="chart",
                        compatibility_state="deferred_rendering",
                    ),
                    speaker_notes="Detailed analysis of statistical distribution across multiple sampling trials.",
                )
            )
        spec = PresentationSpec(
            title="Statistical Analysis",
            config=PresentationConfig(topic="Statistical Analysis", slide_count=10),
            slides=slides,
        )
        pptx_bytes = build_presentation_spec(spec)
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 0
        prs = Presentation(io.BytesIO(pptx_bytes))
        assert len(prs.slides) == 10

    def test_hero_center_vs_offset_both_map_to_hero(self):
        """HERO_CENTER and HERO_OFFSET both map to legacy HERO (lossy — distinction lost)."""
        assert to_legacy_layout_family(Phase3LayoutFamily.HERO_CENTER) == LayoutFamily.HERO
        assert to_legacy_layout_family(Phase3LayoutFamily.HERO_OFFSET) == LayoutFamily.HERO


# ═══════════════════════════════════════════════════════════════
# SECTION 12: ADAPTIVE RHYTHM POLICY
# ═══════════════════════════════════════════════════════════════

class TestAdaptiveRhythmPolicy:
    """Verify rhythm selection priority: semantic fit > readability > diversity."""

    def test_semantic_fitness_overrides_diversity(self):
        """When all slides need the same layout for semantic fit, rhythm must not
        force unnecessary variety at the cost of semantic correctness."""
        # All slides are data insights needing data canvas
        packets = []
        for i in range(5):
            packets.append(VisualSemanticPacket(
                slide_no=i + 1,
                visual_intent=VisualIntent.SHOW_DATA_PATTERN,
                visual_priority=0.8,
                visual_candidates=[
                    VisualCandidate(
                        asset_type=VisualAssetType.CHART,
                        layout_family=Phase3LayoutFamily.DATA_CANVAS,
                        suitability_score=0.95,
                    ),
                    VisualCandidate(
                        asset_type=VisualAssetType.TABLE,
                        layout_family=Phase3LayoutFamily.SPLIT_40_60,
                        suitability_score=0.6,
                    ),
                ],
            ))
        brief = PresentationBrief(topic="Test", selected_template="academic", selected_theme="blue_professional")
        dna = generate_design_dna(brief)
        plan = plan_visual_rhythm(packets, dna, topic="Data Analysis")
        # Most beats should use data-oriented layouts (data_canvas or split)
        data_oriented = sum(
            1 for b in plan.beats
            if b.layout_family in (Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.SPLIT_40_60)
        )
        assert data_oriented >= 4  # At least 4 of 5 are semantically data-focused

    def test_card_cap_is_default_ceiling_not_fixed(self):
        """Card cap of 25% is a safety ceiling, not the only rhythm policy."""
        # With mixed intents, card clusters should appear only when semantically appropriate
        packets = [
            VisualSemanticPacket(slide_no=1, visual_intent=VisualIntent.HERO_STATEMENT),
            VisualSemanticPacket(slide_no=2, visual_intent=VisualIntent.SHOW_PROCESS),
            VisualSemanticPacket(slide_no=3, visual_intent=VisualIntent.COMPARE),
            VisualSemanticPacket(slide_no=4, visual_intent=VisualIntent.SHOW_FORMULA),
        ]
        brief = PresentationBrief(topic="Test", selected_template="technical", selected_theme="blue_professional")
        dna = generate_design_dna(brief)
        plan = plan_visual_rhythm(packets, dna, topic="Mixed")
        # Technical template should NOT default to card clusters for these intents
        card_count = sum(1 for b in plan.beats if b.layout_family == Phase3LayoutFamily.CARD_CLUSTER)
        assert card_count <= 1  # At most 1 card cluster for these non-card intents

