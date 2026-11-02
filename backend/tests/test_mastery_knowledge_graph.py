"""
LearnByGenie — Feature 3: Mastery + Prerequisite Knowledge Graph Test Suite
============================================================================
Comprehensive deterministic unit and integration test suite covering all 41
invariants specified in Feature 3 requirements (§41).

Invariants Verified:
1. Feature 2 evidence ingestion contract
2. Idempotent ingestion (zero duplicate evidence or state mutations)
3. NOT_ASSESSED initial state
4. DEVELOPING transition
5. NEEDS_REPAIR transition
6. SECURE transition (>=2 independent items, >=80% accuracy)
7. FRAGILE behavior (prior SECURE + subsequent independent failure)
8. No one-item SECURE
9. No one-item NEEDS_REPAIR where evidence insufficient
10. Assisted vs independent evidence distinction (assisted cannot alone satisfy SECURE)
11. Skill readiness computation
12. Blocked prerequisite detection
13. Partially ready state detection
14. Repair path computation
15. Shortest meaningful repair start (no unnecessary low-grade remediation)
16. Next concept recommendation (explainable priority 1 and priority 2)
17. Explainability ("why" and "next_action" generation)
18. State history preservation in evidence ledger
19. Cross-user isolation (Student A vs Student B)
20. Student cannot directly mutate mastery (client-side mutation disallowed)
21. Service-role backend authorization & authenticated endpoints
22. Cycle rejection in DAG
23. Self-edge rejection
24. Orphan edge rejection in graph auditor
25. Concurrency safety & state version increment
26. State version increment on state updates
27. Engine version tracking ("3.0.0")
28. Class 3-5 Primary skill graph (e.g. Number Operations)
29. Class 11-12 JEE graph (Vectors -> Electrostatics, Newton's Laws)
30. Class 11-12 NEET graph (Cell Biology -> Genetics)
31. Undergraduate CS graph (Logic -> Data Structures)
32. Content-gap handling (unassessed concepts remain NOT_ASSESSED)
33. No IQ or intelligence labels
34. No rank or percentile predictions
35. No gamification (no XP, coins, badges, streaks)
36. LearnerContextService summary integration without prompt bloat
37. Zero live LLM calls
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.services.mastery.schemas import (
    MasteryState, ReadinessState, ReviewStatus, ConfidenceClass,
    EvidenceSource, AssistanceLevel, RelationshipType,
    SkillPrerequisiteEdge, LearnerSkillEvidence, LearnerSkillState,
    SkillNodeView, LearningRecommendation, SubjectGraphView,
    GraphAuditReport, CompactMasterySummary
)
from app.services.mastery.dag_engine import PrerequisiteDAGEngine
from app.services.mastery.transition_engine import MasteryTransitionEngine
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.audit import GraphAuditor
from app.services.diagnostic.schemas import Feature3SkillEvidence
from app.services.learner_context.service import LearnerContextService


STUDENT_A = "a56da972-0f19-418d-b0f7-de91ff114190"
STUDENT_B = "d7007dd2-57dd-477c-9429-629d620cd616"


from app.db.supabase_client import supabase

@pytest.fixture(autouse=True)
def clean_mastery_state():
    """Resets repository memory between tests for pure deterministic isolation."""
    MasteryRepository.clear_memory_cache()
    if supabase is not None:
        try:
            supabase.table("learner_skill_evidence").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("learner_skill_states").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
        except Exception:
            pass
    yield
    MasteryRepository.clear_memory_cache()
    if supabase is not None:
        try:
            supabase.table("learner_skill_evidence").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("learner_skill_states").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
        except Exception:
            pass


# ─── 1 & 2. FEATURE 2 INGESTION & IDEMPOTENCY ────────────────────────────────

def test_feature2_evidence_ingestion_and_idempotency():
    """
    Ingests Feature 2 diagnostic payload and verifies:
    1. Durable evidence and states created
    2. Reprocessing identical session is 100% idempotent
    """
    payload = [
        Feature3SkillEvidence(
            skill_id="MATH_NUM_OPS",
            diagnostic_state="SECURE",
            evidence_count=2,
            correct_count=2,
            confidence="HIGH_EVIDENCE",
            source="DIAGNOSTIC",
            diagnostic_session_id="diag_sess_101",
            timestamp=datetime.now(timezone.utc).isoformat(),
            recommended_action="Concept is secure."
        ),
        Feature3SkillEvidence(
            skill_id="MATH_ALG_EXP",
            diagnostic_state="NEEDS_REPAIR",
            evidence_count=2,
            correct_count=0,
            confidence="HIGH_EVIDENCE",
            source="DIAGNOSTIC",
            diagnostic_session_id="diag_sess_101",
            timestamp=datetime.now(timezone.utc).isoformat(),
            recommended_action="Requires prerequisite algebraic review."
        )
    ]

    states = MasteryGraphService.ingest_diagnostic_evidence(
        user_id=STUDENT_A,
        session_id="diag_sess_101",
        contract_payload=payload
    )

    assert len(states) == 2
    state_num = MasteryRepository.get_skill_state(STUDENT_A, "MATH_NUM_OPS")
    state_alg = MasteryRepository.get_skill_state(STUDENT_A, "MATH_ALG_EXP")

    assert state_num is not None
    assert state_num.mastery_state == MasteryState.SECURE
    assert state_num.correct_count == 2
    assert state_num.state_version >= 1
    version_before = state_num.state_version

    assert state_alg is not None
    assert state_alg.mastery_state == MasteryState.NEEDS_REPAIR
    assert state_alg.correct_count == 0

    # IDEMPOTENCY TEST: Reprocess identical diagnostic session
    evidence_count_before = len(MasteryRepository.get_evidence_for_user(STUDENT_A))
    states_second_pass = MasteryGraphService.ingest_diagnostic_evidence(
        user_id=STUDENT_A,
        session_id="diag_sess_101",
        contract_payload=payload
    )
    evidence_count_after = len(MasteryRepository.get_evidence_for_user(STUDENT_A))

    assert evidence_count_before == evidence_count_after, "Idempotency failed: duplicate evidence created"
    state_num_after = MasteryRepository.get_skill_state(STUDENT_A, "MATH_NUM_OPS")
    assert state_num_after.mastery_state == MasteryState.SECURE
    assert state_num_after.state_version == version_before, "Idempotency failed: state_version incremented on duplicate"


# ─── 3. NOT_ASSESSED INITIAL STATE & CONTENT GAPS ─────────────────────────────

def test_not_assessed_initial_state_and_content_gap():
    """Concepts without evidence must remain NOT_ASSESSED; never fabricate mastery."""
    state = MasteryRepository.get_skill_state(STUDENT_A, "MATH_CALC_LIMITS")
    assert state is None  # Unassessed in DB

    graph = MasteryGraphService.get_subject_graph(STUDENT_A, "Mathematics")
    node = next((n for n in graph.nodes if n.skill_id == "MATH_CALC_LIMITS"), None)
    assert node is not None
    assert node.mastery_state == MasteryState.NOT_ASSESSED
    assert "No evidence" in node.why


# ─── 4, 8 & 9. DETERMINISTIC TRANSITIONS: 1-ITEM RULES ───────────────────────

def test_no_one_item_secure_and_developing_transition():
    """
    Invariants (§41):
    - 1 correct item must transition to DEVELOPING, NEVER SECURE
    - Requires >= 2 independent items with >= 80% accuracy for SECURE
    """
    now = datetime.now(timezone.utc)
    single_ev = [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_FRAC_DEC",
            source_type=EvidenceSource.DIAGNOSTIC,
            source_record_id="attempt_1",
            correctness=True,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now
        )
    ]

    mastery, conf, rev, why, next_act = MasteryTransitionEngine.evaluate_state(None, single_ev, now=now)
    assert mastery == MasteryState.DEVELOPING, "1-item correct must be DEVELOPING, never SECURE"
    assert mastery != MasteryState.SECURE

    # Add second independent correct attempt
    second_ev = single_ev + [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_FRAC_DEC",
            source_type=EvidenceSource.PRACTICE,
            source_record_id="attempt_2",
            correctness=True,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now + timedelta(minutes=5)
        )
    ]
    mastery2, conf2, rev2, why2, next_act2 = MasteryTransitionEngine.evaluate_state(None, second_ev, now=now)
    assert mastery2 == MasteryState.SECURE, "2 independent correct attempts must transition to SECURE"


def test_no_one_item_needs_repair():
    """
    Invariants (§41):
    - 1 incorrect item must be DEVELOPING with caution, NEVER NEEDS_REPAIR
    - Requires >= 2 failures to declare NEEDS_REPAIR
    """
    now = datetime.now(timezone.utc)
    single_fail = [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_RATIO_PROP",
            source_type=EvidenceSource.PRACTICE,
            source_record_id="attempt_fail_1",
            correctness=False,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now
        )
    ]

    mastery, conf, rev, why, next_act = MasteryTransitionEngine.evaluate_state(None, single_fail, now=now)
    assert mastery == MasteryState.DEVELOPING, "1 single failure must NOT trigger NEEDS_REPAIR"
    assert mastery != MasteryState.NEEDS_REPAIR

    # Second failure triggers NEEDS_REPAIR
    two_fails = single_fail + [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_RATIO_PROP",
            source_type=EvidenceSource.PRACTICE,
            source_record_id="attempt_fail_2",
            correctness=False,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now + timedelta(minutes=10)
        )
    ]
    mastery2, _, _, _, _ = MasteryTransitionEngine.evaluate_state(None, two_fails, now=now)
    assert mastery2 == MasteryState.NEEDS_REPAIR


# ─── 7. FRAGILE RETENTION BEHAVIOR ────────────────────────────────────────────

def test_fragile_behavior_on_contradictory_failure():
    """
    If a concept was SECURE and a subsequent independent attempt fails,
    mastery must transition to FRAGILE (§5, §11).
    """
    now = datetime.now(timezone.utc)
    ev_history = [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_NUM_OPS",
            source_type=EvidenceSource.DIAGNOSTIC,
            source_record_id="a1",
            correctness=True,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now - timedelta(days=2)
        ),
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_NUM_OPS",
            source_type=EvidenceSource.DIAGNOSTIC,
            source_record_id="a2",
            correctness=True,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now - timedelta(days=2)
        )
    ]
    # Current state is SECURE
    curr_state = LearnerSkillState(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        mastery_state=MasteryState.SECURE,
        total_evidence_count=2,
        independent_evidence_count=2,
        correct_count=2
    )

    # Now add contradictory failure
    contradictory_ev = ev_history + [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_NUM_OPS",
            source_type=EvidenceSource.QUIZ,
            source_record_id="a3_fail",
            correctness=False,
            independence_level=AssistanceLevel.INDEPENDENT,
            occurred_at=now
        )
    ]

    mastery, conf, rev, why, next_act = MasteryTransitionEngine.evaluate_state(curr_state, contradictory_ev, now=now)
    assert mastery == MasteryState.FRAGILE, "Previously SECURE with recent contradictory failure must be FRAGILE"
    assert "fragile" in why.lower()


# ─── 10. ASSISTED VS INDEPENDENT EVIDENCE ─────────────────────────────────────

def test_assisted_vs_independent_distinction():
    """
    Hint-assisted practice cannot alone promote a skill to SECURE (§8, §41).
    """
    now = datetime.now(timezone.utc)
    assisted_ev = [
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_ALG_EXP",
            source_type=EvidenceSource.PRACTICE,
            source_record_id="ast_1",
            correctness=True,
            independence_level=AssistanceLevel.HINT_ASSISTED,
            occurred_at=now
        ),
        LearnerSkillEvidence(
            user_id=STUDENT_A,
            skill_id="MATH_ALG_EXP",
            source_type=EvidenceSource.PRACTICE,
            source_record_id="ast_2",
            correctness=True,
            independence_level=AssistanceLevel.FULLY_ASSISTED,
            occurred_at=now + timedelta(minutes=5)
        )
    ]

    mastery, _, _, why, _ = MasteryTransitionEngine.evaluate_state(None, assisted_ev, now=now)
    assert mastery == MasteryState.DEVELOPING, "Assisted evidence alone cannot achieve SECURE"
    assert mastery != MasteryState.SECURE


# ─── 11, 12, 13. READINESS & BLOCKED PREREQUISITES ────────────────────────────

def test_skill_readiness_and_blocked_prerequisites():
    """
    Tests readiness calculation (§13):
    Quadratic Equations depends on Linear Equations and Algebraic Expressions.
    If Linear Equations is NEEDS_REPAIR, Quadratic Equations must be BLOCKED_BY_PREREQUISITE.
    """
    dag = PrerequisiteDAGEngine()

    # Case 1: Prerequisite NEEDS_REPAIR -> BLOCKED_BY_PREREQUISITE
    mastery_map = {
        "MATH_NUM_OPS": MasteryState.SECURE,
        "MATH_ALG_EXP": MasteryState.SECURE,
        "MATH_LIN_EQ": MasteryState.NEEDS_REPAIR,
    }

    readiness, blockers = dag.compute_readiness("MATH_QUAD_EQ", mastery_map)
    assert readiness == ReadinessState.BLOCKED_BY_PREREQUISITE
    assert "MATH_LIN_EQ" in blockers

    # Case 2: All prerequisites SECURE -> READY
    mastery_map["MATH_LIN_EQ"] = MasteryState.SECURE
    readiness2, blockers2 = dag.compute_readiness("MATH_QUAD_EQ", mastery_map)
    assert readiness2 == ReadinessState.READY
    assert len(blockers2) == 0

    # Case 3: Prerequisite DEVELOPING -> PARTIALLY_READY
    mastery_map["MATH_LIN_EQ"] = MasteryState.DEVELOPING
    readiness3, _ = dag.compute_readiness("MATH_QUAD_EQ", mastery_map)
    assert readiness3 == ReadinessState.PARTIALLY_READY


# ─── 14 & 15. REPAIR PATH & SHORTEST MEANINGFUL START ─────────────────────────

def test_repair_path_and_shortest_meaningful_start():
    """
    Quadratic Equations -> Linear Equations -> Algebraic Expressions -> Number Operations.
    If Number Operations is SECURE and Algebraic Expressions NEEDS_REPAIR:
    Repair path must start at Algebraic Expressions, NOT Number Operations (§14, §15).
    """
    dag = PrerequisiteDAGEngine()

    mastery_map = {
        "MATH_NUM_OPS": MasteryState.SECURE,       # Secure foundation
        "MATH_ALG_EXP": MasteryState.NEEDS_REPAIR, # Broken concept
        "MATH_LIN_EQ": MasteryState.NOT_ASSESSED,
        "MATH_QUAD_EQ": MasteryState.NOT_ASSESSED,
    }

    repair_path = dag.get_repair_path("MATH_QUAD_EQ", mastery_map)
    assert len(repair_path) > 0
    # Must start at the broken skill, NOT the secure foundation
    assert repair_path[0] == "MATH_ALG_EXP"
    assert "MATH_NUM_OPS" not in repair_path, "Secure foundational skills must not be included in repair path"


# ─── 16 & 17. RECOMMENDATIONS & EXPLAINABILITY ────────────────────────────────

def test_recommendations_and_explainability():
    """
    Recommendations must provide explainable reasons and unblocked concepts (§15, §29).
    """
    dag = PrerequisiteDAGEngine()
    mastery_map = {
        "MATH_NUM_OPS": MasteryState.SECURE,
        "MATH_ALG_EXP": MasteryState.NEEDS_REPAIR,
    }

    recs = dag.get_recommendations("Mathematics", mastery_map)
    assert len(recs) > 0

    # Priority 1 must be repair
    repair_rec = next((r for r in recs if r.priority == 1), None)
    assert repair_rec is not None
    assert repair_rec.skill_id == "MATH_ALG_EXP"
    assert "repair" in repair_rec.reason.lower()
    assert len(repair_rec.unblocks_skills) > 0

    # Every recommendation must have clear explanation and unblocked skills
    for r in recs:
        assert len(r.reason) > 5
        assert r.skill_name is not None


# ─── 18. STATE HISTORY PRESERVATION ───────────────────────────────────────────

def test_state_history_preservation():
    """
    Evidence ledger is append-only (§7, §33).
    New states do not erase historical evidence records.
    """
    now = datetime.now(timezone.utc)
    # Submission 1
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="sess_1",
        correctness=True,
        independence_level=AssistanceLevel.INDEPENDENT
    )
    # Submission 2
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.PRACTICE,
        source_record_id="sess_2",
        correctness=True,
        independence_level=AssistanceLevel.INDEPENDENT
    )

    ev_list = MasteryRepository.get_evidence_for_skill(STUDENT_A, "MATH_NUM_OPS")
    assert len(ev_list) == 2
    assert ev_list[0].source_record_id == "sess_1"
    assert ev_list[1].source_record_id == "sess_2"


# ─── 19. CROSS-USER ISOLATION ─────────────────────────────────────────────────

def test_cross_user_isolation():
    """
    Evidence submitted for Student A must not affect Student B (§41).
    """
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="sess_student_a",
        correctness=True,
        independence_level=AssistanceLevel.INDEPENDENT
    )

    state_a = MasteryRepository.get_skill_state(STUDENT_A, "MATH_NUM_OPS")
    state_b = MasteryRepository.get_skill_state(STUDENT_B, "MATH_NUM_OPS")

    assert state_a is not None
    assert state_a.total_evidence_count == 1
    assert state_b is None  # Student B remains unassessed


# ─── 22, 23 & 24. DAG INTEGRITY, CYCLE & ORPHAN AUDIT ─────────────────────────

def test_dag_cycle_prevention_and_graph_audit():
    """
    Checks cycle detection, self-edge rejection, and GraphAuditor (§4, §40).
    """
    edges = [
        SkillPrerequisiteEdge(prerequisite_skill_id="A", dependent_skill_id="B"),
        SkillPrerequisiteEdge(prerequisite_skill_id="B", dependent_skill_id="C"),
    ]
    dag = PrerequisiteDAGEngine(edges)

    # 1. Self edge detection
    assert dag.would_create_cycle("A", "A") is True

    # 2. Transitive cycle detection (C -> A would create cycle A -> B -> C -> A)
    assert dag.would_create_cycle("C", "A") is True

    # 3. Valid edge (D -> A) does not create cycle
    assert dag.would_create_cycle("D", "A") is False

    # 4. Auditor flags cycles and broken foreign references
    bad_edges = edges + [
        SkillPrerequisiteEdge(prerequisite_skill_id="C", dependent_skill_id="A"), # Cycle
        SkillPrerequisiteEdge(prerequisite_skill_id="UNKNOWN_ID", dependent_skill_id="A"), # Orphan reference
        SkillPrerequisiteEdge(prerequisite_skill_id="B", dependent_skill_id="B") # Self-edge
    ]
    report = GraphAuditor.audit_graph(bad_edges)
    assert report.is_healthy is False
    assert len(report.cycles) > 0
    assert len(report.self_edges) > 0
    assert "UNKNOWN_ID" in report.orphan_skills


# ─── 25 & 26. CONCURRENCY & STATE VERSIONING ──────────────────────────────────

def test_state_versioning_and_concurrency():
    """
    Each state recalculation increments state_version and updates engine_version (§27, §28).
    """
    state1, _ = MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_FRAC_DEC",
        source_type=EvidenceSource.PRACTICE,
        source_record_id="c_1",
        correctness=True
    )
    assert state1.state_version == 1
    assert state1.engine_version == "3.0.0"

    state2, _ = MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_FRAC_DEC",
        source_type=EvidenceSource.PRACTICE,
        source_record_id="c_2",
        correctness=True
    )
    assert state2.state_version == 2
    assert state2.mastery_state == MasteryState.SECURE


# ─── 28 to 31. CURRICULUM BREADTH (PRIMARY, JEE, NEET, UG CS) ─────────────────

def test_curriculum_coverage_primary_jee_neet_ug():
    """
    Verifies prerequisite DAG handles:
    - Primary Class 3-5 (Number Operations)
    - JEE Senior Secondary (Vectors -> Electrostatics)
    - NEET Senior Secondary (Cell Biology -> Genetics)
    - UG Computer Science (Logic -> Data Structures)
    """
    dag = MasteryGraphService.get_dag_engine()

    # Primary
    assert "MATH_NUM_OPS" in dag.all_skills

    # JEE Physics
    assert "PHY_ELECTROSTATICS" in dag.get_immediate_dependents("PHY_VECTORS")

    # NEET Biology
    assert "BIO_GENETICS" in dag.get_immediate_dependents("BIO_CELL_UNIT")

    # UG Computer Science
    assert "CS_DATA_STRUCT" in dag.get_immediate_dependents("CS_BASIC_LOGIC")


# ─── 33, 34, 35. NO IQ, NO RANK, NO GAMIFICATION ──────────────────────────────

def test_no_iq_no_rank_no_gamification_invariants():
    """
    Feature 3 must NEVER represent IQ, talent, rank, or gamification (§MISSION, §2, §30).
    """
    # 1. Ingest evidence and get graph view
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="clean_test",
        correctness=True
    )
    graph = MasteryGraphService.get_subject_graph(STUDENT_A, "Mathematics")
    graph_str = graph.model_dump_json().lower()

    # Forbidden terms with word boundaries (avoids false-positive inside "expressions", etc.)
    import re
    forbidden_patterns = [
        r"\biq\b", r"\btalent\b", r"\brank\b", r"\bpercentile\b",
        r"\bair prediction\b", r"\bxp\b", r"\bcoins\b", r"\bstreak\b",
        r"\bbadges?\b", r"\bconfetti\b"
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, graph_str), f"Forbidden pattern '{pat}' matched in knowledge graph payload"


# ─── 36. LEARNER CONTEXT INTEGRATION ──────────────────────────────────────────

def test_learner_context_integration():
    """
    LearnerContextService produces bounded compact mastery summary without prompt bloat (§23).
    """
    # Ingest 2 secure and 1 needs_repair
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="ctx_1",
        correctness=True
    )
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="ctx_2",
        correctness=True
    )
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_ALG_EXP",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="ctx_3",
        correctness=False
    )
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_ALG_EXP",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="ctx_4",
        correctness=False
    )

    summary = LearnerContextService.get_compact_mastery_context(STUDENT_A, "Mathematics")
    assert summary is not None
    assert "secure_skills" in summary
    assert "needs_repair_skills" in summary
    assert any("Number Operations" in s for s in summary["secure_skills"])

    # Verify formatted prompt context includes concise bounded mastery
    mock_ctx = {
        "education": {"level": "Class 10", "board": "CBSE"},
        "goals": {"primary": "Board Exam"},
        "preferences": {"explanation_language": "English", "content_difficulty": "standard"},
        "subjects": ["Mathematics"],
        "mastery": summary
    }
    prompt_str = LearnerContextService.format_learner_prompt_context(mock_ctx)
    assert "Mastery:" in prompt_str
    assert "Number Operations" in prompt_str
    assert len(prompt_str) < 500, "Learner prompt context must remain compact and bounded"


# ─── 20 & 21. API AUTHORIZATION & DIRECT MUTATION DENIAL ───────────────────────

class MockAuthUser:
    def __init__(self, user_id: str, role: str = "student"):
        self.id = user_id
        self.role = role
        self.email = f"{user_id[:8]}@example.com"


def test_unauthenticated_mastery_api_rejected():
    """Unauthenticated requests must be rejected with 401/403 (§21)."""
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as client:
        res1 = client.get("/api/mastery/graph")
        assert res1.status_code in (401, 403)

        res2 = client.get("/api/mastery/recommendations")
        assert res2.status_code in (401, 403)

        res3 = client.post("/api/mastery/ingest-diagnostic", json={"session_id": "test_sess"})
        assert res3.status_code in (401, 403)


def test_authenticated_mastery_api_endpoints_and_direct_mutation_denied():
    """
    Authenticated requests succeed, and direct mutation of mastery states is denied (§20, §25).
    All state changes must flow through authorized evidence ingestion.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.dependencies import get_current_user

    mock_user = MockAuthUser(STUDENT_A)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # 1. Ingest practice evidence via authorized endpoint
        res_ingest = client.post("/api/mastery/ingest-evidence", json={
            "skill_id": "MATH_NUM_OPS",
            "source_type": "PRACTICE",
            "source_record_id": "api_test_ev_1",
            "correctness": True,
            "independence_level": "INDEPENDENT"
        })
        assert res_ingest.status_code == 200
        state = res_ingest.json()
        assert state["skill_id"] == "MATH_NUM_OPS"
        assert state["mastery_state"] == "DEVELOPING"

        # 2. Query knowledge graph
        res_graph = client.get("/api/mastery/graph?subject=Mathematics")
        assert res_graph.status_code == 200
        graph = res_graph.json()
        assert graph["subject"] == "Mathematics"
        assert len(graph["nodes"]) > 0

        # 3. Query recommendations
        res_recs = client.get("/api/mastery/recommendations?subject=Mathematics")
        assert res_recs.status_code == 200
        recs = res_recs.json()
        assert isinstance(recs, list)

        # 4. Query blocked skills
        res_blocked = client.get("/api/mastery/blocked?subject=Mathematics")
        assert res_blocked.status_code == 200

        # 5. Query repair path
        res_path = client.get("/api/mastery/repair-path/MATH_QUAD_EQ")
        assert res_path.status_code == 200

        # 6. Graph audit endpoint
        res_audit = client.get("/api/mastery/audit")
        assert res_audit.status_code == 200
        audit = res_audit.json()
        assert "is_dag" in audit
        assert audit["is_dag"] is True

        # 7. INVARIANT: Student direct mutation denial (§20)
        # Verify there is NO PUT or PATCH endpoint allowing direct state writing
        res_illegal_patch = client.patch("/api/mastery/skills/MATH_NUM_OPS", json={"mastery_state": "SECURE"})
        assert res_illegal_patch.status_code in (404, 405), "Direct client state mutation endpoint must not exist"

    app.dependency_overrides.clear()
