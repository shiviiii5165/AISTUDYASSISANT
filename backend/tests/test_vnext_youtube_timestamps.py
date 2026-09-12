import pytest
from app.services.lesson_planner.schemas import RoadmapStage, StageArchetype, TopicVolatility
from app.services.lesson_planner.vnext.resources.youtube_router import YouTubeSegmentRouter
from app.core.config import settings


@pytest.fixture(autouse=True)
def enable_segments_for_unit_tests(monkeypatch):
    monkeypatch.setattr(settings, "LESSON_YOUTUBE_SEGMENTS_ENABLED", True)


class MockVideoItem:
    def __init__(self, title, url, channel, chapters=None, transcript=None, transcript_segments=None):
        self.title = title
        self.url = url
        self.channel = channel
        self.chapters = chapters or []
        self.transcript = transcript
        self.transcript_segments = transcript_segments or []


def _get_test_stage() -> RoadmapStage:
    return RoadmapStage(
        id="s_yt",
        concept_id="c_yt",
        title="Binary Search Algorithm",
        description="Divide and conquer search",
        sequence=0,
        duration_minutes=15,
        archetype=StageArchetype.DEMONSTRATION
    )


def test_chapter_based_timestamp_provenance():
    """Video with verified chapters matching concept extracts valid segment and provenance."""
    stage = _get_test_stage()
    video = MockVideoItem(
        title="Complete Algorithms: Binary Search Explained",
        url="https://youtube.com/watch?v=xyz12345",
        channel="MIT OpenCourseWare",
        chapters=[
            {"title": "Introduction to Linear Search", "start_time": 0, "end_time": 180},
            {"title": "Binary Search Algorithm Implementation", "start_time": 180, "end_time": 480}
        ]
    )

    card = YouTubeSegmentRouter._score_and_segment(
        item=video,
        stage=stage,
        topic="Binary Search",
        learner_level="B.Tech",
        volatility=TopicVolatility.LOW
    )

    assert card.timestamp_source == "video_chapters"
    assert card.segment_confidence >= 0.90
    assert card.timestamp_start == "03:00"
    assert card.timestamp_end == "08:00"
    assert "t=180s" in card.url


def test_unverified_video_falls_back_to_whole_video():
    """
    Video without verified chapters or transcripts falls back cleanly
    to whole-video recommendation rather than fabricating a fake segment!
    """
    stage = _get_test_stage()
    video = MockVideoItem(
        title="Binary Search in 10 Minutes",
        url="https://youtube.com/watch?v=abc99999",
        channel="Gate Smashers"
    )

    card = YouTubeSegmentRouter._score_and_segment(
        item=video,
        stage=stage,
        topic="Binary Search",
        learner_level="B.Tech",
        volatility=TopicVolatility.LOW
    )

    assert card.timestamp_source == "whole_video"
    assert card.transcript_available is False
    assert card.timestamp_start is None
    assert card.timestamp_end is None
    assert card.type == "video"
    assert "t=" not in card.url
