"""
LearnByGenie — Feature 1: Learner Intelligence Core Test Suite
Validates canonical student profile, database-driven academic configuration,
role separation, context generation, versioning, validation, backward compatibility,
zero fake mastery, durable database writes, and RLS / backend authorization.
"""

import pytest
import os
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.core.dependencies import get_current_user
from app.services.learner_context.service import LearnerContextService
from app.services.learner_context.repository import LearnerProfileRepository, _MEMORY_STORE
from app.services.learner_context.schemas import LearnerProfileUpdate
from app.services.learner_context.academic_catalog import (
    EDUCATION_LEVELS,
    CURRICULA,
    EXAM_TRACKS,
    EducationStage,
    get_academic_config_payload
)
from app.db.supabase_client import supabase

# Real authenticated user IDs present in production/staging auth.users table
REAL_STUDENT_ALPHA = "a56da972-0f19-418d-b0f7-de91ff114190"
REAL_STUDENT_BETA = "d7007dd2-57dd-477c-9429-629d620cd616"
REAL_TEACHER = "6ca14719-b196-427f-8c3d-fc42a81d7e8b"


class MockAuthUser:
    def __init__(self, user_id: str = REAL_STUDENT_ALPHA, email: str = "student@learnbygenie.com", role: str = "student"):
        self.id = user_id
        self.email = email
        self.app_metadata = {"role": role}
        self.user_metadata = {"full_name": f"User {user_id}", "role": role}


@pytest.fixture(autouse=True)
def clean_memory_store():
    """Isolate memory cache for every test run."""
    LearnerProfileRepository.clear_memory_cache()
    yield
    LearnerProfileRepository.clear_memory_cache()


# ─── 1 & 2. Profile Creation & Retrieval ──────────────────────────────────────

def test_student_profile_creation_and_retrieval():
    """Verify that a student profile can be created with initial version 1 and retrieved."""
    student_id = REAL_STUDENT_ALPHA
    mock_user = MockAuthUser(student_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Initial retrieval of user returns safe default with version 1
        res = client.get("/api/learner/profile")
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == student_id
        assert "completeness" in data
        assert isinstance(data["subjects"], list)

        # Profile submission with authoritative persistence
        update_payload = {
            "education_level": "class_11",
            "board_or_curriculum": "CBSE",
            "academic_stream": "science_pcm",
            "target_exam": "JEE",
            "target_year": datetime.now().year + 1,
            "subjects": ["Physics", "Chemistry", "Mathematics"],
            "preferred_language": "hinglish",
            "short_term_goal": "Master Kinematics and revise mechanics",
            "long_term_goal": "Top rank in JEE Advanced",
            "preferred_session_minutes": 45,
            "weekly_study_availability_hours": 15.0,
            "onboarding_completed": True
        }
        create_res = client.patch("/api/learner/profile", json=update_payload)
        assert create_res.status_code == 200
        created_data = create_res.json()
        assert created_data["education_level"] == "class_11"
        assert created_data["grade_or_class"] == "Class 11"
        assert created_data["education_stage"] == "SENIOR_SECONDARY"
        assert created_data["target_exam"] == "JEE"
        assert created_data["preferred_language"] == "hinglish"
        assert created_data["preferred_session_minutes"] == 45
        assert created_data["completeness"]["is_complete"] is True
        assert created_data["completeness"]["status"] == "Profile ready"

    app.dependency_overrides.clear()


# ─── 3 & 12. Profile Update & Deterministic Version Increment ────────────────

def test_profile_update_and_version_increment():
    """Verify that updates increment profile_version deterministically."""
    student_id = REAL_STUDENT_ALPHA
    mock_user = MockAuthUser(student_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # First update
        r1 = client.patch("/api/learner/profile", json={"preferred_language": "hi"})
        assert r1.status_code == 200
        v1 = r1.json()["profile_version"]
        assert r1.json()["preferred_language"] == "hi"

        # Second update (e.g. changing target exam from JEE to BOARDS without erasing history)
        r2 = client.patch("/api/learner/profile", json={"target_exam": "BOARDS"})
        assert r2.status_code == 200
        assert r2.json()["profile_version"] == v1 + 1
        assert r2.json()["target_exam"] == "BOARDS"
        # Language should still be preserved
        assert r2.json()["preferred_language"] == "hi"

        # Third update
        r3 = client.patch("/api/learner/profile", json={"preferred_session_minutes": 45})
        assert r3.status_code == 200
        assert r3.json()["profile_version"] == v1 + 2

    app.dependency_overrides.clear()


# ─── 4 & 5. Profile Ownership & Cross-User Isolation ─────────────────────────

def test_profile_ownership_and_cross_user_isolation():
    """Verify that User A and User B have strictly isolated profiles and cannot alter each other's state."""
    user_a = MockAuthUser(REAL_STUDENT_ALPHA, email="alice@test.com")
    user_b = MockAuthUser(REAL_STUDENT_BETA, email="bob@test.com")

    # User A sets Class 10 CBSE
    app.dependency_overrides[get_current_user] = lambda: user_a
    with TestClient(app) as client:
        client.patch("/api/learner/profile", json={
            "education_level": "class_10",
            "board_or_curriculum": "CBSE",
            "target_exam": "BOARDS",
            "preferred_language": "en"
        })
        prof_a = client.get("/api/learner/profile").json()
        assert prof_a["user_id"] == REAL_STUDENT_ALPHA
        assert prof_a["education_level"] == "class_10"
        assert prof_a["preferred_language"] == "en"

    # User B logs in — must see their own distinct profile, completely independent of User A
    app.dependency_overrides[get_current_user] = lambda: user_b
    with TestClient(app) as client:
        prof_b = client.get("/api/learner/profile").json()
        assert prof_b["user_id"] == REAL_STUDENT_BETA

        # User B updates their language to Hindi
        client.patch("/api/learner/profile", json={"preferred_language": "hi"})
        prof_b_updated = client.get("/api/learner/profile").json()
        assert prof_b_updated["preferred_language"] == "hi"

    # Re-verify User A is untouched
    app.dependency_overrides[get_current_user] = lambda: user_a
    with TestClient(app) as client:
        prof_a_recheck = client.get("/api/learner/profile").json()
        assert prof_a_recheck["user_id"] == REAL_STUDENT_ALPHA
        assert prof_a_recheck["education_level"] == "class_10"
        assert prof_a_recheck["preferred_language"] == "en"

    app.dependency_overrides.clear()


# ─── 6. Role Separation (Student vs Teacher vs Admin) ─────────────────────────

def test_teacher_student_role_handling():
    """Verify that teachers and students have their roles properly reflected in context."""
    teacher_user = MockAuthUser(REAL_TEACHER, email="teacher@learnbygenie.com", role="teacher")
    app.dependency_overrides[get_current_user] = lambda: teacher_user

    with TestClient(app) as client:
        ctx_res = client.get("/api/learner/context")
        assert ctx_res.status_code == 200
        ctx = ctx_res.json()
        assert ctx["role"] == "teacher"
        assert ctx["student_id"] == REAL_TEACHER

    student_user = MockAuthUser(REAL_STUDENT_ALPHA, email="student@learnbygenie.com", role="student")
    app.dependency_overrides[get_current_user] = lambda: student_user

    with TestClient(app) as client:
        ctx_res = client.get("/api/learner/context")
        assert ctx_res.status_code == 200
        ctx = ctx_res.json()
        assert ctx["role"] == "student"

    app.dependency_overrides.clear()


# ─── 7. Academic Configuration Retrieval (Database-Driven) ────────────────────

def test_academic_config_retrieval():
    """Verify that /api/learner/academic-config returns all canonical academic records."""
    with TestClient(app) as client:
        res = client.get("/api/learner/academic-config")
        assert res.status_code == 200
        data = res.json()
        
        # Verify education levels
        level_ids = [l["id"] for l in data["education_levels"]]
        assert "class_3" in level_ids
        assert "class_8" in level_ids
        assert "class_10" in level_ids
        assert "class_11" in level_ids
        assert "class_12" in level_ids
        assert "ug_year_1" in level_ids

        # Verify curricula
        curricula_ids = [c["id"] for c in data["curricula"]]
        assert "CBSE" in curricula_ids
        assert "ICSE_ISC" in curricula_ids
        assert "STATE_BOARD" in curricula_ids

        # Verify exam tracks
        exam_ids = [e["id"] for e in data["exam_tracks"]]
        assert "JEE" in exam_ids
        assert "NEET" in exam_ids
        assert "BOARDS" in exam_ids

        # Verify languages
        lang_ids = [lng["id"] for lng in data["languages"]]
        assert "hinglish" in lang_ids
        assert "en" in lang_ids
        assert "hi" in lang_ids


# ─── 8. Invalid Subject Rejection ─────────────────────────────────────────────

def test_invalid_subject_rejection():
    """Verify backend rejects empty subject arrays."""
    mock_user = MockAuthUser(REAL_STUDENT_ALPHA)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        res = client.patch("/api/learner/profile", json={"subjects": []})
        assert res.status_code == 400
        assert "valid subject" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


# ─── 9. Invalid Exam Combination Handling ─────────────────────────────────────

def test_invalid_exam_combination_handling():
    """Verify that assigning high-school entrance exams (JEE/NEET) to Primary school is rejected."""
    mock_user = MockAuthUser(REAL_STUDENT_ALPHA)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Class 3 cannot prepare for JEE
        res = client.patch("/api/learner/profile", json={
            "education_level": "class_3",
            "target_exam": "JEE"
        })
        assert res.status_code == 400
        assert "only available for senior secondary" in res.json()["detail"].lower()

        # Class 4 cannot prepare for NEET
        res_neet = client.patch("/api/learner/profile", json={
            "education_level": "class_4",
            "target_exam": "NEET"
        })
        assert res_neet.status_code == 400

        # Class 11 CAN prepare for JEE
        res_valid = client.patch("/api/learner/profile", json={
            "education_level": "class_11",
            "target_exam": "JEE"
        })
        assert res_valid.status_code == 200

    app.dependency_overrides.clear()


# ─── 10. Language Preference ──────────────────────────────────────────────────

def test_language_preference_selection_and_validation():
    """Verify that supported language preferences (Hinglish, Hindi, English, regional) are accepted and invalid codes rejected."""
    mock_user = MockAuthUser(REAL_STUDENT_ALPHA)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        for valid_lang in ["hinglish", "en", "hi", "bn", "ta"]:
            res = client.patch("/api/learner/profile", json={"preferred_language": valid_lang})
            assert res.status_code == 200
            assert res.json()["preferred_language"] == valid_lang

        # Reject unsupported arbitrary language code
        bad_res = client.patch("/api/learner/profile", json={"preferred_language": "klingon_xyz"})
        assert bad_res.status_code == 400
        assert "invalid language" in bad_res.json()["detail"].lower()

    app.dependency_overrides.clear()


# ─── 11. Target Year Validation ───────────────────────────────────────────────

def test_target_year_validation():
    """Verify that unrealistic target years are rejected."""
    mock_user = MockAuthUser(REAL_STUDENT_ALPHA)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Year in distant past
        res_past = client.patch("/api/learner/profile", json={"target_year": 1995})
        assert res_past.status_code == 400
        assert "target year" in res_past.json()["detail"].lower()

        # Year in distant future
        res_future = client.patch("/api/learner/profile", json={"target_year": 2085})
        assert res_future.status_code == 400
        assert "target year" in res_future.json()["detail"].lower()

        # Realistic year
        valid_year = datetime.now().year + 2
        res_valid = client.patch("/api/learner/profile", json={"target_year": valid_year})
        assert res_valid.status_code == 200
        assert res_valid.json()["target_year"] == valid_year

    app.dependency_overrides.clear()


# ─── 13 & 14. Profile Absent Fallback & Existing User Compatibility ──────────

def test_profile_absent_fallback_and_existing_user_compatibility():
    """Verify existing users without a profile record get safe defaults without crashes or 404."""
    existing_user_id = "00000000-0000-0000-0000-000000009999"
    mock_user = MockAuthUser(existing_user_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Profile endpoint must return 200 with safe defaults
        prof_res = client.get("/api/learner/profile")
        assert prof_res.status_code == 200
        prof = prof_res.json()
        assert prof["user_id"] == existing_user_id
        assert prof["onboarding_completed"] is False
        assert prof["education_level"] == "class_11"

        # Context endpoint must also succeed without throwing
        ctx_res = client.get("/api/learner/context")
        assert ctx_res.status_code == 200
        ctx = ctx_res.json()
        assert ctx["student_id"] == existing_user_id
        assert ctx["profile_completeness"]["is_complete"] is False

    app.dependency_overrides.clear()


# ─── 15, 16. Learner Context Generation & NO Fake Mastery ─────────────────────

def test_learner_context_generation_and_no_fake_mastery():
    """Verify canonical LearnerContext structure and ensure ZERO fabricated mastery or pseudo-psychology fields."""
    student_id = REAL_STUDENT_ALPHA
    mock_user = MockAuthUser(student_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Save a known state
        client.patch("/api/learner/profile", json={
            "education_level": "class_12",
            "board_or_curriculum": "CBSE",
            "academic_stream": "science_pcb",
            "target_exam": "NEET",
            "subjects": ["Physics", "Chemistry", "Biology"],
            "preferred_language": "hinglish",
            "preferred_session_minutes": 30
        })

        res = client.get("/api/learner/context")
        assert res.status_code == 200
        ctx = res.json()

        # Validate canonical schema structure
        assert ctx["student_id"] == student_id
        assert ctx["education"]["level"] == "Class 12"
        assert ctx["education"]["stage"] == "SENIOR_SECONDARY"
        assert ctx["education"]["stream"] == "science_pcb"
        assert "NEET" in ctx["education"]["exam_tracks"]
        assert ctx["subjects"] == ["Physics", "Chemistry", "Biology"]
        assert ctx["preferences"]["explanation_language"] == "hinglish"
        assert ctx["preferences"]["preferred_session_minutes"] == 30

        # CRITICAL VERIFICATION: No fabricated mastery fields
        raw_keys = set(ctx.keys())
        for forbidden in ["mastery_score", "mastery_percentage", "predicted_rank", "weak_topics", "iq_score", "learning_style"]:
            assert forbidden not in raw_keys, f"Forbidden fake mastery field '{forbidden}' found in context!"

        # Ensure learning activity summary contains only factual counters
        activity = ctx["learning_activity_summary"]
        assert "total_documents" in activity
        assert "total_quiz_attempts" in activity

    app.dependency_overrides.clear()


# ─── 17. Authorization & Tenant Isolation ─────────────────────────────────────

def test_unauthenticated_request_rejected():
    """Verify that unauthenticated calls to learner profile and context endpoints return 401/403."""
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        res1 = client.get("/api/learner/profile")
        assert res1.status_code in (401, 403)

        res2 = client.patch("/api/learner/profile", json={"preferred_language": "hi"})
        assert res2.status_code in (401, 403)

        res3 = client.get("/api/learner/context")
        assert res3.status_code in (401, 403)


# ─── Class 3 to 12 & Undergraduate Extensibility ──────────────────────────────

def test_class_3_to_12_and_undergraduate_coverage():
    """Verify coverage of Class 3 to 12 and Undergraduate support."""
    classes = [f"class_{i}" for i in range(3, 13)]
    config_levels = {lvl["id"]: lvl for lvl in EDUCATION_LEVELS}

    for c in classes:
        assert c in config_levels, f"Missing level {c} in configuration"
        stage = config_levels[c]["stage"]
        assert stage in [EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY, EducationStage.SENIOR_SECONDARY]

    # Undergraduate verification
    for yr in [1, 2, 3, 4]:
        ug_key = f"ug_year_{yr}"
        assert ug_key in config_levels
        assert config_levels[ug_key]["stage"] == EducationStage.UNDERGRADUATE


# ─── AI Prompt Adapter Formatting Helper ──────────────────────────────────────

def test_prompt_context_formatting_adapter():
    """Verify that LearnerContextService.format_learner_prompt_context generates a clean, non-intrusive instruction."""
    ctx_data = {
        "education": {
            "level": "Class 11",
            "board": "CBSE",
            "stream": "science_pcm",
        },
        "goals": {
            "primary": "JEE",
            "target_year": 2027
        },
        "subjects": ["Physics", "Chemistry", "Mathematics"],
        "preferences": {
            "explanation_language": "Hinglish",
            "content_difficulty": "standard"
        }
    }
    prompt_str = LearnerContextService.format_learner_prompt_context(ctx_data)
    assert "Class 11 (CBSE)" in prompt_str
    assert "Target: JEE 2027" in prompt_str
    assert "Physics, Chemistry, Mathematics" in prompt_str
    assert "Explanation Language: Hinglish" in prompt_str
    assert "Content Difficulty: standard" in prompt_str


# ─── PRODUCTION CLOSURE REQUIREMENT TESTS ─────────────────────────────────────

def test_durable_profile_writes_and_no_in_memory_false_success(monkeypatch):
    """
    CRITICAL REQUIREMENT 2:
    A profile write must NOT pretend persistence succeeded using only process memory.
    If database storage is unavailable, CREATE/PATCH must fail explicitly with HTTP 503
    LEARNER_PROFILE_STORAGE_UNAVAILABLE.
    """
    import app.services.learner_context.repository as repo_mod

    mock_user = MockAuthUser(REAL_STUDENT_ALPHA)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Simulate database outage by setting supabase client to None
    monkeypatch.setattr(repo_mod, "supabase", None)

    with TestClient(app) as client:
        patch_res = client.patch("/api/learner/profile", json={"preferred_language": "hi"})
        assert patch_res.status_code == 503
        assert "LEARNER_PROFILE_STORAGE_UNAVAILABLE" in patch_res.json()["detail"]

        # Verify that memory cache was NOT modified with false success
        assert REAL_STUDENT_ALPHA not in _MEMORY_STORE

    app.dependency_overrides.clear()


def test_profile_restart_persistence_from_authoritative_database():
    """
    CRITICAL REQUIREMENT 3:
    Data written to the canonical profile must survive process memory purge (backend restart)
    and reload directly from real Supabase PostgreSQL.
    """
    student_id = REAL_STUDENT_ALPHA
    mock_user = MockAuthUser(student_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # 1. Update profile with unique parameters
        patch_res = client.patch("/api/learner/profile", json={
            "preferred_language": "hi",
            "target_exam": "JEE",
            "preferred_session_minutes": 45
        })
        assert patch_res.status_code == 200
        saved_ver = patch_res.json()["profile_version"]
        saved_lang = patch_res.json()["preferred_language"]
        saved_mins = patch_res.json()["preferred_session_minutes"]

        # 2. Simulate complete Render restart: Purge in-memory cache
        LearnerProfileRepository.clear_memory_cache()
        assert REAL_STUDENT_ALPHA not in _MEMORY_STORE

        # 3. GET profile after restart: Must read directly from real PostgreSQL table
        get_res = client.get("/api/learner/profile")
        assert get_res.status_code == 200
        reloaded = get_res.json()
        assert reloaded["preferred_language"] == saved_lang == "hi"
        assert reloaded["target_exam"] == "JEE"
        assert reloaded["preferred_session_minutes"] == saved_mins == 45
        assert reloaded["profile_version"] == saved_ver

    app.dependency_overrides.clear()


def test_legacy_profile_exam_target_synchronization():
    """
    CRITICAL REQUIREMENT 7:
    Verify that updating learner_profiles.target_exam keeps public.profiles.exam_target synchronized.
    """
    student_id = REAL_STUDENT_ALPHA
    mock_user = MockAuthUser(student_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        patch_res = client.patch("/api/learner/profile", json={"target_exam": "JEE"})
        assert patch_res.status_code == 200

        # Query real profiles table to confirm legacy sync
        prof_row = supabase.table("profiles").select("exam_target").eq("id", student_id).execute()
        assert prof_row.data[0]["exam_target"] == "JEE"

    app.dependency_overrides.clear()


def test_real_academic_catalog_from_supabase():
    """
    CRITICAL REQUIREMENT 5:
    Read academic configuration from real database and verify required entities.
    """
    with TestClient(app) as client:
        res = client.get("/api/learner/academic-config")
        assert res.status_code == 200
        data = res.json()

        # Levels
        level_ids = [l["id"] for l in data["education_levels"]]
        for required_level in ["class_3", "class_8", "class_10", "class_11", "class_12", "ug_year_1"]:
            assert required_level in level_ids

        # Curricula
        cur_ids = [c["id"] for c in data["curricula"]]
        assert "CBSE" in cur_ids
        assert "ICSE_ISC" in cur_ids

        # Exams
        exam_ids = [e["id"] for e in data["exam_tracks"]]
        assert "JEE" in exam_ids
        assert "NEET" in exam_ids
        assert "BOARDS" in exam_ids


def test_database_rls_blocks_anon_client():
    """
    CRITICAL REQUIREMENT 4:
    Verify database-level Row Level Security (RLS) blocks anon/unauthenticated clients
    from querying learner_profiles table.
    """
    from supabase import create_client
    from app.core.config import settings
    from pathlib import Path
    from dotenv import dotenv_values
    root_env = Path(__file__).resolve().parents[2] / ".env"
    envs = dotenv_values(root_env) if root_env.exists() else {}
    anon_key = envs.get("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")

    anon_client = create_client(settings.SUPABASE_URL, anon_key)
    res = anon_client.table("learner_profiles").select("*").execute()
    # RLS must yield 0 rows to unauthenticated/anon callers
    assert len(res.data) == 0
