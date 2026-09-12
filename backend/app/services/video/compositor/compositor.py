"""
FFmpeg Video Compositor & Pipeline Normalizer
=============================================
Assembles animated scene clips, graphics frames, audio tracks, and synchronized subtitles
into a broadcast-standard MP4 (H.264 / AAC / 30fps / 1280x720).

FFmpeg Discovery Order:
1. FFMPEG_BINARY environment override
2. shutil.which("ffmpeg") system PATH
3. imageio_ffmpeg.get_ffmpeg_exe()
4. Local developer paths only as last resort
"""
import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional
from app.core.logging import logger


def get_ffmpeg_binary() -> str:
    """Discovers FFmpeg binary following the strict production cascade."""
    # 1. FFMPEG_BINARY environment override
    env_bin = os.environ.get("FFMPEG_BINARY")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    # 2. System PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # 3. imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass

    # 4. Developer-specific local paths (last resort)
    for local_path in [r"C:\KMPlayer\ffmpeg.exe"]:
        if os.path.isfile(local_path):
            return local_path

    return "ffmpeg"


def check_ffmpeg_available() -> bool:
    """Verifies that an executable ffmpeg binary is found and operational."""
    bin_path = get_ffmpeg_binary()
    try:
        res = subprocess.run([bin_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception:
        return False


def compile_frames_to_animated_clip(
    frame_paths: List[str],
    output_mp4_path: str,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
) -> str:
    """
    Compiles a sequence of rendered PNG frames into an H.264 MP4 animated video clip.
    """
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
    if not frame_paths:
        raise ValueError("No frames provided to compile animated clip.")

    ffmpeg_bin = get_ffmpeg_binary()
    # Write frames list file for concat
    list_file = output_mp4_path + "_frames.txt"
    frame_duration = 1.0 / fps

    with open(list_file, "w", encoding="utf-8") as f:
        for frame in frame_paths:
            norm_path = os.path.abspath(frame).replace("\\", "/")
            f.write(f"file '{norm_path}'\n")
            f.write(f"duration {frame_duration:.4f}\n")
        # Concat demuxer requirement: repeat last frame
        if frame_paths:
            last_frame = os.path.abspath(frame_paths[-1]).replace("\\", "/")
            f.write(f"file '{last_frame}'\n")

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={width}:{height}",
        "-r", str(fps),
        output_mp4_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(list_file):
            os.remove(list_file)
        return output_mp4_path
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", "ignore")[-800:]
        raise RuntimeError(f"FFmpeg frame sequence animation compilation failed: {stderr}") from e


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
    If image_path is actually an MP4 video clip, muxes audio with the video clip.
    """
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
    ffmpeg_bin = get_ffmpeg_binary()

    if not check_ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not available; cannot render scene clip. "
            "Please ensure imageio-ffmpeg is installed or ffmpeg is on system PATH."
        )

    is_video_input = image_path.lower().endswith(".mp4")

    if is_video_input:
        # Loop / stretch video or trim to match audio duration
        cmd = [
            ffmpeg_bin, "-y",
            "-stream_loop", "-1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={width}:{height}",
            "-r", str(fps),
            "-shortest",
            output_mp4_path
        ]
    else:
        # Loop still image frame for audio duration
        cmd = [
            ffmpeg_bin, "-y",
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

    ffmpeg_bin = get_ffmpeg_binary()
    concat_list_file = output_final_path + ".txt"

    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in scene_clip_paths:
            norm_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{norm_p}'\n")

    cmd = [
        ffmpeg_bin, "-y",
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
        raise RuntimeError(f"FFmpeg final concat failed: {stderr}") from e
