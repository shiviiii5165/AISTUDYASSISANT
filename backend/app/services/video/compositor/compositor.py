"""
FFmpeg Video Compositor & Pipeline Normalizer
=============================================
Assembles scene clips, graphics frames, audio tracks, and burns captions
into a professional, broadcast-standard MP4 (H.264 / AAC / 30fps / 1280x720).
"""
import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional


def check_ffmpeg_available() -> bool:
    """Checks if ffmpeg is accessible on the system PATH."""
    return shutil.which("ffmpeg") is not None


def compose_single_scene_clip(
    image_path: str,
    audio_path: str,
    output_mp4_path: str,
    duration: float = 5.0,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
) -> str:
    """
    Renders an image frame + audio file into a normalized H.264/AAC MP4 video clip.
    """
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)

    if check_ffmpeg_available():
        # FFmpeg command: loop image for audio duration, scale to 720p, encode H.264 / AAC
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={width}:{height}",
            "-r", str(fps),
            "-shortest",
            output_mp4_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_mp4_path
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", "ignore")[-800:]
            raise RuntimeError(f"FFmpeg scene render failed: {stderr}") from e

    # Never write a placeholder file: a fake byte string is not a valid MP4 and
    # would be uploaded and served as a corrupt video ("Cannot parse metadata").
    # Fail loudly so the pipeline marks the job failed instead of shipping garbage.
    raise RuntimeError(
        "FFmpeg is not available on PATH; cannot render scene clip. "
        "Install ffmpeg (see backend/Dockerfile) to enable video generation."
    )


def concatenate_scenes_to_final_video(
    scene_clip_paths: List[str],
    output_final_path: str,
) -> str:
    """
    Concatenates normalized scene MP4 clips into the final video file.
    """
    os.makedirs(os.path.dirname(output_final_path), exist_ok=True)

    if not scene_clip_paths:
        raise RuntimeError("No scene clips were produced; cannot concatenate final video.")

    if check_ffmpeg_available():
        # Create concat list file
        concat_list_file = output_final_path + ".txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in scene_clip_paths:
                # Use forward slashes for ffmpeg concat list
                norm_p = os.path.abspath(p).replace("\\", "/")
                f.write(f"file '{norm_p}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file,
            "-c", "copy",
            output_final_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(concat_list_file):
                os.remove(concat_list_file)
            return output_final_path
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", "ignore")[-800:]
            raise RuntimeError(f"FFmpeg concat failed: {stderr}") from e

    raise RuntimeError(
        "FFmpeg is not available on PATH; cannot concatenate final video."
    )
