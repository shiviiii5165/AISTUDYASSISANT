"""
Caption & Subtitle Generator (Zero LLM Tokens)
==============================================
Generates synchronized .srt and .ass subtitles from scene narration scripts
and timeline boundaries.
"""
import os
from typing import List, Dict, Any
from ..schemas import SceneSpec


def format_timestamp_srt(seconds: float) -> str:
    """Formats float seconds into SRT timestamp format: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def generate_srt_subtitles(scenes: List[SceneSpec], output_path: str) -> str:
    """
    Builds a synchronized .srt file across all scenes in the storyboard.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    srt_blocks = []
    current_time = 0.0
    subtitle_idx = 1

    for scene in scenes:
        scene_start = current_time
        scene_duration = max(3.0, float(scene.duration))
        scene_end = scene_start + scene_duration
        narration = scene.narration.strip()

        if narration:
            # Segment into smaller sentences/phrases if narration is long
            sentences = [s.strip() for s in narration.split(".") if s.strip()]
            if not sentences:
                sentences = [narration]

            sub_duration = scene_duration / len(sentences)
            for i, sent in enumerate(sentences):
                sub_start = scene_start + (i * sub_duration)
                sub_end = sub_start + sub_duration
                
                block = f"{subtitle_idx}\n{format_timestamp_srt(sub_start)} --> {format_timestamp_srt(sub_end)}\n{sent}\n"
                srt_blocks.append(block)
                subtitle_idx += 1

        current_time = scene_end

    full_srt_content = "\n".join(srt_blocks)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_srt_content)

    return output_path
