"""
Content Creator Agent — Comprehensive Test Suite
================================================
12 pytest cases covering all functional requirements, cost guardrails,
fact-grounding prompt overrides, and job/status state machines.

Run with:
    pytest test_content_creator.py -v
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from app.agents.content_creator import (
    create_content,
    ContentRequest,
    ContentType,
    ContentStatus,
    ContentCreatorOutput,
    MAX_SLIDE_COUNT,
    MAX_VIDEO_DURATION_SEC,
    _get_job,
    _JOB_STORE
)
from app.agents.librarian import LibrarianOutput, ChunkResult
from app.services.presentation.schemas import PresentationSpec, PresentationConfig


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clear_job_store():
    """Clear the job store before each test."""
    _JOB_STORE.clear()


def _run(coro):
    """Run an async coroutine in a synchronous test."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _make_librarian_output(chunks=None) -> LibrarianOutput:
    """Build a LibrarianOutput with optional chunk text."""
    if not chunks:
        return LibrarianOutput(context=[], related_context=[], sufficient=False, used_web_fallback=False)
        
    context = []
    for i, text in enumerate(chunks):
        context.append(ChunkResult(
            text=text,
            source_document=f"doc_{i}",
            page_or_location=f"Page {i+1}",
            relevance_score=0.9,
            source="internal",
        ))
    return LibrarianOutput(
        context=context,
        related_context=[],
        sufficient=True,
        used_web_fallback=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 & 2: PPT with and without Librarian Context
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.content_creator.generate_presentation_pipeline", new_callable=AsyncMock)
def test_ppt_request_with_sufficient_context(mock_ppt_pipeline):
    """Valid PPT request with sufficient librarian_context → grounded_in_notes: True, topic injected."""
    mock_spec = PresentationSpec(title="Test", config=PresentationConfig(topic="Test", slide_count=10), slides=[])
    mock_ppt_pipeline.return_value = (mock_spec, b"fake_bytes")

    request = ContentRequest(
        content_type=ContentType.PPT,
        topic="Photosynthesis",
        librarian_context=_make_librarian_output(["Plants use sunlight to make food."]),
        generation_params={"slide_count": 10}
    )

    # Submission should return PROCESSING immediately
    output = _run(create_content(request))
    assert output.status == ContentStatus.PROCESSING
    assert output.job_id is not None
    assert output.grounded_in_notes is True

    # Allow the background task to complete
    _run(asyncio.sleep(0.1))

    # Poll status
    job = _get_job(output.job_id)
    assert job.status == ContentStatus.COMPLETE
    assert job.output_url_or_path == f"/mock_storage/{output.job_id}.pptx"

    # Assert underlying function called with custom_context correctly mapped
    mock_ppt_pipeline.assert_called_once()
    config_passed = mock_ppt_pipeline.call_args.kwargs["config"]
    
    # Topic MUST remain clean to avoid leaking prompt instructions into the UI
    assert config_passed.topic == "Photosynthesis"
    assert "DO NOT fabricate facts" not in config_passed.topic
    
    # The grounding instructions must be cleanly isolated in custom_context
    assert config_passed.custom_context is not None
    assert "Plants use sunlight" in config_passed.custom_context


@patch("app.agents.content_creator.generate_presentation_pipeline", new_callable=AsyncMock)
def test_ppt_request_with_no_context(mock_ppt_pipeline):
    """Valid PPT request with NO context → grounded_in_notes: False, topic unaltered."""
    mock_spec = PresentationSpec(title="Test", config=PresentationConfig(topic="Test", slide_count=10), slides=[])
    mock_ppt_pipeline.return_value = (mock_spec, b"fake_bytes")

    request = ContentRequest(
        content_type=ContentType.PPT,
        topic="Black Holes",
        librarian_context=_make_librarian_output([]),  # Empty
        generation_params={"slide_count": 12}
    )

    output = _run(create_content(request))
    assert output.grounded_in_notes is False

    _run(asyncio.sleep(0.1))
    job = _get_job(output.job_id)
    assert job.status == ContentStatus.COMPLETE

    # Assert topic is NOT injected
    config_passed = mock_ppt_pipeline.call_args.kwargs["config"]
    assert config_passed.topic == "Black Holes"
    assert "DO NOT fabricate facts" not in config_passed.topic


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: Video Routing
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.content_creator.generate_video_pipeline", new_callable=AsyncMock)
@patch("app.agents.content_creator.generate_presentation_pipeline", new_callable=AsyncMock)
def test_video_request_routes_to_video_service(mock_ppt_pipeline, mock_video_pipeline):
    """Valid video request correctly routes to the video service, not the ppt service."""
    mock_project = MagicMock()
    mock_project.final_video_url = "https://supabase.com/test.mp4"
    mock_video_pipeline.return_value = mock_project

    request = ContentRequest(
        content_type=ContentType.VIDEO,
        topic="Neural Networks",
        generation_params={"duration_seconds": 120}
    )

    output = _run(create_content(request))
    _run(asyncio.sleep(0.1))

    mock_video_pipeline.assert_called_once()
    mock_ppt_pipeline.assert_not_called()

    job = _get_job(output.job_id)
    assert job.status == ContentStatus.COMPLETE
    assert job.output_url_or_path == "https://supabase.com/test.mp4"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 & 5: Empty Topic & Unsupported Content Type
# ══════════════════════════════════════════════════════════════════════════════

def test_empty_topic_rejected_immediately():
    """Empty topic → rejected immediately, underlying services never called."""
    request = ContentRequest(
        content_type=ContentType.PPT,
        topic="   ",  # Whitespace only
    )
    output = _run(create_content(request))
    
    assert output.status == ContentStatus.FAILED
    assert "empty" in output.error_message.lower()
    assert output.job_id is None


def test_unsupported_content_type_pydantic():
    """Unsupported content_type throws Pydantic validation error before agent is called."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc:
        ContentRequest(content_type="hologram", topic="Future Tech")
    
    assert "Input should be" in str(exc.value)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 & 7: Cost and Resource Guardrails
# ══════════════════════════════════════════════════════════════════════════════

def test_slide_count_exceeding_cap_rejected():
    """Slide count exceeding cap → rejected with clear message."""
    request = ContentRequest(
        content_type=ContentType.PPT,
        topic="Too Many Slides",
        generation_params={"slide_count": MAX_SLIDE_COUNT + 5}
    )
    
    output = _run(create_content(request))
    assert output.status == ContentStatus.FAILED
    assert str(MAX_SLIDE_COUNT) in output.error_message
    assert output.job_id is None


def test_video_duration_exceeding_cap_rejected():
    """Video duration exceeding cap → rejected with clear message."""
    request = ContentRequest(
        content_type=ContentType.VIDEO,
        topic="Too Long Video",
        generation_params={"duration_seconds": MAX_VIDEO_DURATION_SEC + 100}
    )
    
    output = _run(create_content(request))
    assert output.status == ContentStatus.FAILED
    assert str(MAX_VIDEO_DURATION_SEC) in output.error_message


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: Underlying Service Exception Handling
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.content_creator.generate_presentation_pipeline", new_callable=AsyncMock)
def test_underlying_service_exception_caught(mock_ppt_pipeline):
    """Underlying service raises exception → caught, friendly error message, no crash."""
    mock_ppt_pipeline.side_effect = Exception("Supabase connection timeout at line 42")

    request = ContentRequest(content_type=ContentType.PPT, topic="Error Handling")
    output = _run(create_content(request))
    
    _run(asyncio.sleep(0.1))  # Wait for background task to fail
    
    job = _get_job(output.job_id)
    assert job.status == ContentStatus.FAILED
    # Error message must be friendly, no raw stack trace or raw exception string
    assert "Supabase" not in job.error_message
    assert "error" in job.error_message.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: Flashcard Sync Generation Path
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.content_creator.call_gemini", new_callable=AsyncMock)
def test_flashcard_generation_success(mock_gemini):
    """Flashcards are generated synchronously and returned directly in the output."""
    mock_gemini.return_value = '{"flashcards": [{"front": "Q1", "back": "A1"}]}'
    
    request = ContentRequest(
        content_type=ContentType.FLASHCARDS,
        topic="Basic Math",
        generation_params={"count": 1}
    )
    
    output = _run(create_content(request))
    
    # Must be COMPLETE immediately, no job_id needed for sync
    assert output.status == ContentStatus.COMPLETE
    assert output.content_type == ContentType.FLASHCARDS
    assert len(output.flashcards_data) == 1
    assert output.flashcards_data[0]["front"] == "Q1"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: Flashcard Fact Grounding Injection
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.content_creator.call_gemini", new_callable=AsyncMock)
def test_flashcard_grounded_does_not_fabricate(mock_gemini):
    """Flashcard generation with context explicitly includes 'DO NOT fabricate facts' in prompt."""
    mock_gemini.return_value = '{"flashcards": []}'
    
    request = ContentRequest(
        content_type=ContentType.FLASHCARDS,
        topic="Mitochondria",
        librarian_context=_make_librarian_output(["Powerhouse of the cell."]),
    )
    
    _run(create_content(request))
    
    mock_gemini.assert_called_once()
    messages = mock_gemini.call_args.kwargs["messages"]
    sys_prompt = messages[0]["content"]
    
    # Must include the grounding strictness instruction
    assert "DO NOT fabricate facts beyond this provided context" in sys_prompt
    assert "Powerhouse of the cell" in sys_prompt


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: Job Status Endpoint Equivalent (Direct function logic)
# ══════════════════════════════════════════════════════════════════════════════

def test_get_job_logic():
    """Verify the job state tracker logic for the /status endpoint."""
    _JOB_STORE["test_job_123"] = ContentCreatorOutput(
        job_id="test_job_123",
        content_type=ContentType.PPT,
        status=ContentStatus.PROCESSING
    )
    
    job = _get_job("test_job_123")
    assert job is not None
    assert job.status == ContentStatus.PROCESSING
    
# ══════════════════════════════════════════════════════════════════════════════
# TEST 12: Planner System Prompt Grounding Injection
# ══════════════════════════════════════════════════════════════════════════════

def test_custom_context_reaches_planners_cleanly():
    """Verify that custom_context safely reaches the system prompt without corrupting topic."""
    from app.services.presentation.planner_agent import plan_presentation
    from app.services.video.planner import plan_storyboard
    from app.services.video.schemas import VideoConfig
    from app.services.ai import router
    
    with patch.object(router, "generate_json", new_callable=AsyncMock) as mock_router:
        # 1. Test Presentation Planner
        mock_router.return_value = {"slides": [{"type": "hero"}], "deck_title": "Clean Title"}
        ppt_config = PresentationConfig(
            topic="Safe Topic",
            custom_context="Crucial grounding fact: 42",
            slide_count=10
        )
        _run(plan_presentation(ppt_config, user_id="test"))
        
        ppt_messages = mock_router.call_args.kwargs["messages"]
        ppt_sys = ppt_messages[0]["content"]
        ppt_user = ppt_messages[1]["content"]
        
        assert "Crucial grounding fact: 42" in ppt_sys
        assert "DO NOT fabricate facts" in ppt_sys
        assert "Safe Topic" in ppt_user
        assert "Crucial grounding fact: 42" not in ppt_user
        assert ppt_config.topic == "Safe Topic"  # Clean!
        
        mock_router.reset_mock()
        
        # 2. Test Video Planner
        mock_router.return_value = {"topic": "Clean Title", "scenes": [{"purpose": "hook"}]}
        vid_config = VideoConfig(
            topic="Safe Topic",
            custom_context="Crucial grounding fact: 42",
            duration=60
        )
        _run(plan_storyboard(vid_config, user_id="test"))
        
        vid_messages = mock_router.call_args.kwargs["messages"]
        vid_sys = vid_messages[0]["content"]
        vid_user = vid_messages[1]["content"]
        
        assert "Crucial grounding fact: 42" in vid_sys
        assert "DO NOT fabricate facts" in vid_sys
        assert "Safe Topic" in vid_user
        assert "Crucial grounding fact: 42" not in vid_user
        assert vid_config.topic == "Safe Topic"  # Clean!
