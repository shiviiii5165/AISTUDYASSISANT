import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime

from app.main import app
from app.core.dependencies import get_current_user, AuthenticatedUser
from app.services.gamification.service import GamificationService
from app.services.gamification.repository import GamificationRepository
from app.services.gamification.schemas import XPReasonCode, AwardXPRequest
from app.services.spaced_repetition.service import SpacedRepetitionService
from app.services.spaced_repetition.repository import SpacedRepetitionRepository
from app.services.spaced_repetition.schemas import ReviewSubmissionRequest
from app.services.portals.service import (
    ParentPortalService,
    TeacherPortalService,
    SchoolAdminPortalService,
    ContentCreatorPortalService,
    SuperAdminPortalService
)
from app.services.portals.repository import PortalsRepository

PARENT_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000077",
    email="parent@learnbygenie.com",
    role="parent",
    full_name="Parent Rajesh"
)

TEACHER_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000001",
    email="teacher@learnbygenie.com",
    role="teacher",
    full_name="Teacher Jane"
)

SCHOOL_ADMIN_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000088",
    email="principal@dps.edu",
    role="school_admin",
    full_name="Principal Sharma"
)

CONTENT_CREATOR_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000066",
    email="creator@learnbygenie.com",
    role="content_creator",
    full_name="Creator Sarah"
)

SUPER_ADMIN_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000099",
    email="admin@learnbygenie.com",
    role="super_admin",
    full_name="Super Admin"
)

STUDENT_USER = AuthenticatedUser(
    id="a56da972-0f19-418d-b0f7-de91ff114190",
    email="student@learnbygenie.com",
    role="student",
    full_name="Student Arjun"
)


@pytest.fixture(autouse=True)
def clean_state():
    GamificationRepository.clear_memory_cache()
    SpacedRepetitionRepository.clear_memory_cache()
    PortalsRepository.clear_memory_cache()
    yield
    GamificationRepository.clear_memory_cache()
    SpacedRepetitionRepository.clear_memory_cache()
    PortalsRepository.clear_memory_cache()


# ─── 1. GAMIFICATION & XP LEDGER TESTS ────────────────────────────────────────

def test_xp_award_and_duplicate_idempotency():
    """Verify that XP transactions are recorded and duplicate idempotency keys prevent duplicate awards."""
    uid = STUDENT_USER.id
    tx1, is_new1 = GamificationService.award_xp(
        user_id=uid,
        amount=50,
        reason_code=XPReasonCode.DIAGNOSTIC_COMPLETION,
        source_entity_type="diagnostic_session",
        idempotency_key="diag_sess_001"
    )
    assert is_new1 is True
    assert tx1.amount == 50

    # Duplicate call with same idempotency key
    tx2, is_new2 = GamificationService.award_xp(
        user_id=uid,
        amount=50,
        reason_code=XPReasonCode.DIAGNOSTIC_COMPLETION,
        source_entity_type="diagnostic_session",
        idempotency_key="diag_sess_001"
    )
    assert is_new2 is False
    assert tx2.id == tx1.id
    assert GamificationRepository.get_total_xp(uid) == 50


def test_level_progression_calculation():
    """Verify level threshold calculations."""
    lvl1, needed1, pct1 = GamificationService.calculate_level_progression(50)
    assert lvl1 == 1
    assert needed1 == 50
    assert pct1 == 50

    lvl2, needed2, pct2 = GamificationService.calculate_level_progression(150)
    assert lvl2 == 2
    assert needed2 == 150
    assert pct2 == 25


def test_streak_maintenance():
    """Verify daily streak increment and status."""
    uid = STUDENT_USER.id
    streak1 = GamificationService.check_in_streak(uid)
    assert streak1.current_streak_days == 1
    assert streak1.is_active_today is True


# ─── 2. SPACED REPETITION SM-2 TESTS ──────────────────────────────────────────

def test_spaced_repetition_queue_seeding_and_retrieval():
    """Verify that default cards are seeded and available in review queue."""
    uid = STUDENT_USER.id
    queue = SpacedRepetitionService.get_queue(uid)
    assert queue.total_cards >= 4
    assert queue.due_today_count >= 4
    assert len(queue.cards) >= 4


def test_sm2_review_progression():
    """Verify SuperMemo SM-2 interval expansion on successful recall."""
    uid = STUDENT_USER.id
    queue = SpacedRepetitionService.get_queue(uid)
    first_card = queue.cards[0]

    # Perfect recall (quality = 5)
    res = SpacedRepetitionService.process_review(
        user_id=uid,
        request=ReviewSubmissionRequest(card_id=first_card.id, quality_rating=5)
    )
    assert res.quality_rating == 5
    assert res.new_interval == 1
    assert res.new_ease_factor >= first_card.ease_factor
    assert res.xp_awarded > 0

    # Second successful recall (repetition 1 -> interval 6 days)
    res2 = SpacedRepetitionService.process_review(
        user_id=uid,
        request=ReviewSubmissionRequest(card_id=first_card.id, quality_rating=4)
    )
    assert res2.new_interval == 6


# ─── 3. PORTAL ACCESS & RBAC API TESTS ────────────────────────────────────────

def test_parent_portal_dashboard_api():
    """Verify Parent Portal API returns linked children and summary."""
    try:
        app.dependency_overrides[get_current_user] = lambda: PARENT_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/parent/dashboard")
            assert res.status_code == 200
            data = res.json()
            assert "linked_children" in data
            assert len(data["linked_children"]) > 0
            assert data["linked_children"][0]["student_id"] == "a56da972-0f19-418d-b0f7-de91ff114190"
    finally:
        app.dependency_overrides.clear()


def test_parent_portal_blocks_unauthorized_student():
    """Verify student role is rejected with 403 on Parent Portal routes."""
    try:
        app.dependency_overrides[get_current_user] = lambda: STUDENT_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/parent/dashboard")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_teacher_portal_dashboard_api():
    """Verify Teacher Portal API returns classrooms and class misconceptions."""
    try:
        app.dependency_overrides[get_current_user] = lambda: TEACHER_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/teacher/dashboard")
            assert res.status_code == 200
            data = res.json()
            assert "classrooms" in data
            assert "top_class_misconceptions" in data
    finally:
        app.dependency_overrides.clear()


def test_school_admin_portal_overview_api():
    """Verify School Admin Portal API returns school stats and faculty."""
    try:
        app.dependency_overrides[get_current_user] = lambda: SCHOOL_ADMIN_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/school-admin/overview")
            assert res.status_code == 200
            data = res.json()
            assert "school_name" in data
            assert "stats" in data
            assert data["stats"]["total_teachers"] >= 2
    finally:
        app.dependency_overrides.clear()


def test_creator_portal_dashboard_api():
    """Verify Content Creator Portal API returns item bank stats."""
    try:
        app.dependency_overrides[get_current_user] = lambda: CONTENT_CREATOR_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/creator/dashboard")
            assert res.status_code == 200
            data = res.json()
            assert "item_bank_stats" in data
            assert data["item_bank_stats"]["total_items"] > 0
    finally:
        app.dependency_overrides.clear()


def test_super_admin_portal_overview_api():
    """Verify Super Admin Portal API returns system health and LLM provider metrics."""
    try:
        app.dependency_overrides[get_current_user] = lambda: SUPER_ADMIN_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/super-admin/overview")
            assert res.status_code == 200
            data = res.json()
            assert "llm_providers" in data
            assert len(data["llm_providers"]) >= 3
    finally:
        app.dependency_overrides.clear()

