import pytest
import asyncio
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageArchetype, PlanRecompileDiff
)
from app.services.lesson_planner.vnext.adaptive import (
    AdaptiveLessonEngine, VersionConflictException
)


def _build_test_roadmap() -> LearningRoadmap:
    stage1 = RoadmapStage(
        id="s1",
        concept_id="c1",
        title="Intro Stage",
        description="Intro",
        sequence=0,
        duration_minutes=15,
        status=StageStatus.AVAILABLE,
        archetype=StageArchetype.CONCEPT_INTRO
    )
    return LearningRoadmap(
        id="roadmap_concurrency_test",
        topic="Concurrency & CAS",
        stages=[stage1],
        version=1,
        current_version=1
    )


def test_atomic_cas_success():
    """Valid expected_plan_version successfully increments version and logs snapshot."""
    roadmap = _build_test_roadmap()
    diff = PlanRecompileDiff(
        reason="Test adaptation",
        stages_added=[{
            "stage_id": "s_new",
            "title": "Remedial Stage",
            "duration_minutes": 5,
            "archetype": "remediation",
            "reason": "Test"
        }]
    )

    updated, new_ver = AdaptiveLessonEngine.apply_adaptation_atomic(
        roadmap=roadmap,
        diff=diff,
        expected_plan_version=1
    )
    assert new_ver == 2
    assert updated.version == 2
    assert updated.current_version == 2
    assert len(updated.stages) == 2


def test_competing_recompiles_detects_version_conflict():
    """
    Simulates two concurrent adaptation requests computed against the same expected version (v1).
    The first must succeed (moving plan to v2); the second must raise VersionConflictException.
    """
    roadmap = _build_test_roadmap()
    diff1 = PlanRecompileDiff(
        reason="Adaptation 1",
        stages_added=[{"stage_id": "s_a", "title": "A", "duration_minutes": 5, "archetype": "remediation", "reason": "A"}]
    )
    diff2 = PlanRecompileDiff(
        reason="Adaptation 2",
        stages_added=[{"stage_id": "s_b", "title": "B", "duration_minutes": 5, "archetype": "remediation", "reason": "B"}]
    )

    # First request arrives and succeeds
    updated, new_ver = AdaptiveLessonEngine.apply_adaptation_atomic(
        roadmap=roadmap,
        diff=diff1,
        expected_plan_version=1
    )
    assert new_ver == 2

    # Second competing request arrives with stale expected_plan_version=1
    with pytest.raises(VersionConflictException) as exc_info:
        AdaptiveLessonEngine.apply_adaptation_atomic(
            roadmap=roadmap,
            diff=diff2,
            expected_plan_version=1
        )
    assert "VERSION_CONFLICT" in str(exc_info.value)


def test_failure_atomicity_rolls_back_partial_state():
    """
    Explicit failure-atomicity test:
    If snapshot or audit write fails after CAS, the entire transaction rolls back
    and leaves ZERO partial state behind.
    """
    roadmap = _build_test_roadmap()
    initial_stage_count = len(roadmap.stages)
    diff = PlanRecompileDiff(
        reason="Failure test",
        stages_added=[{"stage_id": "s_fail", "title": "Fail", "duration_minutes": 5, "archetype": "remediation", "reason": "F"}]
    )

    # 1. Snapshot write failure simulation
    with pytest.raises(RuntimeError) as exc_info:
        AdaptiveLessonEngine.apply_adaptation_atomic(
            roadmap=roadmap,
            diff=diff,
            expected_plan_version=1,
            simulate_failure_stage="snapshot_write_failure"
        )
    assert "Snapshot write failure" in str(exc_info.value)
    # Plan version and stage count MUST remain unchanged
    assert roadmap.version == 1
    assert roadmap.current_version == 1
    assert len(roadmap.stages) == initial_stage_count

    # 2. Adaptation audit write failure simulation
    with pytest.raises(RuntimeError) as exc_info2:
        AdaptiveLessonEngine.apply_adaptation_atomic(
            roadmap=roadmap,
            diff=diff,
            expected_plan_version=1,
            simulate_failure_stage="adaptation_audit_write_failure"
        )
    assert "Adaptation audit log write failure" in str(exc_info2.value)
    assert roadmap.version == 1
    assert len(roadmap.stages) == initial_stage_count
