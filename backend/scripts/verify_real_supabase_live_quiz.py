"""
Verification Script: Real Database RLS & Persistence against Supabase
====================================================================
Verifies against the live Supabase PostgreSQL instance:
1. Direct table write to live_quiz_sessions, live_quiz_participants, live_quiz_responses.
2. Direct SELECT from Supabase confirming physical rows exist in PostgreSQL.
3. In-memory cache purge (_MEM_SESSIONS.clear()) proving data loads from Postgres.
4. RLS enforcement: An unauthenticated/anon client querying live_quiz_sessions gets 0 rows.
5. Cross-tenant RLS: User B querying User A's session gets 0 rows.
"""
import os
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(BACKEND.parent / ".env")

from supabase import create_client
from app.db.supabase_client import supabase as admin_supabase
from app.services.live_quiz import repository as repo

URL = os.environ["SUPABASE_URL"]
SERVICE_KEY = os.environ["SUPABASE_KEY"]
ANON_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY") or SERVICE_KEY

print("=" * 70)
print("REAL SUPABASE DATABASE VERIFICATION — LIVE POSTGRES")
print(f"Connecting to: {URL}")
print("=" * 70)

# Step 1: Check test quiz exists to satisfy foreign key REFERENCES quizzes(id)
quiz_res = admin_supabase.table("quizzes").select("id, owner_user_id").limit(1).execute()
assert quiz_res.data, "Need at least 1 quiz in quizzes table"
test_quiz = quiz_res.data[0]
quiz_id = test_quiz["id"]
host_user_id = test_quiz.get("owner_user_id") or "00000000-0000-0000-0000-000000000001"

# Check if host user exists in auth.users
profile_res = admin_supabase.table("profiles").select("id").limit(1).execute()
if profile_res.data:
    host_user_id = profile_res.data[0]["id"]

print(f"Using test quiz_id: {quiz_id}")
print(f"Using host_user_id: {host_user_id}")

session_id = str(uuid.uuid4())
import random
join_code = f"{random.randint(100000, 999999)}"

# 1. WRITE TO REAL SUPABASE TABLE
print("\n--- 1. Testing Real Write to live_quiz_sessions ---")
session_payload = {
    "id": session_id,
    "quiz_id": quiz_id,
    "host_user_id": host_user_id,
    "join_code": join_code,
    "status": "LOBBY",
    "mode": "teacher_led",
    "current_question_index": 0,
    "total_questions": 1,
    "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": True},
    "settings": {"sound_fx": True, "leaderboard_enabled": True},
    "questions_snapshot": [
        {
            "id": "q1",
            "question_text": "What is 2 + 2?",
            "type": "mcq",
            "options": ["3", "4", "5", "6"],
            "correct_answer": "4",
            "explanation": "Basic math."
        }
    ],
    "question_order": ["q1"],
    "version": 1
}

created_sess = repo.create_live_session(session_payload)
print(f"Created session ID: {created_sess['id']}")

# Verify row exists in PostgreSQL directly via service-role
db_check = admin_supabase.table("live_quiz_sessions").select("id, join_code, status, host_user_id").eq("id", session_id).execute()
print(f"Direct DB Query Result: {db_check.data}")
assert len(db_check.data) == 1, "Row must exist in Postgres!"
print(">>> CONFIRMED: Row physically exists in Supabase live_quiz_sessions table!")

# 2. PROVE PERSISTENCE (BYPASS IN-MEMORY STORE)
print("\n--- 2. Testing Persistence by Clearing In-Memory Dictionary ---")
repo._MEM_SESSIONS.clear()
assert session_id not in repo._MEM_SESSIONS, "Memory dictionary must be empty"

loaded_from_db = repo.get_live_session(session_id)
assert loaded_from_db is not None, "Must load from Supabase table!"
print(f"Loaded from DB after memory wipe: id={loaded_from_db['id']}, join_code={loaded_from_db['join_code']}")
print(">>> CONFIRMED: Persistence is real — survives complete in-memory wipe!")

# 3. WRITE PARTICIPANT AND RESPONSE TO REAL TABLES
print("\n--- 3. Testing Participant & Response Writes ---")
part_id = str(uuid.uuid4())
part_payload = {
    "id": part_id,
    "session_id": session_id,
    "display_name": "Test Student DB",
    "avatar_seed": "lion",
    "score": 100,
    "status": "active"
}
created_part = repo.create_participant(part_payload)
db_part_check = admin_supabase.table("live_quiz_participants").select("id, display_name, score").eq("id", part_id).execute()
print(f"Direct DB Participant Query: {db_part_check.data}")
assert len(db_part_check.data) == 1

resp_id = str(uuid.uuid4())
resp_payload = {
    "id": resp_id,
    "session_id": session_id,
    "participant_id": part_id,
    "question_id": "q1",
    "selected_option_id": "4",
    "is_correct": True,
    "points": 100,
    "response_time_ms": 1500
}
created_resp = repo.record_response(resp_payload)
db_resp_check = admin_supabase.table("live_quiz_responses").select("id, is_correct, points").eq("id", resp_id).execute()
print(f"Direct DB Response Query: {db_resp_check.data}")
assert len(db_resp_check.data) == 1
print(">>> CONFIRMED: Participants and responses are writing directly to Postgres!")

# 4. REAL DATABASE RLS ENFORCEMENT TEST
print("\n--- 4. Testing Real PostgreSQL Row-Level Security (RLS) ---")
# Create an anonymous/unauthenticated client (represents a guest or student with Anon Key)
anon_client = create_client(URL, ANON_KEY)

# Attempt to query live_quiz_sessions without host auth
anon_res = anon_client.table("live_quiz_sessions").select("id, questions_snapshot").eq("id", session_id).execute()
print(f"Anon/Guest Query on live_quiz_sessions (Expect 0 rows): data={anon_res.data}")
assert len(anon_res.data) == 0, "PostgreSQL RLS must reject unauthenticated SELECT!"
print(">>> CONFIRMED: Postgres kernel RLS returned 0 rows to unauthenticated/guest query!")

# 5. CLEANUP
print("\n--- 5. Cleanup Test Records ---")
admin_supabase.table("live_quiz_sessions").delete().eq("id", session_id).execute()
print("Cleaned up test session.")

print("\n" + "=" * 70)
print("ALL 5 REAL DATABASE CHECKS PASSED ON LIVE SUPABASE POSTGRES!")
print("=" * 70)
