import pytest
from app.services.lesson_planner.schemas import (
    ProductMode, CanonicalDomain, TeachingIntent, StageStatus
)
from app.services.lesson_planner.vnext.compiler import LessonCompiler


@pytest.mark.anyio
async def test_lesson_compiler_pipeline():
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Binary Search Trees",
        grade="B.Tech",
        subject="Data Structures",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    assert roadmap.topic == "Binary Search Trees"
    assert roadmap.mode == ProductMode.TEACHER_CLASSROOM
    assert roadmap.domain == CanonicalDomain.COMPUTER_SCIENCE
    assert roadmap.adaptive_reserve_minutes > 0
    assert len(roadmap.stages) >= 4

    # Timing check
    total_stage_time = sum(s.duration_minutes for s in roadmap.stages)
    assert total_stage_time + roadmap.adaptive_reserve_minutes == 60

    # Stage contract check
    first_stage = roadmap.stages[0]
    assert first_stage.status == StageStatus.AVAILABLE
    assert len(first_stage.teacher_actions) > 0
    assert len(first_stage.student_actions) > 0
    assert first_stage.why_now != ""
    assert first_stage.teaching_goal != ""
