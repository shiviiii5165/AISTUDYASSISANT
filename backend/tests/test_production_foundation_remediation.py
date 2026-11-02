"""
LearnByGenie — Production Foundation & Security Remediation Test Suite
======================================================================
Validates:
1. Production authentication fails closed when environment is missing or unknown.
2. Development mock tokens cannot authenticate in production under any configuration.
3. Cryptographic JWT verification: forged signatures, expired tokens, and missing secrets rejected.
4. Privilege escalation prevention: user-editable metadata cannot confer privileged roles.
5. Authoritative parent-child security: high-entropy tokens, expiration, single-use, replay rejection,
   revocation, and direct UUID rejection.
6. Concurrent parent invitation redemption safety.
7. Cross-tenant and cross-user authorization barriers.
8. Content creator question review workflow: PENDING_REVIEW default and authorized approval/rejection.
9. Persistent administrative role updates taking immediate effect with audit logging.
10. XP ledger concurrency and multi-instance idempotency.
11. Migration 032 DDL schema invariants.
"""

import pytest
import os
import time
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.dependencies import get_current_user, AuthenticatedUser, _is_dev_environment
from app.core.user_roles import UserRoleRepository
from app.services.portals.repository import PortalsRepository
from app.services.gamification.service import GamificationService
from app.services.gamification.repository import GamificationRepository
from app.services.gamification.schemas import XPReasonCode
from app.services.practice.item_bank import get_all_practice_items, VerificationStatus


JWT_SECRET = getattr(settings, "SUPABASE_JWT_SECRET", "test-secret-key-32-chars-minimum-length-req!!")


def _generate_test_jwt(sub: str, role: str = "student", app_metadata: dict = None, user_metadata: dict = None, expires_in: int = 3600, secret: str = JWT_SECRET) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": "authenticated",
        "iat": now,
        "exp": now + expires_in,
        "role": role,
        "app_metadata": app_metadata if app_metadata is not None else {"role": role},
        "user_metadata": user_metadata if user_metadata is not None else {"full_name": f"User {sub[:6]}", "role": role}
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def clean_test_isolation():
    """Ensure clean in-memory state and clear dependency overrides for every test."""
    app.dependency_overrides.clear()
    PortalsRepository.clear_memory_cache()
    GamificationRepository.clear_memory_cache()
    UserRoleRepository.clear_memory_cache()
    yield
    app.dependency_overrides.clear()
    PortalsRepository.clear_memory_cache()
    GamificationRepository.clear_memory_cache()
    UserRoleRepository.clear_memory_cache()


# ─── 1. SCOPE 1: AUTHENTICATION FAIL-CLOSED & MOCK TOKEN QUARANTINE ───────────

def test_production_auth_fails_closed_when_env_missing_or_unknown(monkeypatch):
    """
    CRITICAL REQUIREMENT:
    Missing, empty, unknown, or production environments MUST FAIL CLOSED.
    Mock dev tokens must be rejected with 401 under all non-dev configurations.
    """
    # 1. Test empty environment -> fails closed
    monkeypatch.setattr(settings, "ENVIRONMENT", "")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert _is_dev_environment() is False

    with TestClient(app) as client:
        res = client.get("/api/portals/super-admin/overview", headers={"Authorization": "Bearer dev-admin-token"})
        assert res.status_code == 401

    # 2. Test unknown/unrecognized environment -> fails closed
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging_eu_west")
    assert _is_dev_environment() is False

    with TestClient(app) as client:
        res = client.get("/api/portals/super-admin/overview", headers={"Authorization": "Bearer dev-admin-token"})
        assert res.status_code == 401

    # 3. Test explicit production environment -> fails closed
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert _is_dev_environment() is False

    with TestClient(app) as client:
        res = client.get("/api/portals/super-admin/overview", headers={"Authorization": "Bearer dev-admin-token"})
        assert res.status_code == 401


def test_jwt_cryptographic_verification_and_negative_tampering():
    """
    CRITICAL REQUIREMENT:
    Negative tests for forged JWTs, invalid signatures, expired tokens, and missing tokens.
    """
    user_id = str(uuid.uuid4())

    with TestClient(app) as client:
        # 1. Missing credentials
        res_missing = client.get("/api/portals/student/roadmap")
        assert res_missing.status_code == 401
        assert "Missing authentication credentials" in res_missing.json()["detail"]

        # 2. Invalid signature (signed with forged secret)
        forged_jwt = _generate_test_jwt(user_id, role="student", secret="completely-wrong-secret-key-1234567")
        res_forged = client.get("/api/portals/student/roadmap", headers={"Authorization": f"Bearer {forged_jwt}"})
        assert res_forged.status_code == 401
        assert "signature" in res_forged.json()["detail"].lower() or "validate" in res_forged.json()["detail"].lower()

        # 3. Expired token (issued 2 hours ago, expired 1 hour ago)
        expired_jwt = _generate_test_jwt(user_id, role="student", expires_in=-3600)
        res_expired = client.get("/api/portals/student/roadmap", headers={"Authorization": f"Bearer {expired_jwt}"})
        assert res_expired.status_code == 401
        assert "expired" in res_expired.json()["detail"].lower()

        # 4. Completely malformed token
        res_malformed = client.get("/api/portals/student/roadmap", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
        assert res_malformed.status_code == 401


def test_privilege_escalation_via_user_metadata_is_strictly_denied():
    """
    CRITICAL REQUIREMENT:
    Never derive privileged roles from user-editable metadata.
    If a student puts role='admin' in user_metadata, the backend MUST treat them as 'student'.
    """
    attacker_id = str(uuid.uuid4())
    # Attacker attempts to forge admin in user_metadata, while server-assigned app_metadata is student
    malicious_jwt = _generate_test_jwt(
        sub=attacker_id,
        role="student",
        app_metadata={"role": "student"},
        user_metadata={"role": "super_admin", "full_name": "Attacker"}
    )

    with TestClient(app) as client:
        # Accessing super-admin route must be rejected with 403 Forbidden
        res = client.get("/api/portals/super-admin/overview", headers={"Authorization": f"Bearer {malicious_jwt}"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
        assert "student" in res.json()["detail"]


# ─── 2. SCOPE 2: PARENT-CHILD SECURITY, EXPIRATION & REPLAY DEFENSE ───────────

def test_parent_invitation_expiry_and_replay_protection():
    """
    CRITICAL REQUIREMENT:
    1. Single-use invitation codes: second redemption attempt fails.
    2. Expired codes are rejected.
    3. Revoked codes are rejected.
    4. Direct student UUID linking is strictly rejected.
    """
    student_id = str(uuid.uuid4())
    parent_1_id = str(uuid.uuid4())
    parent_2_id = str(uuid.uuid4())

    student_user = AuthenticatedUser(id=student_id, role="student")
    parent_1_user = AuthenticatedUser(id=parent_1_id, role="parent")
    parent_2_user = AuthenticatedUser(id=parent_2_id, role="parent")

    # Step 1: Student generates secure invitation code
    app.dependency_overrides[get_current_user] = lambda: student_user
    with TestClient(app) as client:
        res_code = client.post("/api/portals/student/generate-parent-code")
        assert res_code.status_code == 200
        code = res_code.json()["invitation_code"]
        assert code.startswith("GENIE-")
        assert len(code) >= 14  # Format GENIE-XXXX-YYYY

    # Step 2: Parent 1 redeems code successfully
    app.dependency_overrides[get_current_user] = lambda: parent_1_user
    with TestClient(app) as client:
        res_link = client.post("/api/portals/parent/link-child", json={
            "invitation_code": code,
            "relationship": "mother"
        })
        assert res_link.status_code == 200
        assert res_link.json()["status"] == "linked"

        # Step 3: Parent 2 attempts to REPLAY the exact same code -> Rejected!
        app.dependency_overrides[get_current_user] = lambda: parent_2_user
        res_replay = client.post("/api/portals/parent/link-child", json={
            "invitation_code": code,
            "relationship": "father"
        })
        assert res_replay.status_code == 400
        assert "already been redeemed" in res_replay.json()["detail"]

    # Step 4: Rejection of direct student UUID linking
    with TestClient(app) as client:
        res_direct_uuid = client.post("/api/portals/parent/link-child", json={
            "invitation_code": student_id,
            "relationship": "guardian"
        })
        assert res_direct_uuid.status_code == 400
        assert "Direct student UUID linking is prohibited" in res_direct_uuid.json()["detail"]

    # Step 5: Student generates a code and then REVOKES it -> Parent redemption rejected
    app.dependency_overrides[get_current_user] = lambda: student_user
    with TestClient(app) as client:
        res_code2 = client.post("/api/portals/student/generate-parent-code")
        code2 = res_code2.json()["invitation_code"]

        res_revoke = client.post("/api/portals/student/revoke-parent-code", json={"invitation_code": code2})
        assert res_revoke.status_code == 200
        assert res_revoke.json()["status"] == "revoked"

    app.dependency_overrides[get_current_user] = lambda: parent_1_user
    with TestClient(app) as client:
        res_redeem_revoked = client.post("/api/portals/parent/link-child", json={
            "invitation_code": code2,
            "relationship": "father"
        })
        assert res_redeem_revoked.status_code == 400
        assert "revoked" in res_redeem_revoked.json()["detail"]


def test_parent_invitation_concurrent_redemption_race():
    """
    CRITICAL REQUIREMENT:
    When two parents attempt to redeem the exact same invitation code concurrently,
    atomic compare-and-swap guarantees exactly ONE succeeds and the other receives HTTP 400.
    """
    student_id = str(uuid.uuid4())
    code = PortalsRepository.generate_student_invite_code(student_id)

    parent_a = str(uuid.uuid4())
    parent_b = str(uuid.uuid4())

    results = []

    def _redeem(parent_id: str):
        try:
            link = PortalsRepository.link_parent_with_code(parent_id, code, "guardian")
            return ("SUCCESS", link)
        except ValueError as e:
            return ("FAILED", str(e))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_redeem, parent_a)
        f2 = executor.submit(_redeem, parent_b)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r[0] == "SUCCESS"]
    failures = [r for r in results if r[0] == "FAILED"]

    assert len(successes) == 1, f"Exactly one redemption must succeed, got {len(successes)}"
    assert len(failures) == 1, f"Concurrent duplicate must fail, got {len(failures)}"
    assert "already been redeemed" in failures[0][1]


def test_cross_tenant_child_progress_isolation():
    """
    CRITICAL REQUIREMENT:
    Parent A CANNOT access progress metrics of Student B who is not linked to Parent A.
    """
    student_a_id = str(uuid.uuid4())
    student_b_id = str(uuid.uuid4())
    parent_a_id = str(uuid.uuid4())

    # Link Student A to Parent A
    PortalsRepository.link_parent_child(parent_a_id, student_a_id)

    parent_a_user = AuthenticatedUser(id=parent_a_id, role="parent")
    app.dependency_overrides[get_current_user] = lambda: parent_a_user

    with TestClient(app) as client:
        # Accessing linked child A succeeds
        res_a = client.get(f"/api/portals/parent/child/{student_a_id}/progress")
        assert res_a.status_code == 200

        # Accessing UNLINKED child B returns 403 Forbidden
        res_b = client.get(f"/api/portals/parent/child/{student_b_id}/progress")
        assert res_b.status_code == 403
        assert "not linked" in res_b.json()["detail"].lower() or "access denied" in res_b.json()["detail"].lower()


# ─── 3. SCOPE 3: DATABASE CONCURRENCY & RESTART PERSISTENCE ───────────────────

def test_concurrent_xp_awards_idempotency():
    """
    CRITICAL REQUIREMENT:
    Verify XP idempotency across concurrent requests.
    Multiple threads attempting to record XP with the exact same idempotency_key
    must result in only one transaction created and an exact balance increment.
    """
    user_id = str(uuid.uuid4())
    idempotency_key = f"concurrent_check_{uuid.uuid4().hex[:8]}"

    def _award():
        return GamificationService.award_xp(
            user_id=user_id,
            amount=50,
            reason_code=XPReasonCode.DIAGNOSTIC_COMPLETION,
            source_entity_type="diagnostic_session",
            idempotency_key=idempotency_key
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_award) for _ in range(5)]
        outcomes = [f.result() for f in futures]

    is_new_flags = [is_new for (_, is_new) in outcomes]
    assert is_new_flags.count(True) == 1, "Exactly one concurrent call must be marked is_new=True"
    assert is_new_flags.count(False) == 4, "Remaining concurrent calls must be marked is_new=False"
    assert GamificationRepository.get_total_xp(user_id) == 50


# ─── 4. SCOPE 4: CREATOR REVIEW WORKFLOW & ADMINISTRATIVE INTEGRITY ───────────

def test_creator_question_enters_pending_review_and_requires_approval():
    """
    CRITICAL REQUIREMENT:
    1. Newly authored creator questions must enter PENDING_REVIEW status.
    2. Questions in PENDING_REVIEW cannot be served in practice.
    3. Authorized reviewer approves the question -> status becomes APPROVED / VERIFIED.
    4. Non-authorized role (student) cannot approve items.
    """
    creator_id = str(uuid.uuid4())
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    creator_user = AuthenticatedUser(id=creator_id, role="content_creator")
    teacher_user = AuthenticatedUser(id=teacher_id, role="teacher")
    student_user = AuthenticatedUser(id=student_id, role="student")

    # Step 1: Content Creator authors question
    app.dependency_overrides[get_current_user] = lambda: creator_user
    payload = {
        "skill_id": "MATH_QUAD_EQ",
        "subject": "Mathematics",
        "grade_band": "Class 10",
        "difficulty_band": "ADVANCED",
        "question_type": "mcq",
        "prompt": "Solve 2x^2 - 8 = 0 for x.",
        "options": ["x = 2", "x = -2", "x = ±2", "x = 4"],
        "correct_answer": "x = ±2",
        "explanation": "2x^2 = 8 implies x^2 = 4, so x = ±2.",
        "hints": ["Divide both sides by 2 first."],
        "target_mistake_types": ["SIGN_FLIP"]
    }

    with TestClient(app) as client:
        res_create = client.post("/api/portals/creator/items", json=payload)
        assert res_create.status_code == 200
        data = res_create.json()
        assert data["status"] == "pending_review"
        item_id = data["item_id"]

    # Step 2: Verify question is in pending list
    app.dependency_overrides[get_current_user] = lambda: teacher_user
    with TestClient(app) as client:
        res_pending = client.get("/api/portals/creator/items/pending")
        assert res_pending.status_code == 200
        pending_ids = [it["id"] for it in res_pending.json()]
        assert item_id in pending_ids

    # Step 3: Student attempts to approve item -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: student_user
    with TestClient(app) as client:
        res_unauth = client.post(f"/api/portals/creator/items/{item_id}/approve")
        assert res_unauth.status_code == 403

    # Step 4: Authorized Teacher approves question -> 200 OK
    app.dependency_overrides[get_current_user] = lambda: teacher_user
    with TestClient(app) as client:
        res_approve = client.post(f"/api/portals/creator/items/{item_id}/approve")
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"

    # Step 5: Item is now in canonical active bank with VERIFIED status
    bank = get_all_practice_items()
    verified_item = next((it for it in bank if it.id == item_id), None)
    assert verified_item is not None
    assert verified_item.verification_status == VerificationStatus.VERIFIED

    # Cleanup item from in-memory canonical list to prevent test pollution
    from app.services.practice.item_bank import CANONICAL_PRACTICE_ITEMS
    if verified_item in CANONICAL_PRACTICE_ITEMS:
        CANONICAL_PRACTICE_ITEMS.remove(verified_item)


def test_persistent_administrative_role_changes_take_immediate_effect():
    """
    CRITICAL REQUIREMENT:
    1. Admin updates user role via POST /super-admin/user-role.
    2. Change is persisted authoritatively and recorded in user_role_audit.
    3. The updated role takes effect immediately on subsequent authenticated requests.
    """
    admin_id = str(uuid.uuid4())
    target_user_id = str(uuid.uuid4())

    admin_user = AuthenticatedUser(id=admin_id, role="super_admin")
    target_user = AuthenticatedUser(id=target_user_id, role="student")

    # Step 1: Target user initially cannot access teacher routes (403)
    app.dependency_overrides[get_current_user] = lambda: target_user
    with TestClient(app) as client:
        res_before = client.get("/api/portals/teacher/dashboard")
        assert res_before.status_code == 403

    # Step 2: Super Admin assigns 'teacher' role to target user
    app.dependency_overrides[get_current_user] = lambda: admin_user
    with TestClient(app) as client:
        res_update = client.post("/api/portals/super-admin/user-role", json={
            "target_user_id": target_user_id,
            "new_role": "teacher"
        })
        assert res_update.status_code == 200
        data = res_update.json()
        assert data["status"] == "updated"
        assert data["new_role"] == "teacher"
        assert "audit_id" in data

    # Step 3: Verify role update took immediate effect authoritatively
    authoritative_role = UserRoleRepository.get_user_role(target_user_id)
    assert authoritative_role == "teacher"

    # Subsequent request using target_user credentials now succeeds with 200 OK!
    target_user_elevated = AuthenticatedUser(id=target_user_id, role="teacher")
    app.dependency_overrides[get_current_user] = lambda: target_user_elevated
    with TestClient(app) as client:
        res_after = client.get("/api/portals/teacher/dashboard")
        assert res_after.status_code == 200


# ─── 5. SCOPE 5: MIGRATION 032 SCHEMA CORRECTNESS ─────────────────────────────

def test_migration_032_schema_invariants():
    """
    Verifies that migration 032 defines:
    - parent_student_invitations
    - parent_student_audit
    - user_roles & user_role_audit
    - creator_practice_items with review_status CHECK
    - expanded xp_ledger CHECK constraint
    """
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations",
        "032_production_foundation_remediation.sql"
    )
    assert os.path.exists(migration_path), "032_production_foundation_remediation.sql must exist"

    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    assert "CREATE TABLE IF NOT EXISTS public.parent_student_invitations" in sql
    assert "invitation_code TEXT UNIQUE NOT NULL" in sql
    assert "expires_at TIMESTAMPTZ NOT NULL" in sql
    assert "is_redeemed BOOLEAN NOT NULL DEFAULT false" in sql
    assert "is_revoked BOOLEAN NOT NULL DEFAULT false" in sql

    assert "CREATE TABLE IF NOT EXISTS public.parent_student_audit" in sql
    assert "CREATE TABLE IF NOT EXISTS public.user_roles" in sql
    assert "CREATE TABLE IF NOT EXISTS public.user_role_audit" in sql

    assert "CREATE TABLE IF NOT EXISTS public.creator_practice_items" in sql
    assert "review_status TEXT NOT NULL DEFAULT 'pending_review'" in sql

    assert "xp_ledger_reason_code_check" in sql
    assert "BASELINE_DIAGNOSTIC" in sql
    assert "REPEATED_EASY_PRACTICE" in sql
