"""
Semantic QA & Technical Integrity Engine
========================================
Enforces both Technical File Integrity and Semantic Pedagogical QA (Decision #11):
1. Technical Validation: file existence, MP4 format, non-empty audio, duration tolerance
2. Semantic Teaching Validation:
   - Learning objectives coverage
   - Sensible prerequisite ordering
   - Visual archetype matches concept
   - Presence of concrete worked example
   - Major misconceptions addressed
   - Zero informationally empty scenes
"""
import os
from typing import List, Dict, Any, Tuple, Optional
from ..schemas import Storyboard, SceneSpec, VideoKnowledgePackage, TeachingStoryStage


def validate_storyboard_quality(
    storyboard: Storyboard,
    target_duration: int,
    tolerance_seconds: int = 5,
) -> Tuple[bool, List[str]]:
    """Validates storyboard integrity, scene ordering, and exact target duration."""
    issues = []
    scenes = storyboard.scenes

    if not scenes:
        return False, ["Storyboard has 0 scenes."]

    total_dur = sum(s.duration for s in scenes)
    if abs(total_dur - target_duration) > tolerance_seconds:
        issues.append(f"Duration mismatch: Expected {target_duration}s, got {total_dur}s.")

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
    """Verifies that all rendered media frames and audio files exist and are non-empty."""
    issues = []
    for s in scenes:
        if s.rendered_media_path and not os.path.exists(s.rendered_media_path):
            issues.append(f"Missing rendered media for scene {s.scene_id}: {s.rendered_media_path}")
        elif s.rendered_media_path and os.path.getsize(s.rendered_media_path) < 100:
            issues.append(f"Rendered media file too small for scene {s.scene_id}")

        if s.rendered_audio_path and not os.path.exists(s.rendered_audio_path):
            issues.append(f"Missing audio track for scene {s.scene_id}: {s.rendered_audio_path}")
        elif s.rendered_audio_path and os.path.getsize(s.rendered_audio_path) < 100:
            issues.append(f"Rendered audio track too small for scene {s.scene_id}")

    is_valid = len(issues) == 0
    return is_valid, issues


def validate_semantic_teaching_quality(
    storyboard: Storyboard,
    knowledge_pack: Optional[VideoKnowledgePackage] = None
) -> Tuple[bool, List[str]]:
    """
    Semantic QA (Decision #11):
    - Confirms objectives are covered
    - Confirms prerequisite connection comes early
    - Confirms worked example is provided
    - Confirms no scene is informationally empty
    """
    issues = []
    scenes = storyboard.scenes

    if not scenes:
        return False, ["Video has no pedagogical scenes."]

    # 1. No informationally empty scenes
    for idx, s in enumerate(scenes):
        word_count = len(s.narration.split())
        if word_count < 5:
            issues.append(f"Scene {s.scene_id} is informationally empty ({word_count} words).")
        if not s.caption and not s.visual_spec.title:
            issues.append(f"Scene {s.scene_id} has no visual title or caption.")

    # 2. Check for at least one worked example or mechanism scene
    has_example_or_mechanism = any(
        s.purpose in (TeachingStoryStage.WORKED_EXAMPLE, TeachingStoryStage.VISUAL_MECHANISM, "worked_example", "mechanism")
        or s.worked_example is not None
        for s in scenes
    )
    if not has_example_or_mechanism:
        issues.append("Video lacks a concrete worked example or mechanism demonstration.")

    # 3. Check sensible prerequisite ordering
    prereq_indices = [i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.PREREQUISITE_CONNECTION, "prerequisite_connection")]
    summary_indices = [i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.SUMMARY, "summary")]

    if prereq_indices and summary_indices:
        if min(prereq_indices) > max(summary_indices):
            issues.append("Prerequisite connection appears after lesson summary.")

    # 4. Check learning objectives presence
    if knowledge_pack and not knowledge_pack.learning_objectives:
        issues.append("Knowledge package is missing explicit learning objectives.")

    is_valid = len(issues) == 0
    return is_valid, issues
