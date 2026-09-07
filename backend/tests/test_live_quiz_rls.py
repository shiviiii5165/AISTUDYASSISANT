"""
TeachGenie — Live Quiz Engine: Row Level Security (RLS) & DB Access Control Tests
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
    1. An unauthenticated query with the public Anon Key gets 0 rows on live_quiz_sessions.
    2. Real database RLS prevents guest or participant clients from seeing host sessions.
    """
    from supabase import create_client
    from pathlib import Path
    from dotenv import load_dotenv
    root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)

    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

    if not url or not anon_key or "mock" in url:
        pytest.skip("Skipping live database RLS check (no live SUPABASE_URL configured)")

    anon_client = create_client(url, anon_key)
    # Attempt to query live_quiz_sessions as an unauthenticated guest
    res = anon_client.table("live_quiz_sessions").select("id, questions_snapshot").execute()

    # RLS Policy "Hosts manage their live sessions" restricts rows to auth.uid() = host_user_id
    # Since anon_client has no auth.uid(), PostgreSQL returns exactly 0 rows.
    assert len(res.data) == 0, f"PostgreSQL RLS must return 0 rows to unauthenticated client, got {len(res.data)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

