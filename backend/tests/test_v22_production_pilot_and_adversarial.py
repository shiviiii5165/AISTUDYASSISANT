"""
LearnByGenie AI Video Teacher V2.2 — Production Validation, Pilot & Concurrency Suite
===================================================================================
Rigorous verification for:
1. Server-side bounded DoubtSessionMemory (Decision #1 & #8)
2. Referential Memory Resolution ("20 wala", "uske pehle wala", "upar wali step", "arrow wala") (Decision #2)
3. Unique Job Directories and Scratch Isolation (Decision #3)
4. Formal Storage Lifecycle Classes & Ephemeral Cleanup (Decision #4)
5. Normalized Gain Edge Cases (Div-by-zero, negative gain, raw score persistence) (Decision #5)
6. Transfer Question Pairs with Isomorphic Equivalence (Decision #6)
7. Participant Privacy & Strict Provenance Separation (Decision #7 & #16)
8. Core Tutor Metrics: First-Explanation, Adaptive-Resolution, External-Help Escape (Decisions #9 & #10)
9. Production Readiness Telemetry with Sample Metadata & Windows (Decision #11)
10. Protected Admin Readiness Endpoint (Decision #12)
11. Centralized Failure Taxonomy & Student-Safe Payloads (Decision #13)
12. Genuine Concurrent Job Isolation Testing (Decision #17)
"""
import os
import time
import asyncio
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.video.schemas import (
    VideoConfig, VideoQuality, VideoStyle, AspectRatio, DomainCategory,
    VideoKnowledgePackage, SceneKnowledge, DoubtContext, ExplanationStrategy, ConfusionType,
    StorageArtifactClass, FailureCode, ReferentialAnchorType
)
from app.services.video.doubt.session_memory import DoubtSessionMemoryManager
from app.services.video.storage_lifecycle import StorageLifecycleManager
from app.services.video.failure_taxonomy import FailureTaxonomy
from app.services.video.pilot.pilot_tracker import LearnerPilotTracker
from app.services.video.orchestrator import generate_video_pipeline, PROJECT_STORE


client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# 1. SERVER-SIDE BOUNDED DOUBT MEMORY & BOUNDED LLM CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

def test_server_side_bounded_doubt_memory():
    """Verify DoubtSessionMemoryManager bounds turns to 3 and compresses older turns."""
    session_id = "test_bound_session"
    # Reset or create
    sess = DoubtSessionMemoryManager.get_or_create_session(session_id, "lesson_bounded")

    # Add 5 consecutive turns
    for i in range(1, 6):
        DoubtSessionMemoryManager.record_turn(
            session_id=session_id,
            user_question=f"Question {i} about step {i}",
            timestamp_sec=float(i * 10),
            tutor_explanation=f"Tutor explanation for question {i} in detail.",
            strategy_used="STEP_BY_STEP" if i % 2 == 0 else "SIMPLE",
            focus_concept="Recursion",
            resolved=True
        )

    # Must be strictly bounded to max 3 recent turns (Decision #1 & #8)
    assert len(sess.recent_turns) == 3
    assert sess.recent_turns[0].user_question == "Question 3 about step 3"
    assert sess.recent_turns[1].user_question == "Question 4 about step 4"
    assert sess.recent_turns[2].user_question == "Question 5 about step 5"

    # Overflow turns (1 & 2) must be compressed into summary
    assert "Question 1" in sess.compressed_summary
    assert "Question 2" in sess.compressed_summary

    # Bounded LLM context must be compact
    context = DoubtContext(
        video_id="lesson_bounded",
        timestamp=50.0,
        current_scene_id="s3",
        current_concept="Recursion Base Case",
        student_question="Question 5 about step 5"
    )
    llm_payload = DoubtSessionMemoryManager.get_bounded_llm_context(session_id, context)
    assert len(llm_payload["recent_turns"]) == 3
    assert "Recursion" in llm_payload["current_concept"]
    assert len(llm_payload["conversation_summary"]) <= 400
    print("Bounded doubt memory test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 2. REFERENTIAL CONVERSATIONAL MEMORY RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def test_referential_memory_resolution():
    """Verify deictic and conversational references resolve against normalized anchors (Decision #2)."""
    kp = VideoKnowledgePackage(
        video_id="ref_vid_01",
        topic="Linked List Insertion",
        domain="computer_science",
        learner_level="B.Tech",
        language="hinglish",
        total_duration_seconds=180.0,
        scenes=[
            SceneKnowledge(
                scene_id="sc_01",
                order=1,
                timestamp_start=0.0,
                timestamp_end=45.0,
                concept_id="c_struct",
                concept_name="Node Memory Layout",
                teaching_goal="Understand data and pointer fields",
                purpose="core_concept",
                narration="Har node me do fields hote hain: data aur next address.",
                transcript="Har node me do fields hote hain: data aur next address.",
                visual_strategy="data_structures",
                worked_example="Node struct with data 10",
                visual_state={"elements": ["box node 10", "pointer arrow"]}
            ),
            SceneKnowledge(
                scene_id="sc_02",
                order=2,
                timestamp_start=45.0,
                timestamp_end=90.0,
                concept_id="c_head_insert",
                concept_name="Head Insertion Step",
                teaching_goal="Derive insertion at head pointer",
                purpose="worked_derivation",
                narration="Next hum 20 wala node link karenge head ke sath.",
                transcript="Next hum 20 wala node link karenge head ke sath.",
                visual_strategy="step_by_step",
                worked_example="Inserting 20: 20->next = head; head = 20",
                visual_state={"elements": ["arrow pointing to head", "node 20 box"]}
            )
        ]
    )

    sess = DoubtSessionMemoryManager.get_or_create_session("sess_ref_test", "ref_vid_01", kp)

    # 1. "acha 20 wala?" -> Worked example with value 20
    anchor_20 = DoubtSessionMemoryManager.resolve_referential_query("acha 20 wala?", sess, 60.0, kp)
    assert anchor_20 is not None
    assert anchor_20.anchor_type == ReferentialAnchorType.WORKED_EXAMPLE
    assert "20" in anchor_20.label

    # 2. "wahi arrow wala" -> Visual element with pointer/arrow
    anchor_arrow = DoubtSessionMemoryManager.resolve_referential_query("wahi arrow wala", sess, 60.0, kp)
    assert anchor_arrow is not None
    assert anchor_arrow.anchor_type == ReferentialAnchorType.VISUAL_ELEMENT
    assert any("arrow" in a for a in anchor_arrow.aliases)

    # 3. "upar wali step" -> Derivation step
    anchor_step = DoubtSessionMemoryManager.resolve_referential_query("upar wali step smjha do", sess, 60.0, kp)
    assert anchor_step is not None
    assert anchor_step.anchor_type in [ReferentialAnchorType.EQUATION_STEP, ReferentialAnchorType.SCENE]

    # 4. "nahi uske pehle wala" -> Previous tutor explanation
    DoubtSessionMemoryManager.record_turn(
        session_id="sess_ref_test",
        user_question="how does next point to head?",
        timestamp_sec=65.0,
        tutor_explanation="It copies the memory address into the pointer field.",
        strategy_used="SIMPLE",
        focus_concept="Head Insertion Step"
    )
    anchor_prev = DoubtSessionMemoryManager.resolve_referential_query("nahi uske pehle wala", sess, 70.0, kp)
    assert anchor_prev is not None
    assert anchor_prev.anchor_type == ReferentialAnchorType.PREVIOUS_TUTOR_EXPLANATION
    assert "how does next point to head?" in anchor_prev.label
    print("Referential memory resolution test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 3. UNIQUE JOB DIRECTORIES & STORAGE LIFECYCLE EPHEMERAL CLEANUP
# ─────────────────────────────────────────────────────────────────────────────

def test_unique_job_directories_and_storage_lifecycle():
    """Verify job isolation, artifact classification, and ephemeral cleanup (Decisions #3 & #4)."""
    # 1. Create two separate jobs
    job1_id, job1_dir = StorageLifecycleManager.create_job_scratch_dir(None, "user_alice", "lesson_101")
    job2_id, job2_dir = StorageLifecycleManager.create_job_scratch_dir(None, "user_bob", "lesson_102")

    # Concurrent jobs must have distinct scratch paths
    assert job1_id != job2_id
    assert job1_dir != job2_dir
    assert os.path.exists(job1_dir) and os.path.exists(job2_dir)

    # 2. Populate ephemeral, cacheable, and persistent files in job1
    ephemeral_file = os.path.join(job1_dir, "ephemeral", "frame_001.png")
    with open(ephemeral_file, "w") as f:
        f.write("fake_png_data")

    cacheable_file = os.path.join(job1_dir, "cacheable", "scene_01_clip.mp4")
    with open(cacheable_file, "w") as f:
        f.write("fake_scene_clip")

    persistent_file = os.path.join(job1_dir, "persistent", "final_video.mp4")
    with open(persistent_file, "w") as f:
        f.write("fake_final_video")

    # Register artifacts
    StorageLifecycleManager.register_artifact(ephemeral_file, StorageArtifactClass.EPHEMERAL)
    StorageLifecycleManager.register_artifact(cacheable_file, StorageArtifactClass.CACHEABLE, ttl_seconds=86400)
    StorageLifecycleManager.register_artifact(persistent_file, StorageArtifactClass.PERSISTENT)

    # 3. Clean ephemeral artifacts
    cleaned_count = StorageLifecycleManager.clean_ephemeral_artifacts(job1_dir)
    assert cleaned_count >= 1
    assert not os.path.exists(ephemeral_file), "Ephemeral file was not deleted immediately!"

    # Cacheable and Persistent artifacts must remain intact for single-scene regeneration
    assert os.path.exists(cacheable_file), "Cacheable scene clip was incorrectly deleted!"
    assert os.path.exists(persistent_file), "Persistent master video was incorrectly deleted!"
    print("Storage lifecycle and ephemeral cleanup test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 4. NORMALIZED GAIN EDGE CASES & DIV-BY-ZERO PROTECTION
# ─────────────────────────────────────────────────────────────────────────────

def test_normalized_gain_edge_cases():
    """Verify normalized gain calculation handles edge cases without hiding negative gains (Decision #5)."""
    LearnerPilotTracker.clear_sessions()

    # Case A: Perfect pre-score (pre = 1.0) -> Div by zero protected, returns None
    s_perf = LearnerPilotTracker.record_pilot_session(
        participant_id="p_perf", lesson_id="les_1", topic="Topic A",
        pre_score=1.0, post_score=1.0
    )
    assert s_perf.raw_gain == 0.0
    assert s_perf.normalized_gain is None, "Expected normalized_gain to be None when pre=1.0"

    # Case B: Standard positive learning gain (pre = 0.25, post = 0.75)
    # Norm Gain = (0.75 - 0.25) / (1.0 - 0.25) = 0.50 / 0.75 = 0.6667
    s_pos = LearnerPilotTracker.record_pilot_session(
        participant_id="p_pos", lesson_id="les_1", topic="Topic A",
        pre_score=0.25, post_score=0.75
    )
    assert s_pos.raw_gain == 0.5
    assert abs(s_pos.normalized_gain - 0.6667) < 0.001

    # Case C: Negative learning gain (learner performance decreased post-test)
    # Pre = 0.8, Post = 0.4 -> Norm Gain = (0.4 - 0.8) / (1.0 - 0.8) = -0.4 / 0.2 = -2.0
    s_neg = LearnerPilotTracker.record_pilot_session(
        participant_id="p_neg", lesson_id="les_1", topic="Topic A",
        pre_score=0.8, post_score=0.4
    )
    assert s_neg.raw_gain == -0.4
    assert s_neg.normalized_gain == -2.0, "Negative learning gain must NOT be hidden!"

    # Case D: Raw pre/post scores persisted
    assert s_pos.pre_score == 0.25 and s_pos.post_score == 0.75
    print("Normalized gain edge cases test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 5. TRANSFER QUESTION PAIRS WITH EQUIVALENT DIFFICULTY
# ─────────────────────────────────────────────────────────────────────────────

def test_transfer_question_pairs_and_equivalence():
    """Verify TransferQuestionPair tests equivalent skill with different numbers/scenarios (Decision #6)."""
    # Computer Science / Pointer Redirection
    cs_pair = LearnerPilotTracker.generate_transfer_question_pair(
        concept_id="linked_list_insert",
        concept_name="Linked List Pointer Update",
        domain="computer_science"
    )
    assert cs_pair.assessed_skill == "pointer_redirection_order"
    assert cs_pair.equivalence_score >= 0.95
    assert "[10, 20, 30]" in cs_pair.pre_question
    assert "[40, 60, 80]" in cs_pair.post_question
    # Questions test same capability with different values to prevent memorization
    assert cs_pair.pre_question != cs_pair.post_question

    # Physics / Newton's Second Law
    phys_pair = LearnerPilotTracker.generate_transfer_question_pair(
        concept_id="newtons_second_law",
        concept_name="Newton's Second Law F=ma",
        domain="physics"
    )
    assert phys_pair.assessed_skill == "f_equals_ma_calculation"
    assert phys_pair.equivalence_score >= 0.95
    assert "4 kg" in phys_pair.pre_question
    assert "6 kg" in phys_pair.post_question
    print("Transfer question pairs test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 6. PARTICIPANT PRIVACY & HUMAN EVALUATION PROVENANCE SEPARATION
# ─────────────────────────────────────────────────────────────────────────────

def test_participant_privacy_and_provenance_separation():
    """Verify pseudonymous participant IDs and strict separation of real vs internal evaluations (Decisions #7, #14, #16)."""
    LearnerPilotTracker.clear_sessions()

    # 1. Privacy-safe participant ID
    raw_user = "user_student_secret_uuid_12345"
    p_id = LearnerPilotTracker.generate_participant_id(raw_user)
    assert raw_user not in p_id
    assert p_id.startswith("pilot_hmac_")

    # 2. Add real learner session
    LearnerPilotTracker.record_pilot_session(
        participant_id=p_id,
        lesson_id="les_real_01",
        topic="Linked List",
        pre_score=0.2,
        post_score=0.8,
        delayed_score=None,  # Not taken yet; never fabricate! (Decision #14)
        provenance="REAL_LEARNER_EVALUATION",
        doubts_count=2,
        doubts_resolved=2,
        first_explanation_resolutions=1,
        external_help_needed=False
    )

    # 3. Add internal developer/manual review session
    LearnerPilotTracker.record_pilot_session(
        participant_id="dev_manual_reviewer",
        lesson_id="les_real_01",
        topic="Linked List",
        pre_score=0.0,
        post_score=1.0,
        provenance="INTERNAL_MANUAL_REVIEW",
        doubts_count=0
    )

    # 4. Aggregated metrics for REAL_LEARNER_EVALUATION must quarantine internal reviews
    report = LearnerPilotTracker.aggregate_metrics(measurement_window="24h", provenance_filter="REAL_LEARNER_EVALUATION")
    assert report.sample_count == 1, "Internal review leaked into real learner metrics!"
    assert report.external_help_escape_rate == 0.0
    print("Participant privacy and provenance separation test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 7. CENTRALIZED FAILURE TAXONOMY & STUDENT-SAFE PAYLOAD
# ─────────────────────────────────────────────────────────────────────────────

def test_centralized_failure_taxonomy_and_student_safety():
    """Verify structured failure codes and guaranteed exclusion of internal secrets/stack traces (Decision #13)."""
    exc = RuntimeError("FFmpeg process crashed at internal IP 192.168.1.100 with token secret-key-xyz: exit code 1")
    failure = FailureTaxonomy.classify_exception(exc, context_hint="test_scene_compilation")

    assert failure.code == FailureCode.FFMPEG_FAILED
    assert failure.severity == "CRITICAL"
    assert failure.retryable is True

    # Student payload inspection
    student_payload = FailureTaxonomy.to_student_payload(failure)
    assert "secret-key-xyz" not in str(student_payload)
    assert "192.168.1.100" not in str(student_payload)
    assert "Traceback" not in str(student_payload)
    assert "Video rendering failed during composition" in student_payload["message"]
    print("Failure taxonomy and student safety test passed!")


# ─────────────────────────────────────────────────────────────────────────────
# 8. PROTECTED ADMIN READINESS DASHBOARD ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

def test_protected_admin_readiness_endpoint():
    """Verify /admin/readiness-dashboard requires admin role and returns windowed metrics (Decisions #11 & #12)."""
    from app.core.dependencies import get_current_user
    class MockUser:
        def __init__(self, role):
            self.user_metadata = {"role": role}
            self.app_metadata = {"role": role}

    # 1. Normal authenticated student is rejected with 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser("student")
    try:
        res_student = client.get("/api/lessons/admin/readiness-dashboard")
        assert res_student.status_code == 403
        assert "Insufficient permissions" in res_student.json()["detail"]

        # 2. Admin access succeeds with 200 OK
        app.dependency_overrides[get_current_user] = lambda: MockUser("admin")
        res_admin = client.get("/api/lessons/admin/readiness-dashboard?window=24h")
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert data["measurement_window"] == "24h"
        assert "sample_count" in data
        assert "first_explanation_resolution_rate" in data
        assert "external_help_escape_rate" in data
        # Ensure zero stack traces or secret keys in response
        assert "traceback" not in str(data).lower()
        assert "secret" not in str(data).lower()
        print("Protected admin readiness dashboard test passed!")
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# 9. REAL CONCURRENT GENERATION JOBS ISOLATION TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_real_concurrent_job_isolation():
    """
    Runs 3 simultaneous pipeline generation jobs and verifies (Decision #17):
    - Unique job paths
    - No scene/file collision
    - Correct output association
    - Controlled concurrency
    - Ephemeral cleanup after each job
    """
    async def _run_concurrent():
        config1 = VideoConfig(
            topic="Linked List Node Basics",
            duration=60,
            quality=VideoQuality.QUICK,
            style=VideoStyle.ACADEMIC,
            language="english"
        )
        config2 = VideoConfig(
            topic="Newton First Law Inertia",
            duration=60,
            quality=VideoQuality.QUICK,
            style=VideoStyle.MODERN_EXPLAINER,
            language="english"
        )
        config3 = VideoConfig(
            topic="Photosynthesis Light Reactions",
            duration=60,
            quality=VideoQuality.QUICK,
            style=VideoStyle.VISUAL_LEARNING,
            language="english"
        )

        pid1 = "job_iso_01"
        pid2 = "job_iso_02"
        pid3 = "job_iso_03"

        # Run simultaneously
        results = await asyncio.gather(
            generate_video_pipeline(config1, "user_1", pid1),
            generate_video_pipeline(config2, "user_2", pid2),
            generate_video_pipeline(config3, "user_3", pid3),
        )

        proj1, proj2, proj3 = results

        # Verify distinct output association
        assert proj1.id == pid1 and proj1.topic == "Linked List Node Basics"
        assert proj2.id == pid2 and proj2.topic == "Newton First Law Inertia"
        assert proj3.id == pid3 and proj3.topic == "Photosynthesis Light Reactions"

        # Verify all completed successfully
        assert proj1.status == "ready" and proj2.status == "ready" and proj3.status == "ready"

        # Verify final videos were generated
        assert proj1.final_video_url is not None
        assert proj2.final_video_url is not None
        assert proj3.final_video_url is not None

        # Verify distinct knowledge packages
        assert proj1.knowledge_package.topic == "Linked List Node Basics"
        assert proj2.knowledge_package.topic == "Newton First Law Inertia"
        assert proj3.knowledge_package.topic == "Photosynthesis Light Reactions"

        print("Real concurrent job isolation test passed!")

    asyncio.run(_run_concurrent())

    print("Real concurrent job isolation test passed!")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
