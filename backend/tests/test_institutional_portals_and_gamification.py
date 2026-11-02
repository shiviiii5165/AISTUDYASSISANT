import pytest
import uuid
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
    uid = str(uuid.uuid4())
    test_key = f"diag_sess_{uuid.uuid4().hex[:8]}"
    tx1, is_new1 = GamificationService.award_xp(
        user_id=uid,
        amount=50,
        reason_code=XPReasonCode.DIAGNOSTIC_COMPLETION,
        source_entity_type="diagnostic_session",
        idempotency_key=test_key
    )
    assert is_new1 is True
    assert tx1.amount == 50

    # Duplicate call with same idempotency key
    tx2, is_new2 = GamificationService.award_xp(
        user_id=uid,
        amount=50,
        reason_code=XPReasonCode.DIAGNOSTIC_COMPLETION,
        source_entity_type="diagnostic_session",
        idempotency_key=test_key
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
        PortalsRepository.link_parent_child(PARENT_USER.id, "a56da972-0f19-418d-b0f7-de91ff114190")
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


# ─── 4. DAILY ROADMAP (30/50/20) & BLUEPRINT REWARD TESTS ────────────────────

def test_student_daily_roadmap_30_50_20():
    """Verify Student Daily Roadmap provides 3 choices with 30/50/20 category weights (§8)."""
    try:
        app.dependency_overrides[get_current_user] = lambda: STUDENT_USER
        with TestClient(app) as client:
            res = client.get("/api/portals/student/roadmap")
            assert res.status_code == 200
            data = res.json()
            assert "tasks" in data
            assert len(data["tasks"]) == 3
            weights = [t["weight_percentage"] for t in data["tasks"]]
            assert weights == [30, 50, 20]
            categories = [t["category"] for t in data["tasks"]]
            assert "SPACED_ERROR_REPAIR" in categories
            assert "CORE_PROGRESSION" in categories
            assert "INTERLEAVED_TRANSFER" in categories
            for t in data["tasks"]:
                assert len(t["why_recommended"]) > 10
                assert len(t["unlocks_next"]) > 5
                assert t["expected_duration_minutes"] > 0
    finally:
        app.dependency_overrides.clear()


def test_error_token_taxonomy_resolution():
    """Verify that MistakeClassifier tags errors with canonical E01–E20 ErrorToken IDs."""
    from app.services.mistake_dna.classifier import MistakeClassifier
    from app.services.mistake_dna.schemas import MistakeCandidate, MistakeSourceType, AssistanceLevel, ErrorTokenID

    # Test Sign Flip -> E07
    cand_sign = MistakeCandidate(
        user_id=STUDENT_USER.id,
        skill_id="MATH_ALG_QUAD01",
        source_type=MistakeSourceType.PRACTICE,
        source_record_id="rec_01",
        student_response="-5",
        expected_answer="5",
        feedback_reason="sign error"
    )
    res_sign = MistakeClassifier.classify(cand_sign)
    assert res_sign.error_token_id == ErrorTokenID.E07.value

    # Test Arithmetic Slip -> E08
    cand_calc = MistakeCandidate(
        user_id=STUDENT_USER.id,
        skill_id="MATH_ALG_QUAD01",
        source_type=MistakeSourceType.PRACTICE,
        source_record_id="rec_02",
        student_response="14",
        expected_answer="15"
    )
    res_calc = MistakeClassifier.classify(cand_calc)
    assert res_calc.error_token_id == ErrorTokenID.E08.value

    # Test Empty / Give Up -> E18
    cand_empty = MistakeCandidate(
        user_id=STUDENT_USER.id,
        skill_id="MATH_ALG_QUAD01",
        source_type=MistakeSourceType.PRACTICE,
        source_record_id="rec_03",
        student_response="idk"
    )
    res_empty = MistakeClassifier.classify(cand_empty)
    assert res_empty.error_token_id == ErrorTokenID.E18.value


def test_blueprint_xp_rewards_and_daily_cap():
    """Verify canonical blueprint XP amounts and 10 XP/day cap on repeated easy items (§8)."""
    uid = str(uuid.uuid4())
    run_id = uuid.uuid4().hex[:6]

    # 1. Baseline diagnostic: +50 XP
    tx1, _ = GamificationService.award_blueprint_xp(
        user_id=uid,
        reason_code=XPReasonCode.BASELINE_DIAGNOSTIC,
        source_entity_type="diagnostic_session",
        idempotency_key=f"diag_xp_{run_id}"
    )
    assert tx1.amount == 50

    # 2. Active error resolution: +30 XP
    tx2, _ = GamificationService.award_blueprint_xp(
        user_id=uid,
        reason_code=XPReasonCode.ERROR_RESOLUTION_UNSEEN,
        source_entity_type="mistake_repair",
        idempotency_key=f"repair_xp_{run_id}"
    )
    assert tx2.amount == 30

    # 3. Repeated easy practice: 2 XP per item, capped at 10 XP/day
    for i in range(5):
        GamificationService.award_xp(
            user_id=uid,
            amount=2,
            reason_code=XPReasonCode.REPEATED_EASY_PRACTICE,
            source_entity_type="practice_item",
            idempotency_key=f"easy_item_{run_id}_{i}"
        )
    # 6th easy practice attempt: cap reached, should receive 0 XP
    tx_capped, _ = GamificationService.award_xp(
        user_id=uid,
        amount=2,
        reason_code=XPReasonCode.REPEATED_EASY_PRACTICE,
        source_entity_type="practice_item",
        idempotency_key=f"easy_item_overflow_{run_id}"
    )
    assert tx_capped.amount == 0


def test_parent_student_invite_code_handshake():
    """Verify authentic student invite code generation and parental linking handshake."""
    new_student_id = "00000000-0000-0000-0000-000000000555"
    student_user = AuthenticatedUser(id=new_student_id, role="student", email="child555@learnbygenie.com")
    new_parent_id = "00000000-0000-0000-0000-000000000777"
    parent_user = AuthenticatedUser(id=new_parent_id, role="parent", email="parent777@learnbygenie.com")

    # Step 1: Student generates parent invitation code
    try:
        app.dependency_overrides[get_current_user] = lambda: student_user
        with TestClient(app) as client:
            res_code = client.post("/api/portals/student/generate-parent-code")
            assert res_code.status_code == 200
            invite_code = res_code.json()["invitation_code"]
            assert invite_code.startswith("GENIE-")
    finally:
        app.dependency_overrides.clear()

    # Step 2: Parent links child using valid invite code
    try:
        app.dependency_overrides[get_current_user] = lambda: parent_user
        with TestClient(app) as client:
            res_link = client.post("/api/portals/parent/link-child", json={
                "invitation_code": invite_code,
                "relationship": "guardian"
            })
            assert res_link.status_code == 200
            data = res_link.json()
            assert data["status"] == "linked"
            assert data["link"]["student_id"] == new_student_id

            # Verify parent dashboard now shows linked child
            res_dash = client.get("/api/portals/parent/dashboard")
            assert res_dash.status_code == 200
            dash_data = res_dash.json()
            assert any(c["student_id"] == new_student_id for c in dash_data["linked_children"])
    finally:
        app.dependency_overrides.clear()


# ─── 6. SERVER-VERIFIED ROLES & PORTAL AUTHORIZATION TESTS ────────────────────

def test_user_roles_endpoint_for_all_roles():
    """Verify that /api/portals/me/roles returns strictly server-authorized roles for each persona."""
    roles_test_matrix = [
        (STUDENT_USER, ["student"], "student"),
        (TEACHER_USER, ["teacher", "student"], "teacher"),
        (PARENT_USER, ["parent", "student"], "parent"),
        (SCHOOL_ADMIN_USER, ["school_admin", "teacher", "student"], "school_admin"),
        (CONTENT_CREATOR_USER, ["content_creator", "student"], "content_creator"),
        (SUPER_ADMIN_USER, ["student", "parent", "teacher", "school_admin", "content_creator", "super_admin"], "super_admin"),
    ]

    for user, expected_authorized, expected_primary in roles_test_matrix:
        try:
            app.dependency_overrides[get_current_user] = lambda u=user: u
            with TestClient(app) as client:
                res = client.get("/api/portals/me/roles")
                assert res.status_code == 200, f"Failed for {user.role}: {res.text}"
                data = res.json()
                assert data["user_id"] == user.id
                assert data["primary_role"] == expected_primary
                assert set(data["authorized_roles"]) == set(expected_authorized)
                assert data["active_role"] == expected_primary
        finally:
            app.dependency_overrides.clear()


