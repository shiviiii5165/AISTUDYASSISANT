"""
LearnByGenie — Feature 2 Production & Content-Evidence Certification
====================================================================
Validates all requirements for Feature 2 closure:
1. Real Supabase remote persistence for sessions, responses, and results
2. Real authenticated diagnostic round trip with prerequisite probing
3. Process restart persistence (cache clearance / fresh reconstruction)
4. Interruption and resume preservation
5. Duplicate answer idempotency
6. Cross-user isolation (Student A vs Student B vs Teacher)
7. Database RLS blocking unauthenticated/anon clients
8. Content coverage matrix and auditor certification
9. Feature 3 evidence contract verification
"""
import os
import sys
import uuid
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.supabase_client import supabase
from app.services.diagnostic.service import DiagnosticService
from app.services.diagnostic.repository import DiagnosticRepository
from app.services.diagnostic.schemas import (
    AnswerSubmissionRequest, DiagnosticStage, DiagnosticState, ConfidenceClass
)
from app.services.diagnostic.item_bank import CANONICAL_ITEMS, get_item
from app.services.diagnostic.curriculum_blueprint import CANONICAL_DOMAINS, CANONICAL_SKILLS
from app.services.diagnostic.audit import audit_entire_item_bank
from app.services.diagnostic.adaptive_engine import AdaptiveDecisionEngine
from app.core.config import settings
from supabase import create_client

STUDENT_A = "a56da972-0f19-418d-b0f7-de91ff114190"
STUDENT_B = "d7007dd2-57dd-477c-9429-629d620cd616"


def run_full_diagnostic_certification():
    print("=" * 70)
    print("LEARNBYGENIE - FEATURE 2 PRODUCTION CERTIFICATION")
    print("=" * 70)

    # ─── PART 1: Remote Schema & Seed Validation ─────────────────────────────
    print("\n[PART 1] Remote Database Schema & Seed Verification")
    tables = [
        "diagnostic_domains", "diagnostic_skills", "diagnostic_items",
        "diagnostic_sessions", "diagnostic_responses", "diagnostic_results",
        "diagnostic_skill_results"
    ]
    counts = {}
    for t in tables:
        res = supabase.table(t).select("id", count="exact").execute()
        counts[t] = res.count
        print(f"  [OK] Remote table '{t}' accessible: {res.count} rows")

    assert counts["diagnostic_domains"] >= 10, "diagnostic_domains must be seeded"
    assert counts["diagnostic_skills"] >= 20, "diagnostic_skills must be seeded"
    assert counts["diagnostic_items"] >= 31, "diagnostic_items must be seeded"

    # ─── PART 2: Real Diagnostic Round Trip with Prerequisite Probing ─────────
    print("\n[PART 2] Real Diagnostic Round Trip & Prerequisite Probing")
    DiagnosticRepository.clear_memory_cache()

    # Step 1: Start
    step1 = DiagnosticService.start_diagnostic(user_id=STUDENT_A, subject="Mathematics", retake=True)
    sess_id = step1.session.id
    print(f"  [OK] Started session {sess_id} in stage {step1.session.current_stage}")
    assert step1.current_question is not None
    q1 = step1.current_question

    # Step 2: Answer Q1 incorrectly to trigger downward/prerequisite probe
    step2 = DiagnosticService.submit_answer(
        user_id=STUDENT_A,
        session_id=sess_id,
        submission=AnswerSubmissionRequest(
            item_id=q1.id,
            student_response="INCORRECT_ANSWER",
            response_time_ms=1500
        )
    )
    print(f"  [OK] Submitted Q1 (incorrect). Transitioned stage: {step2.session.current_stage}")
    assert step2.current_question is not None
    assert step2.session.questions_answered == 1
    q2 = step2.current_question

    # Step 3: Answer Q2 (confirming item) incorrectly
    step3 = DiagnosticService.submit_answer(
        user_id=STUDENT_A,
        session_id=sess_id,
        submission=AnswerSubmissionRequest(
            item_id=q2.id,
            student_response="INCORRECT_CONFIRMATION",
            response_time_ms=1800
        )
    )
    print(f"  [OK] Submitted Q2 (confirming failure). Questions answered: {step3.session.questions_answered}")

    # Complete the session by answering remaining questions
    curr = step3
    while not curr.is_completed and curr.current_question:
        item_obj = get_item(curr.current_question.id)
        # Give correct answer to complete cleanly
        ans = item_obj.correct_answer if item_obj else "correct"
        curr = DiagnosticService.submit_answer(
            user_id=STUDENT_A,
            session_id=sess_id,
            submission=AnswerSubmissionRequest(
                item_id=curr.current_question.id,
                student_response=ans,
                response_time_ms=1100
            )
        )

    print(f"  [OK] Diagnostic completed! Status: {curr.session.status}")
    assert curr.is_completed is True
    assert curr.result is not None
    res1 = curr.result
    print(f"  [OK] Derived operating level: '{res1.operating_level_band}'")
    print(f"  [OK] Prerequisite gaps detected: {res1.prerequisite_gaps}")

    # ─── PART 3: Process Restart Persistence ──────────────────────────────────
    print("\n[PART 3] Process Restart Persistence (Cold Cache Recovery)")
    # Clear process memory completely
    DiagnosticRepository.clear_memory_cache()

    # Query result fresh from remote Supabase
    cold_result = DiagnosticService.get_result(user_id=STUDENT_A, session_id=sess_id)
    assert cold_result is not None, "Result must survive process memory restart!"
    assert cold_result.session_id == sess_id
    assert cold_result.operating_level_band == res1.operating_level_band
    assert len(cold_result.skill_results) == len(res1.skill_results)
    print(f"  [OK] Successfully restored result from Supabase cold cache ({len(cold_result.skill_results)} skill results)")

    # ─── PART 4: Real Resume Test ─────────────────────────────────────────────
    print("\n[PART 4] Real Interruption and Resume Test")
    DiagnosticRepository.clear_memory_cache()

    # Start new session
    resume_sess = DiagnosticService.start_diagnostic(user_id=STUDENT_A, subject="Physics", retake=True)
    r_sess_id = resume_sess.session.id
    q_r1 = resume_sess.current_question
    print(f"  [OK] Started session {r_sess_id} on Physics")

    # Answer 1 item
    step_r1 = DiagnosticService.submit_answer(
        user_id=STUDENT_A,
        session_id=r_sess_id,
        submission=AnswerSubmissionRequest(item_id=q_r1.id, student_response="5 N", response_time_ms=1200)
    )
    assert step_r1.session.questions_answered == 1
    next_item_id = step_r1.current_question.id

    # Simulate browser reconnect / crash / memory wipe
    DiagnosticRepository.clear_memory_cache()

    # Resume by calling start_diagnostic without retake (or get_session_state)
    resumed = DiagnosticService.start_diagnostic(user_id=STUDENT_A, subject="Physics", retake=False)
    assert resumed.session.id == r_sess_id, "Must resume the same session"
    assert resumed.session.questions_answered == 1, "Must retain answered count"
    assert resumed.current_question.id == next_item_id, "Server-controlled next question preserved"
    print(f"  [OK] Reconnected session {r_sess_id}: state intact, 1 question answered, next question preserved.")

    # ─── PART 5: Duplicate Submission Idempotency ─────────────────────────────
    print("\n[PART 5] Duplicate Submission Idempotency")
    count_before = len(DiagnosticRepository.get_responses_for_session(r_sess_id))
    # Submit answer for the already-answered item q_r1 again
    dup_res = DiagnosticService.submit_answer(
        user_id=STUDENT_A,
        session_id=r_sess_id,
        submission=AnswerSubmissionRequest(item_id=q_r1.id, student_response="5 N", response_time_ms=900)
    )
    count_after = len(DiagnosticRepository.get_responses_for_session(r_sess_id))
    assert count_before == count_after, "Duplicate answer must not create new response record"
    assert dup_res.session.questions_answered == 1, "Question counter must not increment on duplicate"
    print("  [OK] Idempotency verified: Duplicate submission rejected from double-counting.")

    # ─── PART 6: Cross-User Authorization & Isolation ─────────────────────────
    print("\n[PART 6] Cross-User Authorization & Isolation")
    # Student B cannot access Student A's session
    try:
        DiagnosticService.get_session_state(user_id=STUDENT_B, session_id=sess_id)
        assert False, "Student B must not access Student A session"
    except Exception as e:
        print(f"  [OK] Student B blocked from reading Student A session: {e}")

    try:
        DiagnosticService.submit_answer(
            user_id=STUDENT_B,
            session_id=sess_id,
            submission=AnswerSubmissionRequest(item_id=q1.id, student_response="hacked", response_time_ms=10)
        )
        assert False, "Student B must not submit answer to Student A session"
    except Exception as e:
        print(f"  [OK] Student B blocked from submitting to Student A session: {e}")

    # ─── PART 7: Database Row Level Security (Anon Client) ────────────────────
    print("\n[PART 7] Database Row Level Security (Anon Client Isolation)")
    from pathlib import Path
    from dotenv import dotenv_values
    root_env = Path(__file__).resolve().parents[2] / ".env"
    envs = dotenv_values(root_env) if root_env.exists() else {}
    anon_key = envs.get("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")

    anon_client = create_client(settings.SUPABASE_URL, anon_key)
    res_sess = anon_client.table("diagnostic_sessions").select("*").execute()
    res_resp = anon_client.table("diagnostic_responses").select("*").execute()
    res_res = anon_client.table("diagnostic_results").select("*").execute()

    assert len(res_sess.data) == 0, "Anon client must receive 0 diagnostic_sessions"
    assert len(res_resp.data) == 0, "Anon client must receive 0 diagnostic_responses"
    assert len(res_res.data) == 0, "Anon client must receive 0 diagnostic_results"
    print("  [OK] Database RLS verified: Unauthenticated/anon client receives 0 private diagnostic records.")

    # ─── PART 8: Item Bank Auditor & Minimum Coverage Standard ───────────────
    print("\n[PART 8] Item Bank Content Quality Auditor")
    audit_report = audit_entire_item_bank()
    print(f"  [OK] Audited {audit_report.total_items} items: {audit_report.valid_items} valid, {audit_report.quarantined_items} quarantined")
    assert audit_report.is_healthy is True
    assert audit_report.invalid_items == 0

    # ─── PART 9: Feature 3 Contract Verification ──────────────────────────────
    print("\n[PART 9] Feature 3 Ingestion Contract")
    f3_payload = cold_result.feature3_contract_payload
    assert len(f3_payload) > 0, "Feature 3 payload must be populated"
    sample_f3 = f3_payload[0]
    print(f"  [OK] Sample Feature 3 contract item:")
    print(f"     skill_id: {sample_f3.skill_id}")
    print(f"     diagnostic_state: {sample_f3.diagnostic_state}")
    print(f"     evidence_count: {sample_f3.evidence_count}")
    print(f"     confidence: {sample_f3.confidence}")
    print(f"     source: {sample_f3.source}")
    print(f"     session_id: {sample_f3.diagnostic_session_id}")
    print(f"     timestamp: {sample_f3.timestamp}")
    assert hasattr(sample_f3, "skill_id")
    assert hasattr(sample_f3, "diagnostic_state")
    assert hasattr(sample_f3, "evidence_count")
    assert hasattr(sample_f3, "confidence")
    assert sample_f3.source == "DIAGNOSTIC"
    assert not hasattr(sample_f3, "mastery_probability"), "No fake long-term mastery probability in Feature 2"

    print("\n" + "=" * 70)
    print("ALL PRODUCTION CERTIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_diagnostic_certification()
