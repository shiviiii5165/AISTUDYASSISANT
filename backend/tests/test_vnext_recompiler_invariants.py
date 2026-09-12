import pytest
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageArchetype,
    LearningEvidenceRecord, PlanRecompileDiff
)
from app.services.lesson_planner.vnext.adaptive import AdaptiveLessonEngine


def _build_test_roadmap() -> LearningRoadmap:
    s0 = RoadmapStage(
        id="s0_completed",
        concept_id="c0",
        title="Hook Stage",
        description="Introduction",
        sequence=0,
        duration_minutes=10,
        status=StageStatus.MASTERED,  # Completed stage
        archetype=StageArchetype.HOOK
    )
    s1 = RoadmapStage(
        id="s1_locked",
        concept_id="c1",
        title="Core Concept Lecture",
        description="Must be taught",
        sequence=1,
        duration_minutes=25,
        status=StageStatus.AVAILABLE,
        archetype=StageArchetype.EXPLANATION,
        is_locked=True  # Teacher locked!
    )
    s2 = RoadmapStage(
        id="s2_optional",
        concept_id="c2",
        title="Optional Extension",
        description="Summary & Extension",
        sequence=2,
        duration_minutes=15,
        status=StageStatus.LOCKED,
        archetype=StageArchetype.SUMMARY,
        is_optional=True
    )
    return LearningRoadmap(
        id="plan_invariants_test",
        topic="Dynamic Programming",
        stages=[s0, s1, s2],
        adaptive_reserve_minutes=5,
        target_duration_minutes=50,
        version=1,
        current_version=1
    )


def test_completed_and_locked_stages_remain_immutable():
    """Completed stages and teacher-locked stages cannot be modified or compressed during adaptation."""
    roadmap = _build_test_roadmap()
    initial_s0_dur = roadmap.stages[0].duration_minutes
    initial_s1_dur = roadmap.stages[1].duration_minutes

    evidence = [
        LearningEvidenceRecord(
            student_id=f"student_{i}",
            concept_id="c1",
            correctness=False,
            confidence=0.85,
            misconception_candidate="Greedy vs DP confusion"
        )
        for i in range(8)  # 8 out of 10 students fail with same misconception
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(
        roadmap=roadmap,
        evidence_list=evidence,
        active_class_size=10
    )

    # Invariant: Teacher-locked stage (s1) must NOT be compressed
    for mod in diff.stages_compressed:
        assert mod["stage_id"] != "s1_locked"
        assert mod["stage_id"] != "s0_completed"

    assert roadmap.stages[0].duration_minutes == initial_s0_dur
    assert roadmap.stages[1].duration_minutes == initial_s1_dur


def test_strengthened_class_wide_trigger_requires_minimum_sample():
    """
    A small sample such as 1 affected learner out of 4 responses
    must NOT cause a class-wide intervention simply because 1/4 = 25% > 20%!
    """
    roadmap = _build_test_roadmap()
    
    # Only 4 responses total in a class of 20 students (1 failure = 25%)
    evidence_small = [
        LearningEvidenceRecord(
            student_id="student_1",
            concept_id="c1",
            correctness=False,
            confidence=0.80,
            misconception_candidate="Sign Error"
        ),
        LearningEvidenceRecord(student_id="student_2", concept_id="c1", correctness=True, confidence=0.90),
        LearningEvidenceRecord(student_id="student_3", concept_id="c1", correctness=True, confidence=0.85),
        LearningEvidenceRecord(student_id="student_4", concept_id="c1", correctness=True, confidence=0.80)
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(
        roadmap=roadmap,
        evidence_list=evidence_small,
        active_class_size=20,
        minimum_absolute_sample=5,  # Requires at least 5 responses
        minimum_response_coverage=0.50
    )

    # Must NOT trigger class-wide schedule disruption
    assert len(diff.stages_added) == 0
    assert "Insufficient active class coverage" in diff.reason


def test_optional_stages_compress_before_mandatory():
    """When remediation is added, optional stages compress first to preserve total lesson time."""
    roadmap = _build_test_roadmap()
    evidence_large = [
        LearningEvidenceRecord(
            student_id=f"student_{i}",
            concept_id="c1",
            correctness=False,
            confidence=0.85,
            misconception_candidate="Greedy vs DP confusion"
        )
        for i in range(8)
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(
        roadmap=roadmap,
        evidence_list=evidence_large,
        active_class_size=10
    )

    assert len(diff.stages_added) > 0
    # Optional stage s2 should be compressed first
    compressed_ids = [s["stage_id"] for s in diff.stages_compressed]
    assert "s2_optional" in compressed_ids
