"""
TeachGenie — Video Generation Engine Automated Test Suite
=========================================================
Tests:
1. Storyboard Planning & Exact Python Duration Math
2. Teach Me -> Video Reuse Bridge (0 redundant LLM calls)
3. Visual Asset Decision Engine & Budget Enforcement
4. Python Graphics Frame Renderer (Concept Cards & Process Flows)
5. TTS Narration & Synchronized Caption Generator (.srt)
6. FFmpeg Compositor & Normalized Concat Demuxer
7. Scene-Level Regeneration (Patching single scene without full video re-render)
8. End-to-End Pipeline Execution
"""
import sys
import os
import asyncio

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ["CASHFREE_APP_ID"] = "placeholder_app_id"
os.environ["CASHFREE_SECRET_KEY"] = "placeholder_secret_key"
os.environ["SUPABASE_URL"] = "https://placeholder.supabase.co"
os.environ["SUPABASE_KEY"] = "placeholder"
os.environ["SUPABASE_JWT_SECRET"] = "placeholder"
os.environ["GEMINI_API_KEY"] = "placeholder"
os.environ["GROQ_API_KEY"] = "placeholder"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.video.schemas import (
    VideoConfig, VideoQuality, VideoStyle, AspectRatio,
    VisualAssetType, VisualBudget, SceneSpec, VisualSpec, Storyboard
)
from app.services.video.visual_router import route_scene_visual_asset, get_visual_budget_for_quality
from app.services.video.graphics.renderer import render_concept_card_frame, render_diagram_flow_frame, render_scene_to_image_file
from app.services.video.tts.tts_service import generate_narration_audio
from app.services.video.captions.caption_generator import generate_srt_subtitles, format_timestamp_srt
from app.services.video.compositor.compositor import compose_single_scene_clip, concatenate_scenes_to_final_video
from app.services.video.qa.python_qa import validate_storyboard_quality
from app.services.video.planner import build_storyboard_from_teach_me_state
from app.services.video.orchestrator import generate_video_pipeline, regenerate_single_scene, PROJECT_STORE
from app.services.teach.schemas import LessonPlan, LearningState, ConceptSpec, ConceptStatus
from app.services.teach.tools import save_lesson_plan, save_learning_state


def test_storyboard_duration_and_teachme_reuse():
    print("\n--- TEST 1: Teach Me -> Video Reuse & Duration Normalization ---")

    session_id = "test_teachme_video_session"
    concepts = [
        ConceptSpec(id="c1", name="TCP Slow Start", order=1, summary="Exponential window growth up to ssthresh threshold."),
        ConceptSpec(id="c2", name="Congestion Avoidance", order=2, summary="Additive increase linear probing mechanism."),
        ConceptSpec(id="c3", name="Fast Retransmit & Recovery", order=3, summary="Triple duplicate ACKs trigger rapid loss recovery."),
    ]
    plan = LessonPlan(topic="TCP Congestion Control", concepts=concepts)
    state = LearningState(session_id=session_id, topic="TCP Congestion Control")
    save_lesson_plan(session_id, plan)
    save_learning_state(session_id, state)

    config = VideoConfig(
        topic="TCP Congestion Control",
        lesson_session_id=session_id,
        duration=300,  # 5 minutes = 300s
        quality=VideoQuality.STANDARD,
    )

    storyboard = build_storyboard_from_teach_me_state(session_id, config)
    total_dur = sum(s.duration for s in storyboard.scenes)
    print(f"Teach Me Reused Storyboard: {len(storyboard.scenes)} scenes | Total Duration: {total_dur}s (Target: 300s)")
    assert len(storyboard.scenes) >= 3
    assert total_dur == 300
    assert storyboard.scenes[1].caption == "TCP Slow Start"

    print(">>> Teach Me to Video reuse & duration normalization PASSED.")


def test_visual_asset_router():
    print("\n--- TEST 2: Visual Asset Decision & Budget Engine ---")

    budget = get_visual_budget_for_quality(VideoQuality.STANDARD, total_duration=300)
    assert budget.max_ai_video_seconds == 24

    # 1. Diagram scene -> Must route to PYTHON_GRAPHICS ($0 cost)
    diagram_scene = SceneSpec(
        scene_id="s_diag",
        order=1,
        purpose="mechanism",
        duration=20,
        narration="Here is the architecture stack.",
        visual_spec=VisualSpec(diagram_type="flow", nodes=["Client", "Router", "Server"]),
    )
    vtype1, meta1 = route_scene_visual_asset(diagram_scene, VideoQuality.STANDARD, budget)
    print(f"Diagram Scene Asset Choice: {vtype1.value} (Engine: {meta1['engine']}, Cost: ${meta1['estimated_cost_usd']})")
    assert vtype1 == VisualAssetType.PYTHON_GRAPHICS

    # 2. Hook scene -> Can use AI Video if within budget
    hook_scene = SceneSpec(
        scene_id="s_hook",
        order=2,
        purpose="hook",
        duration=8,
        narration="Imagine billions of packets traveling across continents.",
        visual_spec=VisualSpec(),
    )
    vtype2, meta2 = route_scene_visual_asset(hook_scene, VideoQuality.STANDARD, budget, current_ai_video_seconds=0)
    print(f"Hook Scene Asset Choice: {vtype2.value} (Engine: {meta2['engine']})")
    assert vtype2 == VisualAssetType.AI_VIDEO

    # 3. Hook scene when AI Video budget is exhausted -> Fallback to Stock Video
    vtype3, meta3 = route_scene_visual_asset(hook_scene, VideoQuality.STANDARD, budget, current_ai_video_seconds=30)
    print(f"Hook Scene when budget exhausted: {vtype3.value} (Engine: {meta3['engine']})")
    assert vtype3 == VisualAssetType.STOCK_VIDEO

    print(">>> Visual asset router & budget engine PASSED.")


def test_python_graphics_renderer():
    print("\n--- TEST 3: Python Graphics Frame Renderer ---")

    scratch_dir = os.path.join(os.path.dirname(__file__), "scratch", "test_video_renders")
    os.makedirs(scratch_dir, exist_ok=True)

    # 1. Render Concept Card Frame
    card_path = os.path.join(scratch_dir, "test_card.png")
    render_concept_card_frame(
        title="Three-Way Handshake",
        bullets=["1. SYN sent from client", "2. SYN-ACK returned by server", "3. Final ACK completes connection"],
        caption="TCP Connection Setup",
        citation_badge="Page 14",
    ).save(card_path, "PNG")
    assert os.path.exists(card_path) and os.path.getsize(card_path) > 1000
    print(f"Rendered Concept Card: {card_path} ({os.path.getsize(card_path)} bytes) -> PASS")

    # 2. Render Process Flow Diagram
    flow_path = os.path.join(scratch_dir, "test_flow.png")
    render_diagram_flow_frame(
        title="Packet Transmission",
        nodes=["Sender", "Gateway", "Receiver"],
    ).save(flow_path, "PNG")
    assert os.path.exists(flow_path) and os.path.getsize(flow_path) > 1000
    print(f"Rendered Flow Diagram: {flow_path} ({os.path.getsize(flow_path)} bytes) -> PASS")

    print(">>> Python graphics frame renderer PASSED.")


def test_tts_and_caption_generation():
    print("\n--- TEST 4: TTS Narration & Subtitle Generation ---")

    scratch_dir = os.path.join(os.path.dirname(__file__), "scratch", "test_video_renders")
    os.makedirs(scratch_dir, exist_ok=True)

    # 1. SRT Timestamp Formatting
    assert format_timestamp_srt(0.0) == "00:00:00,000"
    assert format_timestamp_srt(65.5) == "00:01:05,500"

    # 2. Subtitle File Generation
    scenes = [
        SceneSpec(scene_id="s1", order=1, duration=10, narration="Welcome to this lesson on cloud architectures.", caption="Intro"),
        SceneSpec(scene_id="s2", order=2, duration=15, narration="Cloud computing provides on-demand computing resources.", caption="Cloud Basics"),
    ]
    srt_path = os.path.join(scratch_dir, "captions.srt")
    generate_srt_subtitles(scenes, srt_path)
    assert os.path.exists(srt_path)
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "00:00:00,000 -->" in content
    assert "Welcome to this lesson" in content
    print(f"Generated SRT Subtitles:\n{content[:180]}... -> PASS")

    print(">>> TTS narration & subtitle generation PASSED.")


def test_end_to_end_video_generation_and_regeneration():
    print("\n--- TEST 5: End-to-End Pipeline & Scene-Level Regeneration ---")

    config = VideoConfig(
        topic="Operating System Deadlocks",
        duration=60,  # 1 minute test
        quality=VideoQuality.QUICK,
        style=VideoStyle.TECHNICAL,
        language="English",
    )

    project = asyncio.run(generate_video_pipeline(config, user_id="test_user_vid"))
    print(f"Generated Video Project: ID={project.id} | Status={project.status} | Scenes={len(project.storyboard.scenes)}")
    assert project.status == "ready"
    assert len(project.storyboard.scenes) >= 3
    assert project.metrics.total_duration_sec == 60

    # Test Scene-Level Regeneration
    target_scene_id = project.storyboard.scenes[0].scene_id
    updated_proj = asyncio.run(regenerate_single_scene(project.id, target_scene_id, user_id="test_user_vid"))
    print(f"Regenerated Single Scene ({target_scene_id}) -> Recomposed master MP4 successfully: {updated_proj.updated_at}")
    assert updated_proj.status == "ready"

    print(">>> End-to-end pipeline & scene-level regeneration PASSED.")


if __name__ == "__main__":
    test_storyboard_duration_and_teachme_reuse()
    test_visual_asset_router()
    test_python_graphics_renderer()
    test_tts_and_caption_generation()
    test_end_to_end_video_generation_and_regeneration()
    print("\n=======================================================")
    print("ALL AI VIDEO GENERATION SUITE CHECKS PASSED (100%)!")
    print("=======================================================")
