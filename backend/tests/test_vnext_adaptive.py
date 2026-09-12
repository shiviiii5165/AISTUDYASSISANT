import pytest
from datetime import datetime, timezone
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageArchetype,
    ProductMode, LearningEvidenceRecord
)
from app.services.lesson_planner.vnext.adaptive import AdaptiveLessonEngine


def test_adaptive_high_mastery_proceeds():
    roadmap = LearningRoadmap(
        id="r1",
        topic="Binary Trees",
        stages=[
            RoadmapStage(id="s1", concept_id="c1", title="Intro", description="Intro", duration_minutes=15),
            RoadmapStage(id="s2", concept_id="c2", title="Traversal", description="Traversal", duration_minutes=20)
        ]
    )

    # 10 students, 9 correct (90% pass rate >= 85%)
    evidence = [
        LearningEvidenceRecord(student_id=f"stu_{i}", concept_id="c1", correctness=True)
        for i in range(9)
    ] + [
        LearningEvidenceRecord(student_id="stu_10", concept_id="c1", correctness=False)
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(roadmap, evidence)
    assert "Proceeding" in diff.reason
    assert len(diff.stages_added) == 0
    assert diff.requires_teacher_approval is False


def test_same_misconception_rule_teacher_approval():
    stages = [
        RoadmapStage(
            id="s1",
            concept_id="c1",
            title="Tree Traversal",
            description="Understand DFS traversal",
            duration_minutes=20,
            archetype=StageArchetype.EXPLANATION,
            status=StageStatus.IN_PROGRESS
        ),
        RoadmapStage(
            id="s2",
            concept_id="c2",
            title="Summary & Recap",
            description="Recap",
            duration_minutes=15,
            archetype=StageArchetype.SUMMARY,
            status=StageStatus.AVAILABLE
        )
    ]
    roadmap = LearningRoadmap(
        id="r2",
        topic="Binary Trees",
        target_duration_minutes=60,
        adaptive_reserve_minutes=5,
        mode=ProductMode.TEACHER_CLASSROOM,
        stages=stages
    )

    # 10 students: 6 pass, 4 fail with same misconception: "Confused Inorder vs Preorder" (40% > 20%)
    evidence = [
        LearningEvidenceRecord(student_id=f"stu_{i}", concept_id="c1", correctness=True)
        for i in range(6)
    ] + [
        LearningEvidenceRecord(
            student_id=f"stu_{i}",
            concept_id="c1",
            correctness=False,
            misconception_candidate="Confused Inorder vs Preorder"
        )
        for i in range(6, 10)
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(roadmap, evidence)

    # Must trigger class-wide intervention
    assert len(diff.stages_added) == 1
    added = diff.stages_added[0]
    assert "Targeted Remediation" in added["title"]
    assert "Confused Inorder vs Preorder" in added["title"]
    assert diff.requires_teacher_approval is True, "Classroom mode requires teacher approval"

    # Teacher accepts recommendation
    updated_roadmap = AdaptiveLessonEngine.apply_teacher_decision(roadmap, diff, "ACCEPT")
    assert updated_roadmap.version == 2
    stage_titles = [s.title for s in updated_roadmap.stages]
    assert any("Targeted Remediation: Confused Inorder vs Preorder" in t for t in stage_titles)


def test_student_self_study_auto_adapts():
    stages = [
        RoadmapStage(id="s1", concept_id="c1", title="Intro", description="Intro", duration_minutes=20),
        RoadmapStage(id="s2", concept_id="c2", title="Adv", description="Adv", duration_minutes=20)
    ]
    roadmap = LearningRoadmap(
        id="r3",
        topic="Recursion",
        mode=ProductMode.STUDENT_SELF_STUDY,
        adaptive_reserve_minutes=5,
        stages=stages
    )

    # Single student fails diagnostic
    evidence = [
        LearningEvidenceRecord(
            student_id="solo_student",
            concept_id="c1",
            correctness=False,
            misconception_candidate="Missing Base Condition"
        )
    ]

    diff = AdaptiveLessonEngine.evaluate_and_recompile(roadmap, evidence)
    assert diff.requires_teacher_approval is False, "Self-study auto adapts"
    assert roadmap.version == 2
    assert len(roadmap.stages) == 3
    assert any("Targeted Remediation" in s.title for s in roadmap.stages)
