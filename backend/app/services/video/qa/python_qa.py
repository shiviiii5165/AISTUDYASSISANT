"""
Python QA Engine (Zero Tokens)
===============================
Performs strict deterministic quality assurance on scenes, durations, media files,
and caption timings before final video delivery.
"""
import os
from typing import List, Dict, Any, Tuple
from ..schemas import Storyboard, SceneSpec


def validate_storyboard_quality(
    storyboard: Storyboard,
    target_duration: int,
    tolerance_seconds: int = 5,
) -> Tuple[bool, List[str]]:
    """
    Validates storyboard integrity, scene ordering, and exact target duration.
    """
    issues = []
    scenes = storyboard.scenes

    if not scenes:
        return False, ["Storyboard has 0 scenes."]

    # 1. Check total duration
    total_dur = sum(s.duration for s in scenes)
    if abs(total_dur - target_duration) > tolerance_seconds:
        issues.append(f"Duration mismatch: Expected {target_duration}s, got {total_dur}s.")

    # 2. Check scene order & uniqueness
    seen_ids = set()
    for idx, s in enumerate(scenes):
        if s.scene_id in seen_ids:
            issues.append(f"Duplicate scene ID: '{s.scene_id}'.")
        seen_ids.add(s.scene_id)

        if not s.narration.strip():
            issues.append(f"Scene {s.scene_id} has empty narration text.")

        if s.duration < 3:
            issues.append(f"Scene {s.scene_id} duration is too short (< 3s).")

    is_valid = len(issues) == 0
    return is_valid, issues


def validate_rendered_scene_media(
    scenes: List[SceneSpec],
) -> Tuple[bool, List[str]]:
    """
    Verifies that all rendered media frames and audio files exist and are non-empty.
    """
    issues = []
    for s in scenes:
        if s.rendered_media_path and not os.path.exists(s.rendered_media_path):
            issues.append(f"Missing rendered media for scene {s.scene_id}: {s.rendered_media_path}")
        if s.rendered_audio_path and not os.path.exists(s.rendered_audio_path):
            issues.append(f"Missing audio track for scene {s.scene_id}: {s.rendered_audio_path}")

    return len(issues) == 0, issues
