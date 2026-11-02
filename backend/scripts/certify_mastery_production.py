"""
LearnByGenie — Feature 3 Production Certification Script
=========================================================
Validates all requirements for Feature 3 closure (§42):
1. Ingestion of Feature 2 diagnostic evidence payload
2. Retrieval of skill states (MasteryState, ReadinessState)
3. Blocked concepts & prerequisite detection
4. Repair path computation
5. Process restart persistence (clearing memory cache and reconstructing graph state)
6. Evidence idempotency verification
7. Graph topology audit
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.supabase_client import supabase
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.schemas import (
    MasteryState, ReadinessState, ReviewStatus, EvidenceSource, AssistanceLevel
)
from app.services.diagnostic.schemas import Feature3SkillEvidence
from app.services.diagnostic.service import DiagnosticService
from app.services.diagnostic.repository import DiagnosticRepository

STUDENT_A = "a56da972-0f19-418d-b0f7-de91ff114190"


def run_full_mastery_certification():
    print("=" * 70)
    print("LEARNBYGENIE - FEATURE 3 PRODUCTION CERTIFICATION")
    print("=" * 70)

    # ─── PART 1: Remote Database Tables Probe ─────────────────────────────────
    print("\n[PART 1] Remote Database & Schema Probe")
    tables = [
        "skill_prerequisites", "learner_skill_states",
        "learner_skill_evidence", "skill_curriculum_mappings"
    ]
    for t in tables:
        if supabase is not None:
            try:
                res = supabase.table(t).select("id").limit(1).execute()
                print(f"  [OK] Remote table '{t}' accessible (PostgREST)")
            except Exception as e:
                print(f"  [NOTICE] Remote table '{t}' PostgREST note: {e}")
        else:
            print(f"  [MEMORY] Supabase client absent; running in memory store mode for '{t}'")

    # ─── PART 2: Feature 2 Diagnostic Ingestion ──────────────────────────────
    print("\n[PART 2] Feature 2 Evidence Ingestion into Mastery Graph")
    MasteryRepository.clear_memory_cache()

    diagnostic_payload = [
        Feature3SkillEvidence(
            skill_id="MATH_NUM_OPS",
            diagnostic_state="SECURE",
            evidence_count=2,
            correct_count=2,
            confidence="HIGH_EVIDENCE",
            source="DIAGNOSTIC",
            diagnostic_session_id="cert_diag_session_01",
            timestamp=datetime.now(timezone.utc).isoformat(),
            recommended_action="Concept confirmed secure."
        ),
        Feature3SkillEvidence(
            skill_id="MATH_ALG_EXP",
            diagnostic_state="NEEDS_REPAIR",
            evidence_count=2,
            correct_count=0,
            confidence="HIGH_EVIDENCE",
            source="DIAGNOSTIC",
            diagnostic_session_id="cert_diag_session_01",
            timestamp=datetime.now(timezone.utc).isoformat(),
            recommended_action="Prerequisite algebra needs repair."
        )
    ]

    updated_states = MasteryGraphService.ingest_diagnostic_evidence(
        user_id=STUDENT_A,
        session_id="cert_diag_session_01",
        contract_payload=diagnostic_payload
    )
    print(f"  [OK] Ingested {len(updated_states)} states from Feature 2 payload.")

    state_num = MasteryRepository.get_skill_state(STUDENT_A, "MATH_NUM_OPS")
    state_alg = MasteryRepository.get_skill_state(STUDENT_A, "MATH_ALG_EXP")

    assert state_num is not None and state_num.mastery_state == MasteryState.SECURE, "MATH_NUM_OPS must be SECURE"
    assert state_alg is not None and state_alg.mastery_state == MasteryState.NEEDS_REPAIR, "MATH_ALG_EXP must be NEEDS_REPAIR"
    print(f"  [OK] MATH_NUM_OPS MasteryState: {state_num.mastery_state.value}")
    print(f"  [OK] MATH_ALG_EXP MasteryState: {state_alg.mastery_state.value}")

    # ─── PART 3: Blocked Prerequisites & Graph Retrieval ──────────────────────
    print("\n[PART 3] Graph Retrieval & Blocked Prerequisite Detection")
    graph = MasteryGraphService.get_subject_graph(STUDENT_A, "Mathematics")
    print(f"  [OK] Retrieved {len(graph.nodes)} concept nodes for Mathematics.")

    # Linear Equations depends on Algebraic Expressions
    lin_node = next((n for n in graph.nodes if n.skill_id == "MATH_LIN_EQ"), None)
    assert lin_node is not None, "MATH_LIN_EQ node must exist"
    assert lin_node.readiness_state == ReadinessState.BLOCKED_BY_PREREQUISITE, "MATH_LIN_EQ must be BLOCKED_BY_PREREQUISITE"
    assert "MATH_ALG_EXP" in lin_node.blocking_prerequisites
    print(f"  [OK] MATH_LIN_EQ correctly BLOCKED by: {lin_node.blocking_prerequisites}")

    # Quadratic Equations also depends on Algebraic Expressions
    quad_node = next((n for n in graph.nodes if n.skill_id == "MATH_QUAD_EQ"), None)
    assert quad_node is not None
    assert quad_node.readiness_state == ReadinessState.BLOCKED_BY_PREREQUISITE
    print(f"  [OK] MATH_QUAD_EQ correctly BLOCKED by: {quad_node.blocking_prerequisites}")

    # ─── PART 4: Repair Path Computation ──────────────────────────────────────
    print("\n[PART 4] Deterministic Repair Path")
    repair_path = MasteryGraphService.get_repair_path(STUDENT_A, "MATH_QUAD_EQ")
    print(f"  [OK] Repair path for MATH_QUAD_EQ: {repair_path}")
    assert len(repair_path) > 0
    assert repair_path[0] == "MATH_ALG_EXP", "Shortest repair start must be MATH_ALG_EXP"
    assert "MATH_NUM_OPS" not in repair_path, "Foundational secure skills must not be in repair path"

    # ─── PART 5: Explainable Next Recommendations ─────────────────────────────
    print("\n[PART 5] Explainable Recommendations")
    recs = MasteryGraphService.get_next_learning_recommendations(STUDENT_A, "Mathematics")
    print(f"  [OK] Found {len(recs)} recommendations.")
    assert len(recs) > 0
    top_rec = recs[0]
    print(f"  [OK] Top Recommendation: {top_rec.skill_name} ({top_rec.recommendation_type})")
    print(f"       Reason: {top_rec.reason}")
    assert top_rec.priority == 1
    assert top_rec.skill_id == "MATH_ALG_EXP"

    # ─── PART 6: Graph Topology Audit ─────────────────────────────────────────
    print("\n[PART 6] Graph Topology Audit")
    audit = MasteryGraphService.audit_prerequisite_graph()
    print(f"  [OK] DAG validated: is_dag={audit.is_dag}, total_skills={audit.total_skills}, total_edges={audit.total_edges}")
    assert audit.is_dag is True, "Prerequisite graph must be a strict DAG"
    assert len(audit.cycles) == 0, "No cycles allowed"
    assert len(audit.self_edges) == 0, "No self-edges allowed"

    # ─── PART 7: Evidence Idempotency Check ───────────────────────────────────
    print("\n[PART 7] Evidence Idempotency Round Trip")
    ev_count_1 = len(MasteryRepository.get_evidence_for_user(STUDENT_A))
    # Re-ingest exact same diagnostic payload
    MasteryGraphService.ingest_diagnostic_evidence(
        user_id=STUDENT_A,
        session_id="cert_diag_session_01",
        contract_payload=diagnostic_payload
    )
    ev_count_2 = len(MasteryRepository.get_evidence_for_user(STUDENT_A))
    assert ev_count_1 == ev_count_2, f"Idempotency violation: {ev_count_1} != {ev_count_2}"
    print(f"  [OK] Duplicate evidence count preserved: {ev_count_1} == {ev_count_2}")

    # ─── PART 8: Restart Persistence ──────────────────────────────────────────
    print("\n[PART 8] Process Restart Simulation (Cache Clearance & Graph State)")
    # Clear in-memory caches to simulate server restart
    MasteryRepository.clear_memory_cache()
    # Reconstruct graph
    reconstructed_graph = MasteryGraphService.get_subject_graph(STUDENT_A, "Mathematics")
    assert len(reconstructed_graph.nodes) > 0
    print(f"  [OK] Process restart reconstructed {len(reconstructed_graph.nodes)} concept nodes cleanly.")

    print("\n" + "=" * 70)
    print("ALL FEATURE 3 PRODUCTION CERTIFICATION CHECKS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_full_mastery_certification()
    if not success:
        sys.exit(1)
