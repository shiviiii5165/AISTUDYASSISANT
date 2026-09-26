"""
LearnByGenie Notes Context Engine — Comprehensive Test Suite
==========================================================
Verifies all Step 1 architectural requirements:
1. Topic Only (Minimum viable context)
2. Explicit Class Overrides Student Profile (Conflict tracking)
3. Lesson Overrides Curriculum Conflict (Priority ordering)
4. Missing Quiz Graceful Degradation (Honest missing context)
5. Mastery Normalization (Decimal clamping)
6. Topic Normalization (Preserving rawTopic and normalizedTopic)
7. Provenance Tracking (Field-level source and confidence)
8. Conflict Preservation (Structured conflict records)
9. Snapshot Stability (Immutability guarantee)
10. Combined Multi-Source Context (Complete safe aggregation)
11. Realistic Integration Scenario (Class 7 CBSE Science Photosynthesis)
"""
import pytest
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user
from app.services.notes.context import (
    NotesContextAnalyzer,
    AnalyzeContextRequest,
    AnalyzeContextResponse,
    CanonicalNotesContext,
    ContextSnapshotManager,
    ContextNormalizer,
    NotesContextSource,
    ContextResolutionStatus,
)


class MockAuthUser:
    def __init__(self, user_id: str = "usr-context-tester-1"):
        self.id = user_id
        self.email = "tester@teachgenie.ai"


@pytest.fixture
def test_client():
    mock_u = MockAuthUser()
    app.dependency_overrides[get_current_user] = lambda: mock_u
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# UNIT TESTS 1 TO 10
# ============================================================================

def test_1_topic_only_mode():
    """
    TEST 1: Pure topic input (minimum viable context).
    Topic is resolved, optional context is marked unknown/unavailable.
    No assumptions fabricated (e.g. curriculum is None, mastery is empty).
    """
    req = AnalyzeContextRequest(
        topic="Photosynthesis"
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    assert ctx.resolved_context.topic == "Photosynthesis"
    assert ctx.resolved_context.raw_topic == "Photosynthesis"
    assert ctx.resolved_context.curriculum is None  # Honest: NEVER assumes CBSE
    assert ctx.resolved_context.mastery_state == {}  # Honest: NEVER assumes 50%
    assert ctx.resolved_context.teaching_method == "unknown"  # Honest: NEVER assumes passive
    assert ctx.completeness.score == 47.5  # 30 (topic) + 7.5 (General subject) + 10 (English)
    assert "curriculum" in ctx.completeness.missing_fields
    assert "class_level" in ctx.completeness.missing_fields


def test_2_explicit_class_overrides_student_profile():
    """
    TEST 2: Explicit classLevel takes precedence over student profile classLevel.
    Conflict is preserved in structured metadata, NOT silently deleted.
    """
    req = AnalyzeContextRequest(
        topic="Motion",
        class_level="9",
        student={
            "studentId": "stu-101",
            "classLevel": "8",
            "grade": 8
        }
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    # Priority 1 (explicit) overrides Priority 4 (student)
    assert ctx.resolved_context.class_level == "Class 9"
    assert ctx.resolved_context.grade == 9

    # Conflict must be recorded
    conflicts = ctx.provenance.conflicts
    class_conflicts = [c for c in conflicts if c.field == "class_level"]
    assert len(class_conflicts) == 1
    c = class_conflicts[0]
    assert c.resolved_value == "Class 9"
    assert c.resolved_from == "explicit_input"
    assert any(v["source"] == "student" for v in c.values)
    assert any(v["source"] == "explicit_input" for v in c.values)


def test_3_lesson_overrides_curriculum_conflict():
    """
    TEST 3: Lesson stage context (Priority 2) overrides curriculum record (Priority 3).
    """
    req = AnalyzeContextRequest(
        topic="Thermodynamics",
        lesson={
            "roadmapId": "rm-1",
            "stageId": "st-1",
            "stageTitle": "Physics: First Law of Thermodynamics",
            "teachingMethod": "inquiry"
        },
        curriculum_data={
            "board": "CBSE",
            "subject": "Science",
            "grade": 11
        }
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    assert ctx.resolved_context.subject == "Physics"
    assert ctx.resolved_context.teaching_method == "inquiry"
    assert ctx.provenance.field_sources["subject"].source == NotesContextSource.LESSON
    assert ctx.provenance.field_sources["subject"].priority == 2


def test_4_missing_quiz_graceful():
    """
    TEST 4: Quiz context missing or unavailable.
    Request succeeds gracefully, assessment.status is marked unavailable/unknown.
    Zero quiz information fabricated.
    """
    req = AnalyzeContextRequest(
        topic="Cell Division",
        context={"quizId": "quiz_nonexistent_xyz"}
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    assert ctx.assessment.status == "unavailable"
    assert ctx.assessment.mastery == {}
    assert ctx.assessment.latest_score is None
    assert "assessment.quiz" in ctx.completeness.missing_fields
    assert "Assessment context unavailable" in ctx.completeness.warnings


def test_5_mastery_normalization():
    """
    TEST 5: Mastery values in percentages or numbers normalize to 0.0-1.0 decimals.
    """
    assert ContextNormalizer.normalize_mastery("73%") == 0.73
    assert ContextNormalizer.normalize_mastery(73) == 0.73
    assert ContextNormalizer.normalize_mastery(0.73) == 0.73
    assert ContextNormalizer.normalize_mastery("0.45") == 0.45
    assert ContextNormalizer.normalize_mastery(None) is None

    req = AnalyzeContextRequest(
        topic="Circuits",
        assessment={
            "quizId": "q1",
            "score": "84%",
            "mastery": {
                "ohms_law": "73%",
                "resistance": 45,
                "power": 0.90
            }
        }
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    assert ctx.resolved_context.mastery_state["ohms_law"] == 0.73
    assert ctx.resolved_context.mastery_state["resistance"] == 0.45
    assert ctx.resolved_context.mastery_state["power"] == 0.90
    assert ctx.assessment.latest_score == 0.84


def test_6_topic_normalization():
    """
    TEST 6: Topic strings are lightly normalized while preserving raw topic.
    """
    raw_in = "newton's laws of motion"
    raw_out, norm_out = ContextNormalizer.normalize_topic(raw_in)
    assert raw_out == "newton's laws of motion"
    assert norm_out == "Newton's Laws of Motion"

    req = AnalyzeContextRequest(topic="newton's laws of motion")
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))
    assert ctx.resolved_context.raw_topic == "newton's laws of motion"
    assert ctx.resolved_context.topic == "Newton's Laws of Motion"


def test_7_provenance_tracking():
    """
    TEST 7: Every resolved important field can answer: Where did this value come from?
    """
    req = AnalyzeContextRequest(
        topic="Gravity",
        class_level="Class 9",
        subject="Physics",
        curriculum="CBSE",
        language="English"
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    prov = ctx.provenance.field_sources
    for required_field in ["topic", "class_level", "subject", "curriculum", "language", "teaching_method"]:
        assert required_field in prov
        p = prov[required_field]
        assert p.priority >= 1
        assert 0.0 <= p.confidence <= 1.0
        assert p.status in [ContextResolutionStatus.RESOLVED, ContextResolutionStatus.UNKNOWN]

    # Explicit input has Priority 1 and Confidence 1.0
    assert prov["class_level"].priority == 1
    assert prov["class_level"].confidence == 1.0
    assert prov["class_level"].source == NotesContextSource.EXPLICIT_INPUT


def test_8_conflict_tracking():
    """
    TEST 8: Preserves conflicting candidate values in structured format.
    """
    req = AnalyzeContextRequest(
        topic="Photosynthesis",
        class_level="Class 9",
        student={
            "studentId": "stu-1",
            "classLevel": "Class 8"
        },
        curriculum_data={
            "board": "ICSE",
            "subject": "Biology",
            "grade": 7
        }
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    conflicts = ctx.provenance.conflicts
    field_names = [c.field for c in conflicts]
    assert "class_level" in field_names

    class_c = next(c for c in conflicts if c.field == "class_level")
    assert class_c.resolved_value == "Class 9"
    assert len(class_c.values) >= 2
    sources_in_conflict = [v["source"] for v in class_c.values]
    assert "explicit_input" in sources_in_conflict
    assert "student" in sources_in_conflict


def test_9_snapshot_stability():
    """
    TEST 9: Changing student state or mutable objects after snapshot creation
    leaves the historical context snapshot unchanged.
    """
    student_state = {
        "studentId": "stu-history",
        "currentLearningState": {
            "mastery": {"algebra": 0.35}
        }
    }
    req = AnalyzeContextRequest(
        topic="Algebraic Expressions",
        student=student_state
    )

    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))
    snapshot_1 = ContextSnapshotManager.create_snapshot(ctx, user_id="u1")
    snapshot_id = snapshot_1.snapshot_id

    # Mutate the source dictionary after snapshot creation
    student_state["currentLearningState"]["mastery"]["algebra"] = 0.95

    # Retrieve snapshot and verify historical immutability
    retrieved = ContextSnapshotManager.get_snapshot(snapshot_id)
    assert retrieved is not None
    assert retrieved.context.resolved_context.mastery_state["algebra"] == 0.35
    assert retrieved.context.resolved_context.mastery_state["algebra"] != 0.95


def test_10_combined_context():
    """
    TEST 10: Combines all six sources simultaneously:
    Topic + Student + Curriculum + Lesson + Quiz + TeachMe + PPT.
    Safe merge without crash or data loss.
    """
    req = AnalyzeContextRequest(
        topic="Newton's Laws of Motion",
        class_level="Class 9",
        subject="Physics",
        curriculum="CBSE",
        language="English",
        student={
            "studentId": "s-100",
            "ageGroup": "14-15",
            "learningPreferences": ["visual", "step-by-step"]
        },
        curriculum_data={
            "board": "CBSE",
            "subject": "Science",
            "grade": 9,
            "chapter": "Force and Laws of Motion"
        },
        lesson={
            "roadmapId": "rm-10",
            "stageId": "st-2",
            "stageTitle": "Newton's Second Law of Motion",
            "learningObjectives": ["Derive F = ma", "Calculate net force"],
            "activities": ["LAB: Spring balance experiment"],
            "teachingMethod": "active"
        },
        assessment={
            "quizId": "quiz-90",
            "score": 0.58,
            "weakConcepts": ["inertia", "momentum"],
            "mastery": {"inertia": 0.40, "second_law": 0.75}
        },
        teach_me={
            "sessionId": "tm-session-88",
            "misconceptions": ["Heavier objects fall faster due to inertia"],
            "confusedConcepts": ["momentum"]
        },
        ppt={
            "deckId": "deck-44",
            "slideCount": 10,
            "slideTopics": ["Newton's Second Law", "Momentum", "F=ma Derivation"],
            "keyPoints": ["Rate of change of momentum is proportional to force"]
        }
    )

    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="u1"))

    # Verify resolved outputs
    assert ctx.resolved_context.topic == "Newton's Laws of Motion"
    assert ctx.resolved_context.class_level == "Class 9"
    assert ctx.resolved_context.subject == "Physics"
    assert ctx.resolved_context.curriculum == "CBSE"
    assert ctx.resolved_context.teaching_method == "active"

    # Verify merged pedagogical signals
    assert "inertia" in ctx.resolved_context.weak_concepts
    assert "momentum" in ctx.resolved_context.weak_concepts
    assert "Heavier objects fall faster due to inertia" in ctx.resolved_context.misconceptions
    assert ctx.resolved_context.mastery_state["inertia"] == 0.40

    # Verify high completeness score
    assert ctx.completeness.score >= 90.0


# ============================================================================
# INTEGRATION TEST (REALISTIC SCENARIO)
# ============================================================================

def test_realistic_integration_scenario(test_client):
    """
    INTEGRATION TEST: Class 7 CBSE Science Photosynthesis scenario.
    Tests end-to-end API execution at POST /api/notes-generator/context/analyze.
    Verifies CanonicalNotesContext packaging without calling Decision Engine or generating notes.
    """
    payload = {
        "topic": "Photosynthesis",
        "class_level": "Class 7",
        "subject": "Science",
        "curriculum": "CBSE",
        "language": "English",
        "student": {
            "studentId": "student-701",
            "ageGroup": "12-13",
            "currentLearningState": {
                "mastery": {"chloroplast": 0.45, "stomata": 0.70}
            }
        },
        "curriculumData": {
            "board": "CBSE",
            "subject": "Science",
            "grade": 7,
            "chapter": "Nutrition in Plants"
        },
        "lesson": {
            "roadmapId": "rm-bio-7",
            "stageId": "st-photo-1",
            "stageTitle": "Photosynthesis Process & Conditions",
            "stageObjective": "Explain photosynthesis process in green leaves",
            "learningObjectives": ["Explain photosynthesis", "Identify role of chlorophyll"],
            "activities": ["EXPERIMENT: Starch test in leaves"],
            "teachingMethod": "active inquiry"
        },
        "assessment": {
            "quizId": "quiz-bio-62",
            "score": 0.62,
            "weakConcepts": ["chlorophyll"],
            "mastery": {"chlorophyll": 0.40, "light_reaction": 0.65}
        },
        "teachMe": {
            "sessionId": "tm-session-plants",
            "misconceptions": ["Plants get food directly from soil."]
        },
        "ppt": {
            "deckId": "deck-photo-7",
            "slideCount": 8,
            "slideTopics": ["Photosynthesis Process", "Sunlight", "Chlorophyll", "CO2", "Water"]
        }
    }

    response = test_client.post("/api/notes-generator/context/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "snapshot_id" in data
    assert data["snapshot_id"].startswith("notes_ctx_")

    ctx = data["context"]
    assert ctx["context_schema_version"] == "1.0"

    # Resolved Context checks
    resolved = ctx["resolved_context"]
    assert resolved["topic"] == "Photosynthesis"
    assert resolved["class_level"] == "Class 7"
    assert resolved["subject"] == "Science"
    assert resolved["curriculum"] == "CBSE"
    assert resolved["teaching_method"] == "active inquiry"
    assert "chlorophyll" in resolved["weak_concepts"]
    assert "Plants get food directly from soil." in resolved["misconceptions"]

    # Provenance checks
    prov = ctx["provenance"]
    assert prov["confidence"] > 0.80
    assert "class_level" in prov["field_sources"]
    assert prov["field_sources"]["class_level"]["source"] == "explicit_input"

    # Completeness checks
    comp = ctx["completeness"]
    assert comp["score"] >= 95.0

    # NON-NEGOTIABLE BOUNDARY: No decision engine or generated notes in response
    assert "selected_formats" not in data
    assert "sections" not in data
    assert "generated_notes" not in data
