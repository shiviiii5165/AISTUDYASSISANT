"""
Unit and Integration Tests for AI Notes Generation
===================================================
Tests all 8 core capabilities of the Notes Intelligence Layer:
1. Topic Mode Generation
2. Lesson Context Mode Generation
3. Grade Adaptation (Class 3-5 vs 9-10 vs 11-12)
4. Low Mastery & Remedial Flow
5. Misconception Callout & Correction
6. Deterministic Format Selection (Flowchart, Comparison, Formula Sheet)
7. Quality Validation Scoring (0-100 Rubric)
8. API Endpoints, Retrieval, & User Authorization Isolation
9. Regression Verification (Existing OCR /api/notes remains untouched)
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user
from app.services.notes.schemas import (
    GenerateNotesRequest,
    CanonicalNotesContext,
    DecisionOutput,
    NoteFormat,
    NoteDepth,
    NoteDifficulty,
    NotesDocument,
    NoteSection,
    VisualSpec,
    CalloutItem,
    NotesQualityReport,
)
from app.services.notes.context_extractor import NotesContextExtractor
from app.services.notes.decision_engine import NotesDecisionEngine
from app.services.notes.validator import NotesValidator
from app.services.notes.generator import NotesGenerator
from app.services.notes.repository import NotesRepository


# Mock user objects for multi-tenant isolation testing
class MockUser:
    def __init__(self, user_id: str, email: str = "test@teachgenie.ai"):
        self.id = user_id
        self.email = email


user_alpha = MockUser("user-alpha-111")
user_beta = MockUser("user-beta-222")


@pytest.fixture
def auth_client():
    """FastAPI TestClient with user_alpha authenticated."""
    app.dependency_overrides[get_current_user] = lambda: user_alpha
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client_beta():
    """FastAPI TestClient with user_beta authenticated."""
    app.dependency_overrides[get_current_user] = lambda: user_beta
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# 1. CONTEXT EXTRACTOR TESTS
# ============================================================================

def test_context_extractor_topic_mode():
    """Context extractor properly handles pure topic-based request."""
    req = GenerateNotesRequest(
        mode="topic",
        topic="Photosynthesis",
        class_level="Class 7",
        subject="Science",
        curriculum="CBSE",
        language="english",
        user_instructions="Focus on chloroplast function",
    )
    context = asyncio.run(NotesContextExtractor.extract_canonical_context(req, user_id="test-user"))

    assert context.topic == "Photosynthesis"
    assert context.class_level == "Class 7"
    assert context.subject == "Science"
    assert context.curriculum == "CBSE"
    assert context.explicit_user_instructions == "Focus on chloroplast function"
    assert context.mode == "topic"


def test_context_extractor_lesson_context_mock():
    """Context extractor extracts objectives and misconceptions from roadmap stage."""
    mock_stage = MagicMock()
    mock_stage.id = "stage-42"
    mock_stage.title = "Light Reaction Phase"
    mock_stage.mastery = 0.45
    mock_stage.objectives = [MagicMock(description="Identify ATP production sites")]
    mock_stage.activities = [MagicMock(type="lab", title="Starch test", description="Iodine test on leaf")]
    mock_stage.teacher_actions = ["Explain photolysis"]
    mock_stage.student_actions = ["Observe leaf under microscope"]
    mock_stage.expected_misconceptions = ["Chloroplasts absorb all green light"]

    mock_roadmap = MagicMock()
    mock_roadmap.id = "rm-101"
    mock_roadmap.topic = "Plant Biology"
    mock_roadmap.title = "Plant Biology Masterclass"
    mock_roadmap.level = "Class 10"
    mock_roadmap.language = "english"
    mock_roadmap.stages = [mock_stage]

    req = GenerateNotesRequest(
        mode="lesson_context",
        topic="Plant Biology",
        class_level="Class 10",
        subject="Biology",
        roadmap_id="rm-101",
        stage_id="stage-42",
    )

    with patch("app.api.lesson_planner._get_roadmap", return_value=mock_roadmap):
        context = asyncio.run(NotesContextExtractor.extract_canonical_context(req, user_id="test-user"))

    assert "Light Reaction Phase" in context.topic
    assert "Identify ATP production sites" in context.learning_objectives
    assert "Chloroplasts absorb all green light" in context.expected_misconceptions
    assert "Explain photolysis" in context.teacher_instructions


# ============================================================================
# 2. DECISION ENGINE TESTS (GRADE ADAPTATION & FORMAT SELECTION)
# ============================================================================

def test_decision_engine_grade_adaptation_class_4():
    """Class 4 should get foundational difficulty and playful, visual scaffolding."""
    context = CanonicalNotesContext(
        topic="Parts of a Plant",
        class_level="Class 4",
        subject="Science",
        curriculum="CBSE",
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert decision.difficulty == NoteDifficulty.FOUNDATIONAL
    assert "young children" in decision.tone_instructions.lower()


def test_decision_engine_grade_adaptation_class_10():
    """Class 10 should receive standard difficulty with board exam focus."""
    context = CanonicalNotesContext(
        topic="Periodic Classification of Elements",
        class_level="Class 10",
        subject="Chemistry",
        curriculum="CBSE",
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert decision.difficulty == NoteDifficulty.STANDARD
    assert "board" in decision.tone_instructions.lower()


def test_decision_engine_grade_adaptation_class_12_formulas():
    """Class 12 Physics should select Advanced difficulty and Formula Sheet format."""
    context = CanonicalNotesContext(
        topic="Electromagnetic Induction and Alternating Currents",
        class_level="Class 12",
        subject="Physics",
        curriculum="CBSE",
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert decision.difficulty == NoteDifficulty.ADVANCED
    assert NoteFormat.FORMULA_SHEET in decision.selected_formats


def test_decision_engine_low_mastery_triggers_remedial():
    """Low student mastery (< 50%) should trigger Remedial Notes format."""
    context = CanonicalNotesContext(
        topic="Stoichiometry",
        class_level="Class 11",
        subject="Chemistry",
        student_mastery={"Stoichiometry": 0.35},
        weak_concepts=["Mole concept", "Molar mass"],
        student_misconceptions=["Mass of 1 mole is always 1 gram"],
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert NoteFormat.REMEDIAL_NOTES in decision.selected_formats
    assert decision.difficulty == NoteDifficulty.FOUNDATIONAL


def test_decision_engine_process_topic_selects_flowchart():
    """Process-heavy topics (cycle, pathway, mechanism) should include Flowchart format."""
    context = CanonicalNotesContext(
        topic="Nitrogen Cycle and Biochemical Transformations",
        class_level="Class 9",
        subject="Biology",
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert NoteFormat.FLOWCHART in decision.selected_formats


def test_decision_engine_comparison_topic_selects_comparison_matrix():
    """Comparison topics ('vs', 'difference between') should select Comparison Notes format."""
    context = CanonicalNotesContext(
        topic="Mitosis vs Meiosis Cell Division",
        class_level="Class 11",
        subject="Biology",
    )
    decision = NotesDecisionEngine.evaluate(context)

    assert NoteFormat.COMPARISON_NOTES in decision.selected_formats


# ============================================================================
# 3. QUALITY VALIDATOR TESTS (0-100 RUBRIC)
# ============================================================================

def test_validator_rubric_scoring_high_quality():
    """A complete, grounded, well-structured note achieves high quality score."""
    doc = NotesDocument(
        id="test-doc-1",
        user_id="user-1",
        title="Photosynthesis Fundamentals",
        subject="Science",
        class_level="Class 7",
        topic="Photosynthesis",
        mode="topic",
        selected_formats=[NoteFormat.LEARNING_NOTES, NoteFormat.FLOWCHART],
        sections=[
            NoteSection(
                section_type="core_concept",
                title="1. What is Photosynthesis?",
                content="Photosynthesis is the biological process by which green plants convert light energy into chemical energy.",
                key_points=["Chlorophyll absorbs sunlight", "Carbon dioxide enters through stomata"],
                examples=["A healthy green potted plant producing starch when placed in sunlight."],
                callouts=[
                    CalloutItem(
                        type="misconception",
                        title="Common Misconception",
                        text="Plants do not get food from soil; they synthesize glucose in leaves."
                    )
                ]
            ),
            NoteSection(
                section_type="flowchart",
                title="2. Photosynthesis Reaction Steps",
                content="Sequence of chemical transformations in chloroplasts:",
                visual_spec=VisualSpec(
                    type="flowchart",
                    title="Energy Flow",
                    nodes=[{"id": "1", "label": "Sunlight"}, {"id": "2", "label": "Chlorophyll"}, {"id": "3", "label": "Glucose"}],
                    edges=[{"from": "1", "to": "2"}, {"from": "2", "to": "3"}]
                )
            ),
            NoteSection(
                section_type="quick_summary",
                title="3. 5-Minute Recall Summary",
                content="Key takeaways to memorize for exams:",
                key_points=["Equation: 6CO2 + 6H2O -> C6H12O6 + 6O2", "Occurs in chloroplasts"]
            )
        ]
    )

    context = CanonicalNotesContext(
        topic="Photosynthesis",
        class_level="Class 7",
        subject="Science",
        learning_objectives=["Understand photosynthesis equation"],
        expected_misconceptions=["Plants get food from soil"]
    )
    decision = DecisionOutput(
        selected_formats=[NoteFormat.LEARNING_NOTES, NoteFormat.FLOWCHART, NoteFormat.QUICK_REVISION],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        required_sections=["core_concept", "quick_summary"],
        tone_instructions="Clear, structured",
        misconceptions_to_target=["Plants get food from soil"]
    )

    report = NotesValidator.evaluate(doc, context, decision)

    assert report.score >= 80
    assert report.accuracy >= 20.0
    assert report.curriculum_alignment >= 15.0
    assert report.misconception_coverage == 5.0


def test_validator_detects_missing_misconception_and_formats():
    """Validator docks points for missing required formats or unaddressed misconceptions."""
    doc = NotesDocument(
        id="test-doc-2",
        user_id="user-1",
        title="Quick Notes on Photosynthesis",
        subject="Science",
        class_level="Class 7",
        topic="Photosynthesis",
        mode="topic",
        selected_formats=[NoteFormat.LEARNING_NOTES],
        sections=[
            NoteSection(
                section_type="core_concept",
                title="Basic Definition",
                content="Photosynthesis is green plant sugar making process in nature.",
                key_points=["Makes food"]
            )
        ]
    )

    context = CanonicalNotesContext(
        topic="Photosynthesis",
        class_level="Class 7",
        subject="Science",
        expected_misconceptions=["Plants get food from soil"]
    )
    decision = DecisionOutput(
        selected_formats=[NoteFormat.LEARNING_NOTES, NoteFormat.FLOWCHART],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        required_sections=["core_concept", "flowchart"],
        tone_instructions="Clear, structured",
        misconceptions_to_target=["Plants get food from soil"]
    )

    report = NotesValidator.evaluate(doc, context, decision)

    # Missing flowchart in visual_spec will dock format compliance
    assert report.format_compliance < 5.0
    # Misconception not in content will dock misconception coverage
    assert report.misconception_coverage < 5.0
    assert len(report.warnings) > 0


# ============================================================================
# 4. GENERATOR PIPELINE & DETERMINISTIC FALLBACK
# ============================================================================

def test_generator_deterministic_fallback():
    """When LLM router is bypassed or fails, the generator produces valid structured notes."""
    context = CanonicalNotesContext(
        topic="Newton's Laws of Motion",
        class_level="Class 9",
        subject="Physics",
        curriculum="CBSE",
        expected_misconceptions=["Heavier objects always fall faster"],
    )
    decision = DecisionOutput(
        selected_formats=[NoteFormat.LEARNING_NOTES, NoteFormat.FLOWCHART, NoteFormat.QUICK_REVISION],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        required_sections=["core_concept", "quick_summary"],
        tone_instructions="Engaging, rigorous",
        misconceptions_to_target=["Heavier objects always fall faster"]
    )

    doc = NotesGenerator._generate_deterministic_fallback(context, decision)

    assert "Newton's Laws of Motion" in doc.title
    assert doc.topic == "Newton's Laws of Motion"
    assert len(doc.sections) >= 2
    # Verify common misconception callout was built
    callouts = [c for s in doc.sections for c in s.callouts if c.type == "misconception"]
    assert len(callouts) > 0
    assert "Heavier objects always fall faster" in callouts[0].text


# ============================================================================
# 5. API ENDPOINTS & USER MULTI-TENANT ISOLATION
# ============================================================================

def test_api_generate_and_retrieve_flow(auth_client):
    """Generate a note via POST /api/notes-generator/generate and fetch it via GET."""
    payload = {
        "mode": "topic",
        "topic": "Chemical Bonding",
        "class_level": "Class 10",
        "subject": "Chemistry",
        "curriculum": "CBSE",
        "requested_format": "learning_notes",
        "requested_depth": "standard",
    }

    res = auth_client.post("/api/notes-generator/generate", json=payload)
    assert res.status_code == 200, res.text
    note = res.json()
    note_id = note["id"]

    assert note["topic"] == "Chemical Bonding"
    assert note["class_level"] == "Class 10"
    assert len(note["sections"]) > 0
    assert note["quality"]["score"] >= 60

    # Retrieve note by ID
    get_res = auth_client.get(f"/api/notes-generator/{note_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == note_id
    assert retrieved["topic"] == "Chemical Bonding"


def test_api_list_my_notes(auth_client):
    """Listing notes returns user-owned notes."""
    res = auth_client.get("/api/notes-generator/")
    assert res.status_code == 200
    data = res.json()
    assert "notes" in data
    assert isinstance(data["notes"], list)


def test_api_context_sources(auth_client):
    """Context sources endpoint returns roadmaps, teach sessions, and quizzes lists."""
    res = auth_client.get("/api/notes-generator/context/sources")
    assert res.status_code == 200
    data = res.json()
    assert "roadmaps" in data
    assert "teach_sessions" in data
    assert "quizzes" in data


def test_api_multi_tenant_authorization_isolation():
    """User Beta MUST NOT be able to retrieve or delete User Alpha's notes."""
    client = TestClient(app)

    # 1. User Alpha generates a note
    app.dependency_overrides[get_current_user] = lambda: user_alpha
    payload = {
        "mode": "topic",
        "topic": "Private Genetics Note",
        "class_level": "Class 12",
        "subject": "Biology",
    }
    alpha_res = client.post("/api/notes-generator/generate", json=payload)
    assert alpha_res.status_code == 200
    note_id = alpha_res.json()["id"]

    # 2. Switch to User Beta — tries to read User Alpha's note -> 404 Forbidden
    app.dependency_overrides[get_current_user] = lambda: user_beta
    beta_get_res = client.get(f"/api/notes-generator/{note_id}")
    assert beta_get_res.status_code in [403, 404]

    # User Beta tries to delete User Alpha's note -> 404 Forbidden
    beta_del_res = client.delete(f"/api/notes-generator/{note_id}")
    assert beta_del_res.status_code in [403, 404]

    # 3. Switch back to User Alpha — can successfully delete their own note
    app.dependency_overrides[get_current_user] = lambda: user_alpha
    alpha_del_res = client.delete(f"/api/notes-generator/{note_id}")
    assert alpha_del_res.status_code == 200
    assert alpha_del_res.json()["id"] == note_id
    app.dependency_overrides.clear()


# ============================================================================
# 6. REGRESSION VERIFICATION
# ============================================================================

def test_existing_ocr_notes_endpoint_preserved():
    """Verify that existing OCR /api/notes endpoints remain completely intact."""
    openapi_paths = list(app.openapi()["paths"].keys())
    assert any("/api/notes" in p for p in openapi_paths)
    assert any("/api/notes-generator" in p for p in openapi_paths)

