import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageReadiness, 
    StageActivity, LearningObjective, BloomLevel, ResourceType, ResourceStatus,
    ClassType
)
from app.services.lesson_planner.engine import (
    TimeBudgetEngine, PrerequisiteEngine, LessonHealthValidator, 
    StateMachineEngine, ResourceRecommenderEngine, RemedialEngine,
    StageOperationsEngine, ChangeImpactEngine
)
from app.services.lesson_planner.course_intelligence import CourseIntelligenceEngine
from app.services.lesson_planner.adapters import (
    PPTAdapter, VideoAdapter, TeachMeAdapter, QuizAdapter, NotesAdapter
)


def get_mock_roadmap():
    stages = [
        RoadmapStage(
            id="s1",
            concept_id="c_func_dep",
            title="Functional Dependency",
            description="Intro to FD and Armstrong Axioms",
            sequence=0,
            duration_minutes=20,
            status=StageStatus.LOCKED,
            objectives=[
                LearningObjective(id="o1", description="Understand FD definition", bloom_level=BloomLevel.UNDERSTAND)
            ],
            activities=[
                StageActivity(type="hook", title="Anomaly", description="intro anomaly", duration_minutes=5),
                StageActivity(type="explanation", title="FD Concept", description="core FD rules", duration_minutes=15)
            ],
            prerequisite_ids=[],
            checkpoint_questions=["What is FD?"],
            expected_misconceptions=["Assuming primary keys cannot be composite"]
        ),
        RoadmapStage(
            id="s2",
            concept_id="c_1nf",
            title="1NF",
            description="First Normal Form and Atomicity",
            sequence=1,
            duration_minutes=20,
            status=StageStatus.LOCKED,
            objectives=[
                LearningObjective(id="o2", description="Identify non-atomic values", bloom_level=BloomLevel.APPLY)
            ],
            activities=[
                StageActivity(type="explanation", title="1NF Rules", description="1nf core", duration_minutes=20)
            ],
            prerequisite_ids=["c_func_dep"],
            checkpoint_questions=["Rule of 1NF?"],
            expected_misconceptions=["Accepting comma-separated lists"]
        ),
        RoadmapStage(
            id="s3",
            concept_id="c_2nf",
            title="2NF",
            description="Second Normal Form and Partial Dependency",
            sequence=2,
            duration_minutes=20,
            status=StageStatus.LOCKED,
            objectives=[
                LearningObjective(id="o3", description="Decompose partial dependencies", bloom_level=BloomLevel.ANALYZE)
            ],
            activities=[
                StageActivity(type="explanation", title="2NF Rules", description="2nf core", duration_minutes=20)
            ],
            prerequisite_ids=["c_1nf"],
            checkpoint_questions=["Rule of 2NF?"],
            expected_misconceptions=["Thinking partial dependency applies to non-composite keys"]
        )
    ]

    for s in stages:
        ResourceRecommenderEngine.evaluate_stage_resources(s, ClassType.INTERACTIVE_LECTURE)

    return LearningRoadmap(
        id="r1",
        course_id="c1",
        topic="DBMS Normalization",
        level="B.Tech",
        language="english",
        class_type=ClassType.INTERACTIVE_LECTURE,
        target_duration_minutes=60,
        stages=stages
    )


def test_prerequisite_engine():
    roadmap = get_mock_roadmap()
    
    # Initial state evaluation
    PrerequisiteEngine.evaluate_readiness(roadmap)
    assert roadmap.stages[0].status == StageStatus.AVAILABLE, "No prereqs should be AVAILABLE"
    assert roadmap.stages[0].readiness == StageReadiness.READY
    assert roadmap.stages[1].status == StageStatus.LOCKED, "Blocked by s1"
    assert roadmap.stages[1].readiness == StageReadiness.PREREQUISITE_REQUIRED
    assert roadmap.stages[2].status == StageStatus.LOCKED, "Blocked by s2"

    # Simulate s1 is taught
    roadmap.stages[0].status = StageStatus.TAUGHT
    PrerequisiteEngine.evaluate_readiness(roadmap)
    assert roadmap.stages[1].status == StageStatus.AVAILABLE, "s2 should unlock"
    assert roadmap.stages[1].readiness == StageReadiness.READY
    assert roadmap.stages[2].status == StageStatus.LOCKED, "s3 still locked"


def test_lesson_timing():
    roadmap = get_mock_roadmap()
    is_valid, warnings = TimeBudgetEngine.validate_and_adjust_timing(roadmap)
    assert is_valid is True
    assert len(warnings) == 0

    # Overbudget
    roadmap.stages[0].duration_minutes = 30
    is_valid, warnings = TimeBudgetEngine.validate_and_adjust_timing(roadmap)
    assert is_valid is False
    assert len(warnings) > 0
    assert "exceeds lesson target" in warnings[0]


def test_lesson_health():
    roadmap = get_mock_roadmap()
    # Mock some gaps
    roadmap.stages[1].checkpoint_questions = []
    
    health = LessonHealthValidator.evaluate_health(roadmap)
    assert health["score"] < 100
    assert any("formative checkpoint" in w for w in health["warnings"])


def test_adapters():
    roadmap = get_mock_roadmap()
    stage = roadmap.stages[0]
    
    # 1. PPT Adapter
    ppt_config = PPTAdapter.create_presentation_config(roadmap, stage)
    assert ppt_config.topic == "Functional Dependency — DBMS Normalization"
    assert ppt_config.slide_count in [8, 12]
    assert "LEARNING OBJECTIVES:" in ppt_config.custom_context
    assert ppt_config.enable_quiz is True

    # 2. Video Adapter
    video_config = VideoAdapter.create_video_config(roadmap, stage)
    assert video_config.topic == "Functional Dependency"
    assert video_config.duration == 180

    # 3. TeachMe Adapter
    teach_context = TeachMeAdapter.create_teach_me_context(roadmap, stage)
    assert "What is FD?" in teach_context
    assert "Functional Dependency" in teach_context

    # 4. Quiz Adapter
    quiz = QuizAdapter.generate_stage_quiz_spec(roadmap, stage)
    assert quiz["quiz_title"] == "Functional Dependency Concept Check"
    assert len(quiz["questions"]) == 1

    # 5. Notes Adapter
    notes = NotesAdapter.generate_stage_notes(roadmap, stage)
    assert "Study Notes: Functional Dependency" in notes["title"]
    assert "# Functional Dependency" in notes["markdown_content"]


def test_course_graph_cycle_detection():
    units = [{"id": "u1", "unit_number": 1, "title": "Unit 1", "topics": ["T1", "T2"]}]
    concepts = [
        {"id": "A", "title": "Concept A", "prerequisite_ids": []},
        {"id": "B", "title": "Concept B", "prerequisite_ids": ["A"]},
        {"id": "C", "title": "Concept C", "prerequisite_ids": ["B"]},
    ]
    # Create an intentional cycle: C -> A
    deps = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"}
    ]

    graph = CourseIntelligenceEngine.build_concept_graph("c1", "DBMS", units, concepts, deps)
    # The cycle breaker should detect and remove the cycle edge
    assert len(graph.edges) < 3


def test_stage_operations():
    roadmap = get_mock_roadmap()
    
    # 1. Reorder
    StageOperationsEngine.reorder_stages(roadmap, ["s3", "s2", "s1"])
    assert roadmap.stages[0].id == "s3"
    assert roadmap.stages[1].id == "s2"
    assert roadmap.stages[2].id == "s1"

    # 2. Merge s2 and s1
    merged = StageOperationsEngine.merge_stages(roadmap, "s2", "s1", "Merged Stages")
    assert merged is not None
    assert merged.title == "Merged Stages"
    assert len(roadmap.stages) == 2

    # 3. Remedial stage creation
    target_stage = roadmap.stages[0]
    remedial = RemedialEngine.create_remedial_stage(target_stage, "Prereq Concept")
    assert remedial.is_remedial is True
    assert "Remedial Recap" in remedial.title
    assert len(remedial.activities) == 3


def test_change_impact():
    roadmap = get_mock_roadmap()
    stage = roadmap.stages[0]
    # Set a resource to READY
    for rec in stage.resource_recommendations:
        if rec.resource_type == ResourceType.PPT:
            rec.status = ResourceStatus.READY

    # Modify objective
    stale = ChangeImpactEngine.analyze_stage_modification(stage, ["objectives"])
    assert ResourceType.PPT in stale
    ppt_rec = next(r for r in stage.resource_recommendations if r.resource_type == ResourceType.PPT)
    assert ppt_rec.status == ResourceStatus.STALE


def test_semester_planner():
    units = [
        {"id": "u1", "unit_number": 1, "title": "Intro", "topics": ["DBMS Intro", "Data Models", "ER Diagrams"]},
        {"id": "u2", "unit_number": 2, "title": "Relational Model", "topics": ["Relational Algebra", "SQL Lab"]}
    ]
    graph = CourseIntelligenceEngine.build_concept_graph("c1", "DBMS", units, [], [])
    plan = CourseIntelligenceEngine.generate_semester_plan(
        course_id="c1",
        units=graph.units,
        start_date=datetime(2026, 9, 1),
        total_weeks=14,
        classes_per_week=3,
        minutes_per_class=60
    )
    assert len(plan.scheduled_lessons) == 14 * 3
    assert any(s.is_exam for s in plan.scheduled_lessons)
    assert any(s.is_practical for s in plan.scheduled_lessons)
