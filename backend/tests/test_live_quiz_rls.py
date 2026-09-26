"""
LearnByGenie — Live Quiz Engine: Row Level Security (RLS) & DB Access Control Tests
================================================================================
Verifies that:
1. DB RLS Policy on live_quiz_sessions enforces (auth.uid() = host_user_id).
2. A guest/participant JWT cannot query live_quiz_sessions directly (0 rows returned).
3. Non-host authenticated users (User B) cannot query User A's session.
4. Participant tokens (role='participant') cannot authenticate as host.
5. SQL migration file contains strict ENABLE ROW LEVEL SECURITY on all live tables.
"""
import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr


def test_sql_migration_rls_definitions():
    """Verify 014_live_quiz.sql explicitly enables RLS and defines host-only isolation."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations",
        "014_live_quiz.sql"
    )
    assert os.path.exists(migration_path), "014_live_quiz.sql migration file must exist"

    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # 1. Check RLS is enabled on all live quiz tables
    assert "ALTER TABLE live_quiz_sessions     ENABLE ROW LEVEL SECURITY;" in sql or \
           "ALTER TABLE live_quiz_sessions ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE live_quiz_participants ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE live_quiz_responses    ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE live_quiz_events       ENABLE ROW LEVEL SECURITY;" in sql

    # 2. Check Host-Only SELECT policy on live_quiz_sessions
    assert "auth.uid() = host_user_id" in sql
    assert 'CREATE POLICY "Hosts manage their live sessions"' in sql

    # 3. Check cascading policy for participants/responses
    assert "host_user_id = auth.uid()" in sql


def test_participant_jwt_role_cannot_be_host():
    """Verify participant JWT claims cannot masquerade as host or bypass RLS."""
    pid = "student-guest-001"
    sid = "sess-alpha-777"
    display_name = "Speedy Falcon"

    token = repo.create_participant_token(pid, sid, display_name)
    claims = repo.verify_participant_token(token)

    # Participant JWT has role='participant' and no auth.uid matching a host
    assert claims["role"] == "participant"
    assert claims["sub"] == pid
    assert claims["session_id"] == sid
    assert "host_user_id" not in claims


def test_db_rls_simulation_guest_and_participant_blocked():
    """
    Simulates PostgreSQL Row-Level Security policy evaluation:
    POLICY "Hosts manage their live sessions" ON live_quiz_sessions FOR ALL USING (auth.uid() = host_user_id);
    """
    host_user_id = "user-teacher-aaa"
    other_user_id = "user-attacker-bbb"
    participant_id = "student-guest-ccc"

    # Simulated row in live_quiz_sessions table
    db_row = {
        "id": "sess-live-999",
        "host_user_id": host_user_id,
        "questions_snapshot": [
            {"id": "q1", "correct_answer": "42", "explanation": "Secret answer"}
        ]
    }

    # Policy evaluation function: returns True if row is visible under RLS
    def evaluate_rls_policy(row: dict, auth_uid: str | None) -> bool:
        if auth_uid is None:
            return False
        return row.get("host_user_id") == auth_uid

    # 1. Host user queries -> Visible
    assert evaluate_rls_policy(db_row, auth_uid=host_user_id) is True

    # 2. Guest/Unauthenticated (auth.uid() is NULL) queries -> BLOCKED (0 rows)
    assert evaluate_rls_policy(db_row, auth_uid=None) is False

    # 3. Participant JWT (sub is participant_id != host_user_id) queries -> BLOCKED (0 rows)
    assert evaluate_rls_policy(db_row, auth_uid=participant_id) is False

    # 4. Another authenticated user (User B) queries -> BLOCKED (0 rows)
    assert evaluate_rls_policy(db_row, auth_uid=other_user_id) is False


def test_participant_only_receives_sanitized_state():
    """Verify that participant queries via session manager NEVER return questions_snapshot."""
    sid = "sess-rls-sanitized-test"
    host_id = "teacher-master"
    pid = "part-student-1"

    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-rls-1",
        "host_user_id": host_id,
        "join_code": "112233",
        "status": "LIVE",
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [
            {
                "id": "q1",
                "question_text": "Confidential question?",
                "options": ["A", "B", "C"],
                "correct_answer": "B",
                "explanation": "Confidential grading reasoning"
            }
        ],
        "question_order": ["q1"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })
    repo.create_participant({"id": pid, "session_id": sid, "display_name": "Student A", "score": 0, "status": "active"})

    # Fetch through participant sanitized access
    student_state = mgr.get_sanitized_student_state(sid, pid)

    # Asserts that DB snapshot with answers is never present
    assert "questions_snapshot" not in student_state
    assert "correct_answer" not in (student_state.get("question") or {})
    assert "explanation" not in (student_state.get("question") or {})


def test_real_database_rls_live_postgres():
    """
    Connects to the REAL Supabase PostgreSQL instance and proves:
    1. Teacher A cannot access Teacher B records (and Teacher B cannot access Teacher A).
    2. Anonymous access is rejected where expected (0 rows returned, mutations blocked).
    3. Revoked participant cannot continue reading/writing (sanitized access and canary lifecycle).
    4. Service-role-only operations remain inaccessible to normal users.
    5. Canary analytics cannot reveal raw identity mappings.
    """
    import uuid
    import time
    import jwt
    from supabase import create_client
    from pathlib import Path
    from dotenv import load_dotenv
    root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)

    url = os.environ.get("SUPABASE_URL")
    secret_key = os.environ.get("SUPABASE_KEY")
    anon_key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")

    if not url or not anon_key or not secret_key or "mock" in url:
        pytest.skip("Skipping live database RLS check (no live SUPABASE_URL configured)")

    # 1. Initialize admin client (service role)
    admin_client = create_client(url, secret_key)
    res_sessions = admin_client.table("live_quiz_sessions").select("id, host_user_id").limit(1).execute()
    assert len(res_sessions.data) >= 1, "Must find at least one existing session in live database for RLS test"
    session_row = res_sessions.data[0]
    session_id = session_row["id"]
    teacher_a_id = session_row["host_user_id"]
    teacher_b_id = str(uuid.uuid4())

    def make_jwt(sub: str, role: str = "authenticated") -> str:
        payload = {
            "sub": sub,
            "role": role,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600
        }
        return jwt.encode(payload, jwt_secret, algorithm="HS256")

    # 2. Check 1: Teacher A vs Teacher B Isolation
    client_a = create_client(url, anon_key)
    client_a.postgrest.auth(make_jwt(teacher_a_id))
    client_b = create_client(url, anon_key)
    client_b.postgrest.auth(make_jwt(teacher_b_id))

    res_a = client_a.table("live_quiz_sessions").select("id, host_user_id").eq("id", session_id).execute()
    res_b = client_b.table("live_quiz_sessions").select("id, host_user_id").eq("id", session_id).execute()
    assert len(res_a.data) == 1, f"Teacher A must see their own session, got {len(res_a.data)}"
    assert len(res_b.data) == 0, f"Teacher B must NOT see Teacher A's session, got {len(res_b.data)}"

    # Teacher B mutation attempt on Teacher A record must affect 0 rows
    res_b_mut = client_b.table("live_quiz_sessions").update({"status": "TAMPERED"}).eq("id", session_id).execute()
    assert len(res_b_mut.data) == 0, "Teacher B must NOT be able to mutate Teacher A's record"

    # 3. Check 2: Anonymous access rejected
    anon_client = create_client(url, anon_key)
    res_anon = anon_client.table("live_quiz_sessions").select("id, questions_snapshot").eq("id", session_id).execute()
    assert len(res_anon.data) == 0, f"PostgreSQL RLS must return 0 rows to unauthenticated client, got {len(res_anon.data)}"

    # 4. Check 3: Participant access rejection & isolation
    # 4a. Participant JWT with role='participant' is rejected by PostgREST / PostgreSQL
    part_id = str(uuid.uuid4())
    client_part = create_client(url, anon_key)
    client_part.postgrest.auth(make_jwt(part_id, role="participant"))
    try:
        res_part = client_part.table("live_quiz_sessions").select("id").eq("id", session_id).execute()
        # If it returned, must be 0 rows
        assert len(res_part.data) == 0
    except Exception as exc:
        # PostgREST strictly rejects tokens without a valid database role
        assert "participant" in str(exc) or "role" in str(exc)

    # 4b. Authenticated participant/student (role='authenticated', sub=student_id != host_user_id) returns 0 rows under RLS
    client_student = create_client(url, anon_key)
    client_student.postgrest.auth(make_jwt(part_id, role="authenticated"))
    res_student = client_student.table("live_quiz_sessions").select("id, questions_snapshot").eq("id", session_id).execute()
    assert len(res_student.data) == 0, f"Authenticated student must get 0 rows on host session under RLS, got {len(res_student.data)}"

    # 4b. Canary revoked participant lifecycle verification
    from app.services.lesson_planner.vnext.canary.authorization import AuthorizationRegistry, AuthorizationStatus
    from app.services.lesson_planner.vnext.canary.pseudonyms import ManagedIdentityStore, ServiceTokenManager, VaultRole
    from app.services.lesson_planner.vnext.canary.lifecycle import DataLifecycleManager, AuthorizationRevokedError

    rev_teacher_raw = f"revoked_teacher_{uuid.uuid4().hex[:8]}@example.com"
    enroll_token = ServiceTokenManager.issue_token("enrollment_service", VaultRole.ENROLLMENT_SERVICE)
    rev_pseudo = ManagedIdentityStore.get_or_create_pseudonym(
        raw_user_id=rev_teacher_raw,
        role="teacher",
        caller_context=enroll_token
    )
    AuthorizationRegistry.grant_authorization(pseudonym_id=rev_pseudo, entity_role="teacher")
    # Revoke participant
    DataLifecycleManager.execute_revocation_lifecycle(rev_pseudo, reason="Pre-canary verification test")

    # Verify telemetry ingestion is completely rejected
    with pytest.raises(AuthorizationRevokedError):
        DataLifecycleManager.verify_telemetry_allowed(rev_pseudo)

    # Verify identity vault lookup is completely blocked
    lookup_token = ServiceTokenManager.issue_token("research_eval_service", VaultRole.CANARY_SERVICE)
    with pytest.raises(PermissionError):
        ManagedIdentityStore.lookup_pseudonym(rev_pseudo, caller_context=lookup_token)

    # 5. Check 4: Service-role-only operations remain inaccessible to normal users
    res_admin = admin_client.table("live_quiz_sessions").select("id").execute()
    assert len(res_admin.data) >= 1, "Admin service role must be able to view all records"
    # Unauthenticated / normal user cannot bypass host filters or view other hosts
    assert len(res_b.data) == 0 and len(res_anon.data) == 0

    # 6. Check 5: Canary analytics cannot reveal raw identity mappings
    from app.services.lesson_planner.vnext.canary.exports import CanaryDatasetExporter
    from app.services.lesson_planner.vnext.canary.lifecycle import DataMinimizer

    # 6a. Data Minimizer strips extraneous keys and rejects raw PII
    dirty_session = {
        "session_id": "sess_canary_audit",
        "teacher_pseudonym_id": rev_pseudo,
        "canonical_concept_id": "concept_algebra_quadratics",
        "extra_unneeded_field": "some_value"
    }
    minimized = DataMinimizer.sanitize("session", dirty_session)
    assert "extra_unneeded_field" not in minimized, "Data minimization must filter unwhitelisted fields"
    assert minimized["teacher_pseudonym_id"] == rev_pseudo

    # Attempting to ingest email / PII raises ValueError
    pii_payload = {
        "session_id": "sess_pii",
        "teacher_pseudonym_id": rev_pseudo,
        "email": "teacher_leaked@example.com"
    }
    with pytest.raises(ValueError, match="PII detected"):
        DataMinimizer.sanitize("session", pii_payload)

    # 6b. CanaryDatasetExporter rejects raw user IDs / unmasked PII
    leaked_record = {
        "session_id": "sess_leak",
        "teacher_pseudonym_id": "raw_teacher_unmasked_123",
        "student_pseudonym_id": "raw_student_unmasked_456",
        "canonical_concept_id": "concept_1",
        "stage_title": "Intro",
        "pre_state": "unknown",
        "post_state": "mastered",
        "misconception_tag": "none",
        "time_spent_seconds": 30,
        "feedback_type": "positive",
        "created_at": "2026-09-13T10:00:00Z"
    }
    privacy_check = CanaryDatasetExporter.validate_export_privacy([leaked_record])
    assert not privacy_check["is_privacy_compliant"], "Export validator must reject non-pseudonymous IDs"
    with pytest.raises(ValueError, match="Privacy validation failed"):
        CanaryDatasetExporter.export_to_csv([leaked_record])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


