import pytest
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, CanonicalDomain, TeachingIntent, ProductMode
)
from app.services.lesson_planner.vnext.resources.registry import ResourceNeedDetector


def _build_stage(archetype: StageArchetype) -> RoadmapStage:
    return RoadmapStage(
        id="stage_matrix",
        concept_id="c_matrix",
        title="Persona Evaluation",
        description="Matrix test",
        sequence=0,
        duration_minutes=20,
        archetype=archetype
    )


def test_class_5_photosynthesis_no_academic_paper_overload():
    """Class 5 Primary School: No academic research papers shown."""
    stage = _build_stage(StageArchetype.CONCEPT_INTRO)
    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.BIOLOGY,
        intent=TeachingIntent.INTRODUCE,
        learner_level="Class 5",
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert "research" not in needs
    assert "textbook" in needs


def test_btech_dynamic_programming_shows_coding_resources():
    """B.Tech Dynamic Programming: Coding resources appear."""
    stage = _build_stage(StageArchetype.GUIDED_PRACTICE)
    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        intent=TeachingIntent.PRACTICE,
        learner_level="B.Tech",
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert "coding" in needs


def test_btech_massive_mimo_shows_official_docs_and_standards():
    """B.Tech ECE Massive MIMO: Official docs and engineering standards appear."""
    stage = _build_stage(StageArchetype.EXPLANATION)
    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.ECE,
        intent=TeachingIntent.TEACH,
        learner_level="B.Tech",
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert "docs" in needs


def test_react_software_engineering_official_docs_dominate():
    """React Software Engineering: Official documentation appears."""
    stage = _build_stage(StageArchetype.WORKED_EXAMPLE)
    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.SOFTWARE_ENGINEERING,
        intent=TeachingIntent.IMPLEMENT,
        learner_level="B.Tech",
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert "docs" in needs
    assert "coding" in needs


def test_phd_research_interface_expands_papers():
    """PhD Research: Research paper interface expands."""
    stage = _build_stage(StageArchetype.RESEARCH_REVIEW)
    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        intent=TeachingIntent.RESEARCH,
        learner_level="PhD",
        mode=ProductMode.RESEARCH_ADVANCED
    )
    assert "research" in needs
