import pytest
from app.services.lesson_planner.schemas import (
    CanonicalDomain, TeachingIntent, StageArchetype, LearningRoadmap, RoadmapStage,
    StageStatus, TeacherLockItem
)
from app.services.lesson_planner.vnext.pedagogy import (
    PedagogyPolicyEngine, ConceptType
)
from app.services.lesson_planner.vnext.time_budget import (
    DynamicTimeBudgetEngine
)


def test_concept_type_detection():
    # Coding
    assert PedagogyPolicyEngine.detect_concept_type(
        "Binary Tree Traversal", CanonicalDomain.COMPUTER_SCIENCE, TeachingIntent.IMPLEMENT
    ) == ConceptType.CODING

    # Math
    assert PedagogyPolicyEngine.detect_concept_type(
        "Linear Algebra", CanonicalDomain.MATHEMATICS, TeachingIntent.TEACH
    ) == ConceptType.MATHEMATICS

    # Research
    assert PedagogyPolicyEngine.detect_concept_type(
        "Vision Transformers", CanonicalDomain.COMPUTER_SCIENCE, TeachingIntent.RESEARCH
    ) == ConceptType.RESEARCH

    # Conceptual
    assert PedagogyPolicyEngine.detect_concept_type(
        "Newton's Laws", CanonicalDomain.PHYSICS, TeachingIntent.TEACH
    ) == ConceptType.CONCEPTUAL


def test_pedagogy_templates_structure():
    templates = PedagogyPolicyEngine.get_pedagogy_templates(ConceptType.CODING)
    archetypes = [t.archetype for t in templates]
    assert StageArchetype.HOOK in archetypes
    assert StageArchetype.MENTAL_MODEL in archetypes
    assert StageArchetype.DEMONSTRATION in archetypes
    assert StageArchetype.GUIDED_PRACTICE in archetypes
    assert StageArchetype.DIAGNOSTIC_CHECK in archetypes

    # Ensure teacher and student active actions exist
    for t in templates:
        assert len(t.suggested_teacher_action) > 10
        assert len(t.suggested_student_action) > 10


def test_initial_time_budget_with_reserve():
    templates = PedagogyPolicyEngine.get_pedagogy_templates(ConceptType.CONCEPTUAL)
    durations, reserve = DynamicTimeBudgetEngine.calculate_initial_budget(
        total_duration_minutes=60,
        templates=templates,
        reserve_pct=0.10
    )

    # 10% of 60 = 6 minutes reserve
    assert reserve == 6
    assert sum(durations) + reserve == 60
    assert all(d >= 5 for d in durations), "Every stage must be at least 5 minutes"


def test_time_reallocation_rules():
    stages = [
        RoadmapStage(
            id="s1",
            concept_id="c1",
            title="Hook",
            description="Motivation",
            duration_minutes=10,
            archetype=StageArchetype.HOOK
        ),
        RoadmapStage(
            id="s2",
            concept_id="c2",
            title="Core Concept",
            description="Explanation",
            duration_minutes=25,
            archetype=StageArchetype.EXPLANATION,
            is_locked=True  # Teacher locked!
        ),
        RoadmapStage(
            id="s3",
            concept_id="c3",
            title="Diagnostic",
            description="Check",
            duration_minutes=15,
            archetype=StageArchetype.DIAGNOSTIC_CHECK  # Protected!
        )
    ]
    roadmap = LearningRoadmap(
        id="r1",
        topic="Test Topic",
        target_duration_minutes=60,
        adaptive_reserve_minutes=5,
        stages=stages
    )

    # Need 8 minutes for a remediation intervention
    diff = DynamicTimeBudgetEngine.reallocate_time_for_adaptation(
        roadmap=roadmap,
        required_remediation_minutes=8,
        reason="Traversal misconception"
    )

    # 5 minutes should come from the adaptive reserve (leaving 0)
    assert roadmap.adaptive_reserve_minutes == 0
    # Remaining 3 minutes must be compressed from s1 (Hook), NOT from s2 (Locked) or s3 (Diagnostic)
    assert stages[0].duration_minutes == 7  # 10 - 3 = 7
    assert stages[1].duration_minutes == 25  # Unchanged because is_locked=True!
    assert stages[2].duration_minutes == 15  # Unchanged because DIAGNOSTIC_CHECK is protected!
    assert len(diff.stages_compressed) == 1
    assert diff.stages_compressed[0]["stage_id"] == "s1"
