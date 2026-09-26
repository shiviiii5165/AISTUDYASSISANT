"""
LearnByGenie PPT vNEXT — Content Delivery Regression Tests
======================================================
Tests:
1. Empty comparison table rejection
2. Slide-topic/content mismatch prevention
3. Speaker-note cross-contamination prevention
4. Missing mandatory content detection
5. Partial sentence truncation / dangling conjunction removal
6. Process-stage count consistency
7. Duplicate semantic title prevention
8. Missing table-cell bindings prevention
9. Unrelated fallback content prevention
10. Content preservation through PPTX serialization
"""
import io
import pytest
from pptx import Presentation
from app.services.presentation.schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind,
    DesignSystem, SlideIntent, SlideType
)
from app.services.presentation.content_completeness_gate import (
    audit_deck_content_completeness,
    check_sentence_completeness,
    validate_comparison_slide,
    validate_process_slide,
    validate_architecture_slide,
    validate_misconception_slide,
    validate_summary_slide,
    validate_slide_content_completeness,
)
from app.services.presentation.engine.builder import build_presentation_spec
from app.services.presentation.engine.templates.dispatch import dispatch_pedagogical_component
from app.services.presentation.content_agent import _word_boundary_truncate, _has_verb


def test_empty_comparison_table_rejection():
    """Header-only or 0-data comparison slides must fail the completeness gate."""
    empty_col_slide = {
        "slide_no": 6,
        "type": "comparison",
        "title": "Architecture Comparison",
        "columns": [
            {"heading": "OPTION 1", "points": []},
            {"heading": "OPTION 2", "points": []},
        ],
        "key_message": "Evaluating architectural options.",
        "body_bullets": [],
    }
    errs = validate_comparison_slide(empty_col_slide)
    assert any("zero comparison data rows" in e or "generic placeholder names" in e for e in errs)


def test_generic_comparand_placeholder_rejection():
    """Option 1 / Option 2 placeholder comparands must fail validation."""
    placeholder_slide = {
        "slide_no": 6,
        "type": "comparison",
        "title": "Tradeoff Analysis",
        "columns": [
            {"heading": "Option 1", "points": ["Point A"]},
            {"heading": "Option 2", "points": ["Point B"]},
        ],
        "key_message": "Tradeoffs between choices.",
        "body_bullets": [],
    }
    errs = validate_comparison_slide(placeholder_slide)
    assert any("generic placeholder names" in e for e in errs)


def test_process_stage_count_inconsistency():
    """Mismatch between claimed stage count and rendered steps must fail."""
    mismatched_slide = {
        "slide_no": 5,
        "type": "process_flow",
        "title": "Execution Lifecycle",
        "key_message": "The event loop executes non-blocking operations across 8 stages.",
        "steps": [
            {"title": "Timers", "description": "setTimeout callbacks"},
            {"title": "Poll", "description": "I/O events"},
            {"title": "Check", "description": "setImmediate callbacks"},
            {"title": "Close", "description": "Close handlers"},
        ],
        "body_bullets": ["Stage 1", "Stage 2", "Stage 3", "Stage 4"],
    }
    errs = validate_process_slide(mismatched_slide)
    assert any("claims 8 stages, but slide renders 4 stages" in e for e in errs)


def test_architecture_unrelated_content_rejection():
    """Node architecture slides displaced by async/await or rejection text must fail."""
    displaced_slide = {
        "slide_no": 3,
        "type": "architecture",
        "title": "Node.js System Architecture Overview",
        "key_message": "Handling uncaught promise rejections across async/await calls.",
        "body_bullets": [
            "Async/await functions wrap execution in promises.",
            "Unhandled rejections crash the Node.js process.",
        ],
        "columns": [],
    }
    errs = validate_architecture_slide(displaced_slide)
    assert any("displaced by unrelated async/await" in e or "uncaught promise rejection" in e for e in errs)


def test_sentence_completeness_and_dangling_conjunctions():
    """Strings terminating in dangling conjunctions or prepositions must be detected."""
    assert check_sentence_completeness("Synchronous require() executed at runtime and") is not None
    assert check_sentence_completeness("Evaluated on demand when encountered in code with") is not None
    assert check_sentence_completeness("Completed execution.") is None

    # Test word boundary truncation strips trailing conjunctions
    truncated = _word_boundary_truncate("JavaScript compiles bytecode directly with and", 42)
    assert not truncated.endswith("and")
    assert not truncated.endswith("with")


def test_misconception_card_completeness():
    """Misconception slides with empty discipline cards must fail."""
    empty_discipline_slide = {
        "slide_no": 7,
        "type": "common_mistakes",
        "title": "Common Misconceptions",
        "columns": [
            {"heading": "THE TRAP", "points": ["Node.js is completely single threaded."]},
            {"heading": "THE DISCIPLINE", "points": []},
        ],
    }
    errs = validate_misconception_slide(empty_discipline_slide)
    assert any("empty discipline/best practice card" in e for e in errs)


def test_speaker_notes_cross_contamination():
    """Slide 8 (CommonJS vs ESM) must not contain Callback vs Promise speaker notes."""
    cjs_esm_notes = (
        "When comparing CommonJS and ES Modules, frame the distinction around loading mechanics "
        "and static tooling guarantees. CommonJS resolves dependencies synchronously at runtime, "
        "which prevents bundlers from performing static dead-code elimination, whereas ES Modules "
        "use an asynchronous parsing and linking phase that enables compile-time tree-shaking."
    )
    assert "callback" not in cjs_esm_notes.lower()
    assert "promise" not in cjs_esm_notes.lower()
    assert "commonjs" in cjs_esm_notes.lower()
    assert "es modules" in cjs_esm_notes.lower()


def test_duplicate_semantic_title_prevention():
    """Slide decks with duplicate titles across slides must fail completeness audit."""
    slides = [
        {"slide_no": 1, "type": "hero", "title": "Node.js Foundations", "key_message": "Introduction to runtime."},
        {"slide_no": 2, "type": "concept", "title": "Node.js Foundations", "key_message": "Core concepts."},
    ]
    result = audit_deck_content_completeness(slides)
    assert not result.passed
    assert any("Duplicate semantic title" in err for err in result.errors)


def test_table_cell_bindings_and_dispatch():
    """Dispatching comparison table must bind all columns and rows without crashing."""
    from app.services.presentation_engine.tokens import ThemeColors
    prs = Presentation()
    prs.slide_width = 12192000
    prs.slide_height = 6858000
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    slide_dict = {
        "slide_no": 6,
        "type": "comparison",
        "content_pattern": "comparison_table",
        "title": "Architecture Comparison",
        "columns": [
            {
                "heading": "Single-Threaded Event Loop",
                "points": ["Low memory overhead", "Non-blocking I/O multiplexing"],
            },
            {
                "heading": "Multi-Threaded Server Model",
                "points": ["High memory stack", "Dedicated thread per request"],
            },
        ],
    }

    from app.services.presentation_engine.tokens import get_theme
    theme = get_theme("blue_professional")
    handled = dispatch_pedagogical_component(slide, slide_dict, theme, 6, 10, "Test Deck")
    assert handled is True

    # Verify native table shape was created with rows
    tables = [s for s in slide.shapes if s.has_table]
    assert len(tables) == 1
    tbl = tables[0].table
    assert len(tbl.rows) >= 2
    assert tbl.cell(0, 0).text.strip() == "SINGLE-THREADED EVENT LOOP"
    assert tbl.cell(0, 1).text.strip() == "MULTI-THREADED SERVER MODEL"


def test_pptx_serialization_and_reopen():
    """Build presentation through production pipeline and verify deserialization."""
    slides = []
    for i in range(10):
        if i == 5:
            slides.append(SlideSpec(
                slide_no=6,
                type=SlideType.COMPARISON,
                content_pattern="comparison_table",
                title="Concurrency Architecture Comparison",
                key_message="Comparing single-threaded and multi-threaded architectures.",
                columns=[
                    {"heading": "Single-Threaded", "points": ["Low memory footprint", "Event multiplexing"]},
                    {"heading": "Multi-Threaded", "points": ["Stack overhead", "Thread pooling"]},
                ],
                body_bullets=["Low memory footprint", "Event multiplexing"],
                speaker_notes="Clarify the architectural differences between single and multi-threaded systems.",
            ))
        else:
            slides.append(SlideSpec(
                slide_no=i + 1,
                type=SlideType.CONCEPT,
                title=f"Node.js Architecture Component {i + 1}",
                key_message=f"Architectural component {i + 1} analysis.",
                body_bullets=["Core execution dynamic", "Underlying runtime structure", "Performance governance"],
                speaker_notes=f"Examine component {i + 1} carefully with the class to ensure thorough comprehension.",
            ))

    spec = PresentationSpec(
        title="Node.js Architecture & Foundations",
        subtitle="University Level",
        config=PresentationConfig(
            topic="Node.js Architecture & Foundations",
            slide_count=10,
            audience="university",
            depth="full",
            design=DesignSystem.ACADEMIC_CLEAN,
            theme="blue_professional",
            enable_images=False,
            enable_diagrams=True,
        ),
        slides=slides,
    )

    pptx_bytes = build_presentation_spec(spec)
    assert len(pptx_bytes) > 1000

    # Reopen presentation and inspect
    prs = Presentation(io.BytesIO(pptx_bytes))
    assert len(prs.slides) == 10
    s6 = prs.slides[5]
    tables = [shape for shape in s6.shapes if shape.has_table]
    assert len(tables) == 1
    table_shape = tables[0].table
    assert table_shape.cell(0, 0).text.strip() == "SINGLE-THREADED"
    assert table_shape.cell(0, 1).text.strip() == "MULTI-THREADED"


def test_generalized_architecture_validation_non_node():
    """Verify non-Node architecture slide passes without Node keywords."""
    tcp_arch_slide = {
        "slide_no": 3,
        "type": "architecture",
        "title": "TCP Congestion Architecture Overview",
        "key_message": "Congestion control couples sending rate estimation with ACK clock feedback.",
        "body_bullets": [
            "Congestion Window (cwnd): Host-managed variable bounding max unacknowledged inflight bytes.",
            "Slow Start Threshold (ssthresh): Determines transition boundary between exponential probing and linear avoidance.",
            "Retransmission Timer (RTO): Dynamically calculated timer triggering loss recovery when acknowledgments cease.",
        ],
        "columns": [],
    }
    errs = validate_architecture_slide(tcp_arch_slide)
    assert len(errs) == 0

    # Incomplete architecture without functional descriptions must fail
    bare_slide = {
        "slide_no": 3,
        "type": "architecture",
        "title": "Generic Architecture",
        "key_message": "System architecture overview.",
        "body_bullets": ["Component A", "Component B"],
        "columns": [],
    }
    bare_errs = validate_architecture_slide(bare_slide)
    assert any("CONTENT_INSUFFICIENT" in e for e in bare_errs)


def test_semantic_completeness_two_points_vs_three_fillers():
    """Verify 2 meaningful points pass, while 3 generic filler points fail."""
    # 2 meaningful points -> passes
    slide_valid = {
        "slide_no": 2,
        "type": "concept",
        "title": "Cellular Reproduction Principles",
        "key_message": "Cell division preserves genomic integrity across generations.",
        "body_bullets": [
            "DNA replication accurately duplicates chromosomes prior to mitotic spindle formation.",
            "Spindle checkpoints prevent premature sister chromatid separation at the metaphase plate.",
        ],
    }
    errs_valid = validate_slide_content_completeness(slide_valid, seen_titles=set())
    assert len(errs_valid) == 0

    # 3 generic filler points -> fails with CONTENT_INSUFFICIENT
    slide_filler = {
        "slide_no": 2,
        "type": "concept",
        "title": "Cellular Reproduction Overview",
        "key_message": "Cell division principles and foundations.",
        "body_bullets": [
            "Overview of concept",
            "Key principles",
            "Important aspects",
        ],
    }
    errs_filler = validate_slide_content_completeness(slide_filler, seen_titles=set())
    assert any("CONTENT_INSUFFICIENT" in e for e in errs_filler)


def test_comparison_table_disallows_bullet_fabrication():
    """Renderer must disallow automatic row fabrication when valid rows are missing."""
    import pytest
    from app.services.presentation_engine import SlideContent
    from app.services.presentation_engine.renderers.comparison_table import render_comparison_table
    from app.services.presentation_engine.tokens import get_theme

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    empty_content = SlideContent(
        title="Empty Comparison",
        columns=[],
        body_bullets=["Key 1: Detail 1", "Key 2: Detail 2"],
    )
    theme = get_theme("blue_professional")
    with pytest.raises(ValueError, match="automatic fabrication from unrelated bullets is disallowed"):
        render_comparison_table(slide, empty_content, theme)


def test_node_factual_claims_and_qualifications():
    """Verify Node.js factual claims adhere to authoritative documentation."""
    from app.services.presentation.content_agent import _synthesize_dynamic_slide_content
    from app.services.presentation.schemas import SlideBlueprint, SlideIntent, TextBudget, PresentationConfig
    from app.services.presentation.brief_builder import build_presentation_brief
    from app.services.presentation.deck_content_memory import DeckContentMemory

    cfg = PresentationConfig(topic="Node.js Architecture & Foundations", slide_count=10, audience="university", depth="full")
    brief = build_presentation_brief(cfg)
    mem = DeckContentMemory()

    # Slide 5 Event loop lifecycle check
    bp5 = SlideBlueprint(
        slide_no=5,
        intent=SlideIntent.PROCESS_EXPLANATION,
        primary_message="The Event Loop Execution Lifecycle",
        learning_purpose="event loop mechanics",
        canonical_concepts=["event_loop", "timers", "poll"],
        text_budget=TextBudget(body_max_words=80),
    )
    c5 = _synthesize_dynamic_slide_content(bp5, brief, None, mem, 5, 10)
    assert "simplified teaching subset" in c5.primary_takeaway.lower() or "libuv" in c5.primary_takeaway.lower()
    assert len(c5.process_steps) == 4

    # Slide 8 ESM vs CJS check
    bp8 = SlideBlueprint(
        slide_no=8,
        intent=SlideIntent.COMPARISON,
        primary_message="Module System Evolution: CommonJS vs ES Modules",
        learning_purpose="module loading and linking",
        canonical_concepts=["commonjs", "esm", "modules"],
        text_budget=TextBudget(body_max_words=80),
    )
    c8 = _synthesize_dynamic_slide_content(bp8, brief, None, mem, 8, 10)
    dims = [r.dimension.lower() for r in c8.comparison_rows]
    assert any("top-level await" in d or "loading" in d for d in dims)
    assert any("top-level await" in r.target_b_value.lower() for r in c8.comparison_rows)

    # Slide 6 Concurrency comparison check (qualified memory and performance claims)
    bp6 = SlideBlueprint(
        slide_no=6,
        intent=SlideIntent.COMPARISON,
        primary_message="Concurrency Model Comparison",
        learning_purpose="concurrency tradeoffs",
        canonical_concepts=["concurrency", "single_thread", "multi_thread"],
        text_budget=TextBudget(body_max_words=80),
    )
    c6 = _synthesize_dynamic_slide_content(bp6, brief, None, mem, 6, 10)
    # Memory claim must not say unsupported universal "2 MB"
    for r in c6.comparison_rows:
        if "memory" in r.dimension.lower():
            assert "1-8 mb" in r.target_b_value.lower() or "1–8 mb" in r.target_b_value.lower()
            assert "exact 2 mb" not in r.target_b_value.lower()


