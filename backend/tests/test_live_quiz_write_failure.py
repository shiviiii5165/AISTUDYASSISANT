"""
Test Suite: Live Quiz Supabase Failure & Loud Error Propagation
==============================================================
Verifies that database write failures (connection drop, constraint violation, outage)
raise DatabaseWriteError loudly and do NOT silently degrade into in-memory storage.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.live_quiz import repository as repo
from app.services.live_quiz.repository import DatabaseWriteError


def test_create_live_session_raises_loud_error_on_supabase_failure():
    """Verify that an insert failure on live_quiz_sessions raises DatabaseWriteError."""
    session_data = {
        "id": "sess-loud-failure-1",
        "quiz_id": "00000000-0000-0000-0000-000000000001",
        "host_user_id": "00000000-0000-0000-0000-000000000002",
        "join_code": "999888",
        "status": "CREATED",
        "version": 1,
    }

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.side_effect = Exception("Simulated connection drop to Postgres")

    with patch.object(repo, "is_persistence_enabled", return_value=True), \
         patch.object(repo, "supabase") as mock_sup:
        mock_sup.table.return_value = mock_table

        with pytest.raises(DatabaseWriteError) as exc_info:
            repo.create_live_session(session_data)

        # 1. Error message contains the root cause
        assert "Simulated connection drop to Postgres" in str(exc_info.value)
        # 2. Memory store did NOT quietly retain the record
        assert "sess-loud-failure-1" not in repo._MEM_SESSIONS
        print("\n[Loud Error Verified] create_live_session raised DatabaseWriteError cleanly")


def test_update_live_session_raises_loud_error_on_supabase_failure():
    """Verify that an update failure on live_quiz_sessions raises DatabaseWriteError."""
    sid = "sess-loud-update-fail"
    repo._MEM_SESSIONS[sid] = {"id": sid, "version": 1, "status": "LOBBY"}

    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.side_effect = Exception("Simulated DB lock timeout")

    with patch.object(repo, "is_persistence_enabled", return_value=True), \
         patch.object(repo, "supabase") as mock_sup:
        mock_sup.table.return_value = mock_table

        with pytest.raises(DatabaseWriteError) as exc_info:
            repo.update_live_session(sid, {"status": "LIVE"})

        assert "Simulated DB lock timeout" in str(exc_info.value)
        print("\n[Loud Error Verified] update_live_session raised DatabaseWriteError cleanly")


def test_create_participant_raises_loud_error_on_supabase_failure():
    """Verify that an insert failure on live_quiz_participants raises DatabaseWriteError."""
    p_data = {
        "id": "part-loud-failure-1",
        "session_id": "sess-any",
        "display_name": "Test Student",
    }

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.side_effect = Exception("Simulated duplicate participant ID in DB")

    with patch.object(repo, "is_persistence_enabled", return_value=True), \
         patch.object(repo, "supabase") as mock_sup:
        mock_sup.table.return_value = mock_table

        with pytest.raises(DatabaseWriteError) as exc_info:
            repo.create_participant(p_data)

        assert "Simulated duplicate participant ID in DB" in str(exc_info.value)
        assert "part-loud-failure-1" not in repo._MEM_PARTICIPANTS
        print("\n[Loud Error Verified] create_participant raised DatabaseWriteError cleanly")


def test_record_response_raises_loud_error_on_supabase_failure():
    """Verify that non-duplicate response insert failures raise DatabaseWriteError."""
    r_data = {
        "session_id": "sess-resp-fail",
        "participant_id": "part-resp-fail",
        "question_id": "q-fail",
        "selected_option": "A",
    }

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.side_effect = Exception("Disk full on Postgres host")

    with patch.object(repo, "is_persistence_enabled", return_value=True), \
         patch.object(repo, "supabase") as mock_sup:
        mock_sup.table.return_value = mock_table

        with pytest.raises(DatabaseWriteError) as exc_info:
            repo.record_response(r_data)

        assert "Disk full on Postgres host" in str(exc_info.value)
        key = ("sess-resp-fail", "part-resp-fail", "q-fail")
        assert key not in repo._MEM_RESPONSES
        print("\n[Loud Error Verified] record_response raised DatabaseWriteError cleanly")


def test_real_supabase_write_failure_raises_loud_database_write_error():
    """
    Live Integration: Connects to real Supabase with invalid data (e.g. non-existent quiz FK)
    and verifies that PostgreSQL constraint rejection raises DatabaseWriteError.
    """
    if not repo.supabase:
        pytest.skip("Skipping live Supabase test (client not configured)")

    # Session with invalid foreign key quiz_id that does not exist in quizzes table
    bad_session = {
        "id": "00000000-0000-0000-0000-000000000099",
        "quiz_id": "00000000-0000-0000-0000-000000000099",  # Does not exist in quizzes
        "host_user_id": "00000000-0000-0000-0000-000000000099",
        "join_code": "000099",
        "status": "CREATED",
        "version": 1,
    }

    repo.set_persistence_enabled(True)
    with pytest.raises(DatabaseWriteError) as exc_info:
        repo.create_live_session(bad_session)

    # Postgres foreign key error was raised and wrapped in DatabaseWriteError
    err_str = str(exc_info.value).lower()
    assert "foreign key" in err_str or "violates" in err_str or "database insert failed" in err_str or "23503" in err_str
    print(f"\n[Real PostgreSQL Constraint Check] Successfully caught: {exc_info.value}")
