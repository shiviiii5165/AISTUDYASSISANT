import pytest
from app.services.lesson_planner.schemas import LearningRoadmap, RoadmapStage, StageStatus, StageActivity
from app.services.lesson_planner.engine import TimeBudgetEngine, PrerequisiteEngine, LessonHealthValidator, StateMachineEngine
from app.services.lesson_planner.adapters import PPTAdapter, VideoAdapter, TeachMeAdapter

def get_mock_roadmap():
    return LearningRoadmap(
        id="r1",
        course_id="c1",
        topic="DBMS Normalization",
        level="B.Tech",
        language="english",
        class_type="lecture",
        target_duration_minutes=60,
        stages=[
            RoadmapStage(
                id="s1",
                concept_id="c_func_dep",
                title="Functional Dependency",
                description="Intro to FD",
                duration_minutes=20,
                status=StageStatus.LOCKED,
                activities=[StageActivity(type="hook", description="intro", duration_minutes=5),
                            StageActivity(type="explanation", description="core", duration_minutes=15)],
                prerequisite_ids=[],
                checkpoint_questions=["What is FD?"],
                recommended_resources=["ppt"]
            ),
            RoadmapStage(
                id="s2",
                concept_id="c_1nf",
                title="1NF",
                description="First Normal Form",
                duration_minutes=20,
                status=StageStatus.LOCKED,
                activities=[StageActivity(type="explanation", description="1nf core", duration_minutes=20)],
                prerequisite_ids=["c_func_dep"],
                checkpoint_questions=["Rule of 1NF?"],
                recommended_resources=["video"]
            ),
            RoadmapStage(
                id="s3",
                concept_id="c_2nf",
                title="2NF",
                description="Second Normal Form",
                duration_minutes=20,
                status=StageStatus.LOCKED,
                activities=[StageActivity(type="explanation", description="2nf core", duration_minutes=20)],
                prerequisite_ids=["c_1nf"],
                checkpoint_questions=["Rule of 2NF?"],
                recommended_resources=["quiz"]
            )
        ]
    )

def test_prerequisite_engine():
    roadmap = get_mock_roadmap()
    
    # Initial state evaluation
    PrerequisiteEngine.evaluate_readiness(roadmap)
    assert roadmap.stages[0].status == StageStatus.AVAILABLE, "No prereqs should be AVAILABLE"
    assert roadmap.stages[1].status == StageStatus.BLOCKED, "Blocked by s1"
    assert roadmap.stages[2].status == StageStatus.BLOCKED, "Blocked by s2"

    # Simulate s1 is taught
    roadmap.stages[0].status = StageStatus.TAUGHT
    PrerequisiteEngine.evaluate_readiness(roadmap)
    assert roadmap.stages[1].status == StageStatus.AVAILABLE, "s2 should unlock"
    assert roadmap.stages[2].status == StageStatus.BLOCKED, "s3 still blocked"

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
    assert "Total time (70m) exceeds target (60m)" in warnings[0]

def test_lesson_health():
    roadmap = get_mock_roadmap()
    # Mock some gaps
    roadmap.stages[1].checkpoint_questions = []
    
    health = LessonHealthValidator.evaluate_health(roadmap)
    assert health["score"] < 100
    assert any("missing checkpoint" in w for w in health["warnings"])

def test_adapters():
    roadmap = get_mock_roadmap()
    stage = roadmap.stages[0]
    
    # 1. PPT Adapter
    ppt_config = PPTAdapter.create_presentation_config(roadmap, stage)
    assert ppt_config.topic == "Functional Dependency"
    assert ppt_config.slide_count == 10
    assert "Activities: ['hook', 'explanation']" in ppt_config.custom_context
    assert ppt_config.enable_quiz is True

    # 2. Video Adapter
    video_config = VideoAdapter.create_video_config(roadmap, stage)
    assert video_config.topic == "Functional Dependency"
    assert video_config.duration == 180 # 20 mins mapped to 3 mins video (next nearest threshold)

    # 3. TeachMe Adapter
    teach_context = TeachMeAdapter.create_teach_me_context(roadmap, stage)
    assert "What is FD?" in teach_context
