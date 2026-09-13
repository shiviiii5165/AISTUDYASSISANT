"""
TeachGenie Canary Infrastructure — Comprehensive Safeguards Test Suite
======================================================================
Tests:
1. Pseudonymous ID generation & isolated identity registry.
2. Zero PII in analytics/exports (scan for emails, phone numbers, IP addresses).
3. Structured authorization records (grant, scopes, revocation).
4. Cohort-level outcome ranking eligibility (canonical_concept_id + learner_level + resource_role).
5. LESSON_OUTCOME_RANKING_ENABLED feature flag guard (default False).
6. Idempotent delayed retention scheduler (24h, 72h, 168h deduplication).
7. Anonymized CSV/JSON exports with privacy verification.
8. Live inference vs deterministic fallback separation.
9. Dynamic gate-based verdict engine (computed verdict CANARY READY with 0 teachers/students).
"""

import pytest
from datetime import datetime, timezone
from app.core.config import settings
from app.services.lesson_planner.vnext.canary import (
    IsolatedIdentityRegistry,
    ManagedIdentityStore,
    generate_pseudonym,
    ServiceTokenManager,
    VaultRole,
    VaultPermission,
    StructuredAuthorizationRecord,
    AuthorizationRegistry,
    AuthorizationScope,
    ActorCategory,
    AuthorizationStatus,
    DataLifecycleManager,
    DataMinimizer,
    DataRetentionPolicy,
    BackupLifecycleManager,
    AuthorizationRevokedError,
    TeacherCanaryWorkflowService,
    DelayedRetentionCheck,
    IdempotentRetentionScheduler,
    RetentionCheckStatus,
    CanaryDatasetExporter,
    InferenceBenchmarkService,
    CanaryVerdictEngine,
    CanaryExecutionGates,
    CanaryKillSwitchRegistry,
    KillSwitchName,
    CanaryRollbackController,
    CanaryReleaseGate,
    GateDecision
)
from app.services.lesson_planner.vnext.resources.outcome_engine import ResourceOutcomeEngine
from app.services.lesson_planner.vnext.resources.contracts import ResourceFeedbackType
from app.services.lesson_planner.schemas import UniversalResourceCard, ResourceScoreBreakdown


# =====================================================================
# 1. PSEUDONYMOUS IDENTITY & ZERO PII TESTS
# =====================================================================

def test_pseudonym_generation_and_validation():
    """Verify pseudonyms use valid prefix and one-way HMAC digest."""
    p_teacher = generate_pseudonym("teacher_john_doe@school.edu", "teacher")
    p_student = generate_pseudonym("student_alice@uni.ac.in", "student")

    assert p_teacher.startswith("tc_psd_")
    assert p_student.startswith("st_psd_")
    assert IsolatedIdentityRegistry.is_valid_pseudonym(p_teacher)
    assert IsolatedIdentityRegistry.is_valid_pseudonym(p_student)
    assert not IsolatedIdentityRegistry.is_valid_pseudonym("john_doe_raw_id")


def test_isolated_identity_vault_prevents_pii_leak():
    """Verify raw user identifiers are strictly isolated inside vault."""
    IsolatedIdentityRegistry.clear_vault_for_testing()
    raw_user = "prof_smith@stanford.edu"
    pseudonym = IsolatedIdentityRegistry.get_or_create_pseudonym(raw_user, "teacher")

    assert pseudonym.startswith("tc_psd_")
    # Same raw ID gets identical deterministic pseudonym
    assert IsolatedIdentityRegistry.get_or_create_pseudonym(raw_user, "teacher") == pseudonym

    # PII scanner detects leaks
    leaky_dataset = {
        "teacher_id": pseudonym,
        "contact_email": "leaked@university.edu",
        "ip_address": "192.168.1.10"
    }
    violations = IsolatedIdentityRegistry.scan_for_pii(leaky_dataset)
    assert len(violations) >= 2
    assert any("email" in v for v in violations)
    assert any("IP" in v for v in violations)

    clean_dataset = {
        "teacher_pseudonym_id": pseudonym,
        "canonical_concept_id": "c_arrays",
        "time_spent": 120
    }
    assert len(IsolatedIdentityRegistry.scan_for_pii(clean_dataset)) == 0


# =====================================================================
# 2. STRUCTURED AUTHORIZATION RECORD TESTS
# =====================================================================

def test_structured_authorization_lifecycle():
    """Verify structured authorization records grant, query, and revoke correctly."""
    AuthorizationRegistry.clear_all()
    st_id = generate_pseudonym("student_123", "student")

    # Grant
    rec = AuthorizationRegistry.grant_authorization(
        pseudonym_id=st_id,
        entity_role="student",
        actor_category=ActorCategory.STUDENT,
        scopes=[AuthorizationScope.CANARY_TELEMETRY, AuthorizationScope.ADAPTIVE_LEARNING]
    )
    assert rec.status == AuthorizationStatus.ACTIVE
    assert AuthorizationRegistry.is_authorized(st_id, AuthorizationScope.CANARY_TELEMETRY)
    assert AuthorizationRegistry.is_authorized(st_id, AuthorizationScope.ADAPTIVE_LEARNING)
    assert not AuthorizationRegistry.is_authorized(st_id, AuthorizationScope.ANONYMIZED_RESEARCH)

    # Revoke
    revoked = AuthorizationRegistry.revoke_authorization(st_id, reason="Student opted out")
    assert revoked
    assert not AuthorizationRegistry.is_authorized(st_id, AuthorizationScope.CANARY_TELEMETRY)


# =====================================================================
# 3. IDEMPOTENT DELAYED RETENTION SCHEDULING TESTS
# =====================================================================

def test_idempotent_retention_scheduling():
    """Verify retention check scheduler deduplicates repeated requests."""
    IdempotentRetentionScheduler.clear_all()
    learner = generate_pseudonym("learner_42", "student")

    # Schedule 24h probe
    check1, created1 = IdempotentRetentionScheduler.schedule_retention_check(
        learner_pseudonym_id=learner,
        canonical_concept_id="c_pointer_arithmetic",
        misconception_id="m_index_offset",
        lifecycle_episode_id="ep_001",
        window="24h"
    )
    assert created1 is True
    assert check1.status == RetentionCheckStatus.PENDING

    # Attempt to schedule exact same probe -> Must deduplicate!
    check2, created2 = IdempotentRetentionScheduler.schedule_retention_check(
        learner_pseudonym_id=learner,
        canonical_concept_id="c_pointer_arithmetic",
        misconception_id="m_index_offset",
        lifecycle_episode_id="ep_001",
        window="24h"
    )
    assert created2 is False
    assert check2.check_id == check1.check_id
    assert IdempotentRetentionScheduler.get_stats()["deduplications_blocked"] == 1

    # Schedule different window (72h) -> Permitted
    check3, created3 = IdempotentRetentionScheduler.schedule_retention_check(
        learner_pseudonym_id=learner,
        canonical_concept_id="c_pointer_arithmetic",
        misconception_id="m_index_offset",
        lifecycle_episode_id="ep_001",
        window="72h"
    )
    assert created3 is True
    assert check3.check_id != check1.check_id


# =====================================================================
# 4. COHORT-LEVEL OUTCOME RANKING & FEATURE FLAG TESTS
# =====================================================================

def test_outcome_ranking_disabled_by_default():
    """Verify outcome-aware ranking does NOT alter scores when feature flag is False."""
    ResourceOutcomeEngine.clear_all_signals()
    assert getattr(settings, "LESSON_OUTCOME_RANKING_ENABLED", False) is False

    card = UniversalResourceCard(
        id="card_1",
        title="Array Indexing Guide",
        type="docs",
        why_recommended="Essential syntax guide",
        what_it_covers="Array declaration and indexing",
        learner_level="B.Tech",
        url="https://geeksforgeeks.org/c-arrays",
        quality_score=85,
        score_breakdown=ResourceScoreBreakdown()
    )

    # Record 15 positive outcome signals
    for _ in range(15):
        ResourceOutcomeEngine.record_outcome_signal(
            resource_id="card_1",
            concept_id="c_arrays",
            learner_level="B.Tech",
            resource_role="core_explanation",
            pre_state="novice",
            post_state="mastered"
        )

    # Apply ranking with flag disabled -> Quality score MUST remain exactly 85
    result = ResourceOutcomeEngine.apply_outcome_aware_ranking(
        cards=[card],
        concept_id="c_arrays",
        learner_level="B.Tech",
        resource_role="core_explanation"
    )
    assert result[0].quality_score == 85


def test_outcome_ranking_cohort_eligibility():
    """Verify outcome stats require cohort-level matching (concept + level + role)."""
    ResourceOutcomeEngine.clear_all_signals()

    # Record signals under B.Tech cohort (N=22 >= MIN_COHORT_SAMPLE_SIZE=20)
    for _ in range(22):
        ResourceOutcomeEngine.record_outcome_signal(
            resource_id="card_algo",
            concept_id="c_dijkstra",
            learner_level="B.Tech",
            resource_role="core_explanation",
            pre_state="novice",
            post_state="mastered"
        )

    # Inquire for B.Tech cohort -> Cohort matched and statistically significant
    stats_btech = ResourceOutcomeEngine.get_outcome_stats(
        resource_id="card_algo",
        concept_id="c_dijkstra",
        learner_level="B.Tech",
        resource_role="core_explanation"
    )
    assert stats_btech["cohort_sample_size"] == 22
    assert stats_btech["is_statistically_significant"] is True

    # Inquire for School Class 8 cohort -> Not statistically significant
    stats_school = ResourceOutcomeEngine.get_outcome_stats(
        resource_id="card_algo",
        concept_id="c_dijkstra",
        learner_level="Class 8",
        resource_role="core_explanation"
    )
    assert stats_school["cohort_sample_size"] == 0
    assert stats_school["is_statistically_significant"] is False


# =====================================================================
# 5. ANONYMIZED EXPORT PRIVACY VALIDATION
# =====================================================================

def test_anonymized_export_validation():
    """Verify export dataset formats and passes automated privacy screening."""
    records = [
        CanaryDatasetExporter.format_export_record(
            session_id="sess_001",
            teacher_pseudonym_id=generate_pseudonym("t1", "teacher"),
            student_pseudonym_id=generate_pseudonym("s1", "student"),
            canonical_concept_id="c_arrays",
            stage_title="Array Fundamentals",
            pre_state="novice",
            post_state="mastered",
            misconception_tag="off_by_one",
            time_spent_seconds=145,
            feedback_type="HELPFUL",
            created_at="2026-09-13T12:00:00Z"
        )
    ]

    csv_output = CanaryDatasetExporter.export_to_csv(records)
    assert "sess_001" in csv_output
    assert "tc_psd_" in csv_output
    assert "st_psd_" in csv_output

    validation = CanaryDatasetExporter.validate_export_privacy(records)
    assert validation["is_privacy_compliant"] is True
    assert validation["pii_leaks_detected"] == 0


# =====================================================================
# 6. INFERENCE BENCHMARK & PROVENANCE SEPARATION
# =====================================================================

def test_deterministic_vs_live_inference_provenance():
    """Verify deterministic fallback has separate provenance and reports properly."""
    import asyncio

    det_res = asyncio.run(InferenceBenchmarkService.run_deterministic_benchmark("Binary Search Algorithm"))
    assert det_res["provenance"] == "DETERMINISTIC_FALLBACK"
    assert det_res["cost_usd"] == 0.0
    assert det_res["latency_ms"] > 0

    cred_status = InferenceBenchmarkService.check_credential_status()
    live_res = asyncio.run(InferenceBenchmarkService.run_live_inference_benchmark("Binary Search Algorithm"))
    assert live_res["provenance"] in ("LIVE_INFERENCE", "PARTIAL_LIVE_PROBE", "COMPLETE_LIVE_MEASURED")
    assert live_res["truth_label"] in ("PARTIAL_LIVE_PROBE", "COMPLETE_LIVE_MEASURED", "LIVE_INFERENCE_NOT_MEASURED")
    if not cred_status["any_live_credentials"]:
        assert live_res["status"] == "LIVE_INFERENCE_NOT_MEASURED"
        assert live_res["truth_label"] == "LIVE_INFERENCE_NOT_MEASURED"
        assert live_res["tokens_used"] is None
        assert live_res["cost_usd"] is None
    else:
        assert live_res["truth_label"] in ("COMPLETE_LIVE_MEASURED", "PARTIAL_LIVE_PROBE")


# =====================================================================
# 7. DYNAMIC GATE-BASED VERDICT ENGINE
# =====================================================================

def test_verdict_engine_zero_human_participants():
    """With zero real teachers and all gates passing, verdict MUST be TEACHER_CANARY_READY."""
    gates = CanaryExecutionGates(
        infrastructure_ready=True,
        tests_passed=True,
        test_pass_rate=1.0,
        regression_count=0,
        export_privacy_passed=True,
        outcome_ranking_guard_passed=True,
        idempotency_guard_passed=True,
        real_teachers_count=0,
        real_students_count=0,
        frontend_build_success=True
    )
    evaluation = CanaryVerdictEngine.evaluate_verdict(gates)
    assert evaluation["verdict"] == "TEACHER_CANARY_READY"
    assert evaluation["status"] == "APPROVED_FOR_TEACHER_ENROLLMENT"


def test_verdict_engine_failures_trigger_hold():
    """Verify build or privacy failures trigger HOLD."""
    broken_gates = CanaryExecutionGates(
        infrastructure_ready=True,
        tests_passed=True,
        export_privacy_passed=False,  # Failure!
        frontend_build_success=True
    )
    eval_broken = CanaryVerdictEngine.evaluate_verdict(broken_gates)
    assert eval_broken["verdict"] == "HOLD"
    assert "Gate failures" in eval_broken["reason"]


# =====================================================================
# 8. MANAGED ENCRYPTED STORE, KEY ROTATION & SERVICE AUTHORIZATION
# =====================================================================

def test_managed_identity_store_authorization_and_key_rotation():
    """Verify cryptographic tokens, permission enforcement, key rotation, and audit integrity."""
    ManagedIdentityStore.clear_vault_for_testing()

    # 1. Issue enrollment token and store identity
    enroll_token = ServiceTokenManager.issue_token("onboarding_microservice", VaultRole.ENROLLMENT_SERVICE, ttl_seconds=300)
    p_teacher = ManagedIdentityStore.get_or_create_pseudonym(
        raw_user_id="prof_turing@cambridge.ac.uk",
        role="teacher",
        caller_context=enroll_token
    )
    assert p_teacher.startswith("tc_psd_")

    # 2. Verify analytics role lacks enrollment and lookup permissions
    analytics_token = ServiceTokenManager.issue_token("metrics_worker", VaultRole.ANALYTICS_SERVICE, ttl_seconds=300)
    with pytest.raises(PermissionError) as exc_info:
        ManagedIdentityStore.get_or_create_pseudonym("prof_turing@cambridge.ac.uk", "teacher", caller_context=analytics_token)
    assert "lacks required permission" in str(exc_info.value) or "Invalid" in str(exc_info.value)

    # 3. Key rotation: Rotate master key from v1 to v2
    admin_token = ServiceTokenManager.issue_token("secops_admin", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    rot_res = ManagedIdentityStore.rotate_vault_keys(caller_context=admin_token)
    assert rot_res["status"] == "SUCCESS"
    assert rot_res["old_key_version"] == "v1"
    assert rot_res["new_key_version"] == "v2"
    assert rot_res["records_re_encrypted"] >= 1

    # 4. Audit integrity verification
    assert ManagedIdentityStore.verify_audit_integrity() is True


# =====================================================================
# 9. COMPLETE DATA LIFECYCLE TESTS (MINIMIZATION, REVOCATION, PURGE)
# =====================================================================

def test_complete_data_lifecycle_minimization_and_revocation():
    """Verify data minimization, check cancellation, cryptographic erasure, and immediate telemetry halt."""
    ManagedIdentityStore.clear_vault_for_testing()
    AuthorizationRegistry.clear_all()
    IdempotentRetentionScheduler.clear_all()
    BackupLifecycleManager.clear_all()

    # 1. Enrollment & structured consent
    p_teacher = ManagedIdentityStore.get_or_create_pseudonym("prof_lovelace@oxford.edu", "teacher")
    auth_rec = AuthorizationRegistry.grant_authorization(p_teacher, "teacher")
    assert AuthorizationRegistry.is_authorized(p_teacher) is True

    # 2. Schedule retention check
    check, created = IdempotentRetentionScheduler.schedule_retention_check(
        learner_pseudonym_id=p_teacher,
        canonical_concept_id="c_analytical_engine",
        misconception_id="m_punch_cards",
        lifecycle_episode_id="ep_001",
        window="24h"
    )
    assert created is True
    assert check.status == RetentionCheckStatus.PENDING

    # 3. Data minimization: extraneous or PII fields rejected
    raw_payload = {
        "session_id": "sess_101",
        "teacher_pseudonym_id": p_teacher,
        "canonical_concept_id": "c_analytical_engine",
        "subject": "CS",
        "grade_level": "Undergrad",
        "plan_decision": "accept",
        "decision_timestamp": "2026-09-13T12:00:00Z",
        "extra_unminimized_garbage": "drop_me"
    }
    sanitized = DataMinimizer.sanitize("session", raw_payload)
    assert "extra_unminimized_garbage" not in sanitized
    assert sanitized["plan_decision"] == "accept"

    # 4. Execute full lifecycle revocation
    rev_res = DataLifecycleManager.execute_revocation_lifecycle(
        pseudonym_id=p_teacher,
        reason="Teacher opted out"
    )
    assert rev_res["status"] == "REVOCATION_COMPLETED"
    assert rev_res["authorization_record_revoked"] is True
    assert rev_res["pending_retention_checks_cancelled"] == 1
    assert rev_res["vault_mapping_cryptographically_erased"] is True

    # 5. Immediate halt of future telemetry
    with pytest.raises(AuthorizationRevokedError):
        DataLifecycleManager.verify_telemetry_allowed(p_teacher)

    # 6. Backup snapshot expiration
    from datetime import timedelta
    old_time = datetime.now(timezone.utc) - timedelta(days=35)
    BackupLifecycleManager.record_backup("snap_old", "hash_old", created_at=old_time)
    BackupLifecycleManager.record_backup("snap_new", "hash_new")
    purged = BackupLifecycleManager.prune_expired_backups()
    assert purged == 1


# =====================================================================
# 10. REAL TEACHER CANARY WORKFLOW & LIVE DASHBOARD TESTS
# =====================================================================

def test_real_teacher_canary_workflow_and_live_dashboard():
    """Verify end-to-end real teacher canary workflow: enrollment, session, decisions, replacements, dashboard."""
    import asyncio
    TeacherCanaryWorkflowService.clear_all_for_testing()
    ManagedIdentityStore.clear_vault_for_testing()
    AuthorizationRegistry.clear_all()

    # Step 1: Explicit enrollment
    enrolled = TeacherCanaryWorkflowService.enroll_teacher(
        raw_teacher_id="teacher_feynman",
        email="rfeynman@caltech.edu",
        name="Richard Feynman",
        school_category="university"
    )
    t_pseudo = enrolled["teacher_pseudonym_id"]
    assert t_pseudo.startswith("tc_psd_")

    # Step 2: Start session
    session = TeacherCanaryWorkflowService.start_session(
        teacher_pseudonym_id=t_pseudo,
        subject="Physics",
        grade_level="Undergraduate",
        topic="Quantum Electrodynamics"
    )
    assert session.session_id.startswith("sess_tc_")

    # Step 3: Generate lesson (measures decomposed latencies)
    gen_res = asyncio.run(TeacherCanaryWorkflowService.generate_lesson(
        session_id=session.session_id,
        teacher_pseudonym_id=t_pseudo
    ))
    assert gen_res["latency_breakdown"]["pure_deterministic_generation_ms"] > 0

    # Step 4: Record plan decision (accept after edit)
    dec_res = TeacherCanaryWorkflowService.record_plan_decision(
        session_id=session.session_id,
        teacher_pseudonym_id=t_pseudo,
        decision="edit_and_accept",
        edits_made=["Reordered path integrals before perturbation theory"]
    )
    assert dec_res["decision"] == "edit_and_accept"

    # Step 5: Resource feedback (helpful)
    fb_res = TeacherCanaryWorkflowService.record_resource_feedback(
        session_id=session.session_id,
        teacher_pseudonym_id=t_pseudo,
        resource_id="card_q1_paper",
        feedback_type="helpful"
    )
    assert fb_res["status"] == "RECORDED"

    # Step 6: Resource replacement
    rep_res = TeacherCanaryWorkflowService.record_resource_replacement(
        session_id=session.session_id,
        teacher_pseudonym_id=t_pseudo,
        original_resource_id="card_generic_video",
        replacement_resource_id="card_mit_ocw_lecture",
        reason_category="rigor"
    )
    assert rep_res["status"] == "RECORDED"

    # Step 7: Adaptation decision
    adapt_res = TeacherCanaryWorkflowService.record_adaptation_decision(
        session_id=session.session_id,
        teacher_pseudonym_id=t_pseudo,
        adaptation_id="adapt_diagram_misconception",
        decision="accept"
    )
    assert adapt_res["status"] == "RECORDED"

    # Verify Live Dashboard contains exact unsimulated metrics
    dashboard = TeacherCanaryWorkflowService.get_live_dashboard()
    assert dashboard["unique_real_teachers"] == 1
    assert dashboard["real_sessions"] == 1
    assert dashboard["plans_accepted_after_edit"] == 1
    assert dashboard["plans_accepted_without_edit"] == 0
    assert dashboard["rejected_plans"] == 0
    assert dashboard["resource_helpfulness"]["helpful"] == 1
    assert dashboard["resource_replacements_count"] == 1
    assert dashboard["adaptation_decisions"]["accepted"] == 1
    assert "NOT YET MEASURED" in dashboard["student_learning_metrics"]
    assert "DISABLED" in dashboard["outcome_aware_ranking"]

    # Step 8: Revoke participation immediately halts telemetry
    TeacherCanaryWorkflowService.revoke_teacher_participation(t_pseudo, "Canary complete")
    with pytest.raises(AuthorizationRevokedError):
        TeacherCanaryWorkflowService.start_session(t_pseudo, "Physics", "Undergrad", "Optics")


# =====================================================================
# 11. CENTRALIZED CANARY RELEASE GATES (PHASE 3)
# =====================================================================

def test_canary_release_gates_blocking():
    """Verify CanaryReleaseGate evaluates 13 dimensions and blocks enrollment on failure."""
    # 1. Baseline evaluation (with working engine and canary tests)
    report = CanaryReleaseGate.evaluate_gates(vnext_tests_passed=True, canary_tests_passed=True)
    assert report.total_checks == 13
    assert report.block_count == 0
    assert report.overall_status in (GateDecision.PASS, GateDecision.WARN)
    assert report.can_enroll_teachers is True

    # 2. Simulated engine regression failure -> Must BLOCK
    report_engine_fail = CanaryReleaseGate.evaluate_gates(vnext_tests_passed=False, canary_tests_passed=True)
    assert report_engine_fail.overall_status == GateDecision.BLOCK
    assert report_engine_fail.can_enroll_teachers is False
    assert any(c.name == "vnext_engine_test_status" and c.decision == GateDecision.BLOCK for c in report_engine_fail.checks)

    # 3. Simulated canary infrastructure regression failure -> Must BLOCK
    report_canary_fail = CanaryReleaseGate.evaluate_gates(vnext_tests_passed=True, canary_tests_passed=False)
    assert report_canary_fail.overall_status == GateDecision.BLOCK
    assert report_canary_fail.can_enroll_teachers is False
    assert any(c.name == "canary_infrastructure_status" and c.decision == GateDecision.BLOCK for c in report_canary_fail.checks)


# =====================================================================
# 12. OPERATOR EMERGENCY KILL SWITCHES & FAIL-CLOSED SAFETY (PHASE 4)
# =====================================================================

def test_canary_kill_switches_fail_closed_and_audit():
    """Verify operator kill switches enforce authorization, record audit logs, and fail closed."""
    admin_token = ServiceTokenManager.issue_token("secops_lead", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    unauth_token = ServiceTokenManager.issue_token("analyst_user", VaultRole.ANALYTICS_SERVICE, ttl_seconds=300)

    # 1. Unauthorized actor cannot toggle kill switches
    with pytest.raises(PermissionError):
        CanaryKillSwitchRegistry.set_switch(KillSwitchName.DISABLE_TEACHER_CANARY, True, unauth_token)

    # 2. Authorized toggle of all 11 critical kill switches
    switches_to_test = [
        KillSwitchName.DISABLE_TEACHER_CANARY,
        KillSwitchName.DISABLE_NEW_TEACHER_ENROLLMENT,
        KillSwitchName.DISABLE_AI_GENERATION,
        KillSwitchName.DISABLE_PROVIDER_GEMINI,
        KillSwitchName.DISABLE_PROVIDER_GROQ,
        KillSwitchName.DISABLE_PROVIDER_OPENROUTER,
        KillSwitchName.FORCE_SAFE_PROVIDER,
        KillSwitchName.DISABLE_TELEMETRY_INGESTION,
        KillSwitchName.DISABLE_FEEDBACK_INGESTION,
        KillSwitchName.FORCE_READ_ONLY_MODE,
        KillSwitchName.ROLLBACK_CANARY_CONFIG
    ]

    for sw in switches_to_test:
        CanaryKillSwitchRegistry.set_switch(sw, True, admin_token, reason=f"Testing {sw}")
        assert CanaryKillSwitchRegistry.get_switch(sw) is True
        CanaryKillSwitchRegistry.set_switch(sw, False, admin_token, reason=f"Restoring {sw}")
        assert CanaryKillSwitchRegistry.get_switch(sw) is False

    # 3. Verify audit history captures entries
    history = CanaryKillSwitchRegistry.get_audit_history()
    assert len(history) >= 22
    assert history[-1]["operator_id"] == "secops_lead"

    # 4. Fail-closed behavior on corrupted state
    CanaryKillSwitchRegistry.simulate_corruption_for_testing(True)
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.DISABLE_TEACHER_CANARY) is True
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.DISABLE_AI_GENERATION) is True
    CanaryKillSwitchRegistry.simulate_corruption_for_testing(False)

    # 5. Clean reset to baseline
    CanaryKillSwitchRegistry.reset_to_safe_baseline(admin_token)
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.DISABLE_TEACHER_CANARY) is False


# =====================================================================
# 13. AUTOMATED EMERGENCY ROLLBACK ENGINE (PHASE 5)
# =====================================================================

def test_canary_emergency_rollback():
    """Verify automated rollback captures state, isolates providers, freezes enrollment, and preserves audit logs."""
    admin_token = ServiceTokenManager.issue_token("sre_lead", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    CanaryKillSwitchRegistry.reset_to_safe_baseline(admin_token)

    # Snapshot safe state
    snapshot = CanaryRollbackController.snapshot_safe_state(admin_token)
    assert "timestamp" in snapshot
    assert snapshot["operator_id"] == "sre_lead"

    # Execute rollback
    rollback_res = CanaryRollbackController.execute_emergency_rollback(
        operator_token=admin_token,
        reason="Automated test canary anomaly"
    )
    assert rollback_res["status"] == "ROLLBACK_EXECUTED"
    assert rollback_res["audit_trail_preserved"] is True
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.DISABLE_NEW_TEACHER_ENROLLMENT) is True
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.FORCE_SAFE_PROVIDER) is True
    assert CanaryKillSwitchRegistry.get_switch(KillSwitchName.ROLLBACK_CANARY_CONFIG) is True

    # Check audit log chain integrity remains valid after rollback event
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Clean reset
    CanaryKillSwitchRegistry.reset_to_safe_baseline(admin_token)


# =====================================================================
# 14. COMPREHENSIVE PARTICIPANT REVOCATION ISOLATION (PHASE 6)
# =====================================================================

def test_revocation_end_to_end_isolation():
    """Verify revocation completely severs identity linkage, halts future telemetry, and cancels retention checks."""
    TeacherCanaryWorkflowService.clear_all_for_testing()
    ManagedIdentityStore.clear_vault_for_testing()
    AuthorizationRegistry.clear_all()
    IdempotentRetentionScheduler.clear_all()
    admin_token = ServiceTokenManager.issue_token("admin_ops", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    CanaryKillSwitchRegistry.reset_to_safe_baseline(admin_token)

    # Enroll teacher
    enrolled = TeacherCanaryWorkflowService.enroll_teacher(
        raw_teacher_id="prof_curie",
        email="marie.curie@sorbonne.fr",
        name="Marie Curie"
    )
    t_pseudo = enrolled["teacher_pseudonym_id"]

    # Start active session
    session = TeacherCanaryWorkflowService.start_session(t_pseudo, "Physics", "Graduate", "Radioactivity")
    assert session.session_id.startswith("sess_tc_")

    # Schedule delayed retention check
    check, created = IdempotentRetentionScheduler.schedule_retention_check(
        learner_pseudonym_id=t_pseudo,
        canonical_concept_id="c_alpha_decay",
        misconception_id="m_half_life",
        lifecycle_episode_id="ep_curie_01",
        window="24h"
    )
    assert created is True
    assert check.status == RetentionCheckStatus.PENDING

    # Execute full lifecycle revocation
    rev_result = DataLifecycleManager.execute_revocation_lifecycle(
        pseudonym_id=t_pseudo,
        reason="Teacher Marie Curie requested complete canary exit"
    )
    assert rev_result["status"] == "REVOCATION_COMPLETED"
    assert rev_result["pending_retention_checks_cancelled"] == 1
    assert rev_result["identity_linkage_erased"] is True
    assert rev_result["future_telemetry_blocked"] is True

    # 1. Attempt future telemetry -> MUST RAISE AuthorizationRevokedError
    with pytest.raises(AuthorizationRevokedError):
        DataLifecycleManager.verify_telemetry_allowed(t_pseudo)

    # 2. Attempt starting a new session -> MUST RAISE AuthorizationRevokedError
    with pytest.raises(AuthorizationRevokedError):
        TeacherCanaryWorkflowService.start_session(t_pseudo, "Physics", "Graduate", "Polonium")

    # 3. Attempt resource feedback -> MUST RAISE AuthorizationRevokedError
    with pytest.raises(AuthorizationRevokedError):
        TeacherCanaryWorkflowService.record_resource_feedback(
            session_id=session.session_id,
            teacher_pseudonym_id=t_pseudo,
            resource_id="card_rad_guide",
            feedback_type="helpful"
        )

    # 4. Identity store lookup -> MUST RAISE PermissionError (revoked participant)
    with pytest.raises(PermissionError):
        ManagedIdentityStore.get_or_create_pseudonym("prof_curie", "teacher")

    # 5. Raw mapping in vault encrypted map is purged (identity-linkage erased)
    assert t_pseudo not in ManagedIdentityStore._pseudo_to_encrypted_raw

    # 6. Audit integrity remains unbroken
    assert ManagedIdentityStore.verify_audit_integrity() is True


# =====================================================================
# 15. RETENTION PERIODS & DETERMINISTIC TTL VALIDATION (PHASE 7)
# =====================================================================

def test_retention_ttl_reality_checks():
    """Verify formal TTL specifications and deterministic backup snapshot pruning."""
    from datetime import timedelta

    policy = DataLifecycleManager.get_policy()
    assert policy.active_session_telemetry_ttl_days == 90
    assert policy.aggregated_metrics_ttl_days == 365
    assert policy.compliance_audit_logs_ttl_days == 365
    assert policy.backup_snapshots_ttl_days == 30

    # Deterministic time injection for backup pruning
    t0 = datetime.now(timezone.utc)
    BackupLifecycleManager.clear_all()

    BackupLifecycleManager.record_backup("snap_today", "hash_0", created_at=t0)
    BackupLifecycleManager.record_backup("snap_15d_old", "hash_15", created_at=t0 - timedelta(days=15))
    BackupLifecycleManager.record_backup("snap_31d_expired", "hash_31", created_at=t0 - timedelta(days=31))
    BackupLifecycleManager.record_backup("snap_60d_expired", "hash_60", created_at=t0 - timedelta(days=60))

    # Prune relative to t0
    purged = BackupLifecycleManager.prune_expired_backups(current_time=t0)
    assert purged == 2
    assert "snap_today" in BackupLifecycleManager._snapshots
    assert "snap_15d_old" in BackupLifecycleManager._snapshots
    assert "snap_31d_expired" not in BackupLifecycleManager._snapshots
    assert "snap_60d_expired" not in BackupLifecycleManager._snapshots


# =====================================================================
# 16. TAMPER-EVIDENT AUDIT INTEGRITY & SERVICE TOKENS (PHASE 8)
# =====================================================================

def test_audit_chain_tamper_detection_and_service_tokens():
    """Verify tamper-evident SHA-256 chained audit log detects 5 tamper modes, and service tokens enforce least privilege."""
    import base64
    import json

    ManagedIdentityStore.clear_vault_for_testing()

    # Generate legitimate audit entries
    ManagedIdentityStore.get_or_create_pseudonym("user_alpha", "teacher")
    ManagedIdentityStore.get_or_create_pseudonym("user_beta", "teacher")
    ManagedIdentityStore.get_or_create_pseudonym("user_gamma", "teacher")

    # Baseline integrity check
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Tamper 1: Modified record content
    orig_reason = ManagedIdentityStore._audit_log[1]["reason"]
    ManagedIdentityStore._audit_log[1]["reason"] = "Hacked record content"
    assert ManagedIdentityStore.verify_audit_integrity() is False
    ManagedIdentityStore._audit_log[1]["reason"] = orig_reason
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Tamper 2: Removed intermediate record
    removed = ManagedIdentityStore._audit_log.pop(1)
    assert ManagedIdentityStore.verify_audit_integrity() is False
    ManagedIdentityStore._audit_log.insert(1, removed)
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Tamper 3: Inserted unauthorized record
    fake = dict(ManagedIdentityStore._audit_log[0])
    fake["timestamp"] = "2026-09-13T00:00:00Z"
    ManagedIdentityStore._audit_log.insert(2, fake)
    assert ManagedIdentityStore.verify_audit_integrity() is False
    ManagedIdentityStore._audit_log.pop(2)
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Tamper 4: Reordered records
    ManagedIdentityStore._audit_log[0], ManagedIdentityStore._audit_log[1] = (
        ManagedIdentityStore._audit_log[1], ManagedIdentityStore._audit_log[0]
    )
    assert ManagedIdentityStore.verify_audit_integrity() is False
    ManagedIdentityStore._audit_log[0], ManagedIdentityStore._audit_log[1] = (
        ManagedIdentityStore._audit_log[1], ManagedIdentityStore._audit_log[0]
    )
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Tamper 5: Altered previous-hash pointer
    orig_prev = ManagedIdentityStore._audit_log[2]["prev_hash"]
    ManagedIdentityStore._audit_log[2]["prev_hash"] = "e" * 64
    assert ManagedIdentityStore.verify_audit_integrity() is False
    ManagedIdentityStore._audit_log[2]["prev_hash"] = orig_prev
    assert ManagedIdentityStore.verify_audit_integrity() is True

    # Service Token Validation
    # A. Expired token
    expired_tok = ServiceTokenManager.issue_token("test_expired", VaultRole.SECURITY_ADMIN, ttl_seconds=-10)
    with pytest.raises(PermissionError):
        ServiceTokenManager.verify_token(expired_tok)

    # B. Lacking permission
    analytics_tok = ServiceTokenManager.issue_token("test_analyst", VaultRole.ANALYTICS_SERVICE, ttl_seconds=300)
    with pytest.raises(PermissionError):
        ServiceTokenManager.verify_token(analytics_tok, VaultPermission.ENROLL)

    # C. Altered signature
    valid_tok = ServiceTokenManager.issue_token("test_sec", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    decoded = json.loads(base64.urlsafe_b64decode(valid_tok.encode()).decode())
    decoded["signature"] = "0" * 64
    tampered_tok = base64.urlsafe_b64encode(json.dumps(decoded).encode()).decode()
    with pytest.raises(PermissionError):
        ServiceTokenManager.verify_token(tampered_tok)

    # D. Malformed payload
    with pytest.raises(PermissionError):
        ServiceTokenManager.verify_token("invalid_payload_token_string")


# =====================================================================
# 17. ADVERSARIAL DATA MINIMIZATION PAYLOADS (PHASE 9)
# =====================================================================

def test_adversarial_data_minimization_payloads():
    """Verify DataMinimizer rejects emails, phones, names, IPs, nested PII, and strips non-whitelisted attributes."""
    valid_pseudo = "tc_psd_1234567890abcdef"

    # 1. Payload with email
    with pytest.raises(ValueError) as exc1:
        DataMinimizer.sanitize("session", {
            "session_id": "sess_01",
            "teacher_pseudonym_id": valid_pseudo,
            "contact_email": "leaked.teacher@school.edu"
        })
    assert "PII" in str(exc1.value)

    # 2. Payload with phone number
    with pytest.raises(ValueError) as exc2:
        DataMinimizer.sanitize("session", {
            "session_id": "sess_02",
            "teacher_pseudonym_id": valid_pseudo,
            "emergency_phone": "+1-800-555-0199"
        })
    assert "PII" in str(exc2.value)

    # 3. Payload with forbidden personal identity key
    with pytest.raises(ValueError) as exc3:
        DataMinimizer.sanitize("session", {
            "session_id": "sess_03",
            "teacher_pseudonym_id": valid_pseudo,
            "student_name": "Johnny Doe"
        })
    assert "PII" in str(exc3.value)

    # 4. Payload with nested PII in dictionary
    with pytest.raises(ValueError) as exc4:
        DataMinimizer.sanitize("feedback", {
            "session_id": "sess_04",
            "teacher_pseudonym_id": valid_pseudo,
            "resource_id": "card_algo",
            "feedback_type": "helpful",
            "metadata": {"author_email": "author@research.org"}
        })
    assert "PII" in str(exc4.value)

    # 5. Clean payload with extraneous fields -> Extra fields stripped, whitelisted preserved
    clean = DataMinimizer.sanitize("session", {
        "session_id": "sess_05",
        "teacher_pseudonym_id": valid_pseudo,
        "canonical_concept_id": "c_recursion",
        "subject": "Computer Science",
        "grade_level": "Undergraduate",
        "plan_decision": "accept",
        "decision_timestamp": "2026-09-13T12:00:00Z",
        "internal_server_debug_trace": "STACK_TRACE_DO_NOT_STORE",
        "unminimized_session_blob": {"raw": 1234}
    })
    assert "internal_server_debug_trace" not in clean
    assert "unminimized_session_blob" not in clean
    assert clean["session_id"] == "sess_05"
    assert clean["canonical_concept_id"] == "c_recursion"


# =====================================================================
# 18. STUDENT ISOLATION & FEATURE FLAG ENFORCEMENT (PHASE 12)
# =====================================================================

def test_student_isolation_and_feature_flags():
    """Verify real students are strictly blocked from canary, and all student adaptation flags remain False."""
    TeacherCanaryWorkflowService.clear_all_for_testing()
    admin_token = ServiceTokenManager.issue_token("admin_ops", VaultRole.SECURITY_ADMIN, ttl_seconds=300)
    CanaryKillSwitchRegistry.reset_to_safe_baseline(admin_token)

    # 1. Attempting student enrollment must fail
    with pytest.raises(PermissionError) as exc:
        TeacherCanaryWorkflowService.enroll_teacher(
            raw_teacher_id="student_sam",
            email="sam@highschool.edu",
            name="Sam Student",
            role="student"
        )
    assert "Student pilot is strictly disabled" in str(exc.value)

    # 2. Critical feature flags must be strictly False
    assert getattr(settings, "LESSON_AUTO_STUDENT_ADAPTATION_ENABLED", False) is False
    assert getattr(settings, "LESSON_CLASS_ADAPTATION_ENABLED", False) is False
    assert getattr(settings, "LESSON_OUTCOME_RANKING_ENABLED", False) is False

    # 3. Live dashboard reflects zero human participants and safe states before enrollment
    dashboard = TeacherCanaryWorkflowService.get_live_dashboard()
    assert dashboard["unique_real_teachers"] == 0
    assert dashboard["real_sessions"] == 0
    assert "NOT YET MEASURED" in dashboard["student_learning_metrics"]
    assert "DISABLED" in dashboard["outcome_aware_ranking"]


def test_fail_closed_vault_master_key_and_domain_separation():
    """
    Verifies:
    1. Vault fails closed when CANARY_VAULT_MASTER_KEY is missing/empty.
    2. Vault encryption key, capability token signing key, and pseudonymization salt are distinct (KDF domain separation).
    3. Multi-instance security guarantees and backup snapshot availability.
    """
    import os
    from app.services.lesson_planner.vnext.canary.pseudonyms import (
        get_canary_vault_master_key,
        ManagedIdentityStore
    )

    # 1. Fail-closed check
    orig_key = os.environ.get("CANARY_VAULT_MASTER_KEY")
    try:
        if "CANARY_VAULT_MASTER_KEY" in os.environ:
            del os.environ["CANARY_VAULT_MASTER_KEY"]
        with pytest.raises(RuntimeError) as exc_info:
            get_canary_vault_master_key()
        assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info.value)
    finally:
        if orig_key:
            os.environ["CANARY_VAULT_MASTER_KEY"] = orig_key
        else:
            os.environ["CANARY_VAULT_MASTER_KEY"] = "test_key_master_canary_2026"

    # 2. Domain separation check
    sep = ManagedIdentityStore.verify_domain_separation()
    assert sep["keys_mutually_distinct"] is True
    assert sep["status"] == "VERIFIED_DOMAIN_SEPARATION"

    # 3. Multi-instance posture check
    posture = ManagedIdentityStore.verify_multi_instance_safety()
    assert posture["atomic_write_strategy"] == "TMP_SWAP_REPLACE"
    assert "0600" in posture["file_permissions"]



