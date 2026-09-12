"""
Base Visualizer & Drawing Framework
===================================
Provides shared 1280x720 16:9 canvas creation, color tokens, typography,
shape drawing (rounded boxes, connectors, arrows, glowing halos),
and multi-frame animation compilation for all visualizer archetypes.
"""
import os
import math
from typing import Tuple, List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from ..schemas import SceneSpec
from ..compositor.compositor import compile_frames_to_animated_clip


# Modern Educational Design Tokens (Vibrant Dark/Academic Palette)
PALETTE = {
    "bg": (15, 23, 42),            # Dark slate #0F172A
    "card_bg": (30, 41, 59),       # #1E293B
    "card_border": (51, 65, 85),   # #334155
    "primary": (56, 189, 248),     # Cyan / Sky #38BDF8
    "accent_blue": (99, 102, 241), # Indigo #6366F1
    "accent_green": (16, 185, 129),# Emerald #10B981
    "accent_amber": (245, 158, 11),# Amber #F59E0B
    "accent_rose": (244, 63, 94),  # Rose #F43F5E
    "accent_purple": (168, 85, 247), # Purple #A855F7
    "text_primary": (248, 250, 252), # #F8FAFC
    "text_muted": (148, 163, 184),   # #94A3B8
    "header_line": (56, 189, 248)
}


class BaseVisualizer:
    """Base class for all visualizer archetypes and specialized engines."""

    WIDTH = 1280
    HEIGHT = 720

    @classmethod
    def get_font(cls, size: int, bold: bool = False) -> ImageFont.ImageFont:
        font_names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "segoeui.ttf"]
        for fn in font_names:
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @classmethod
    def create_canvas(cls, title: str = "", subtitle: str = "", tag: str = "") -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        """Creates a modern 1280x720 canvas with title banner, accent borders, and tags."""
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), color=PALETTE["bg"])
        draw = ImageDraw.Draw(img)

        # Top accent gradient line
        draw.rectangle([0, 0, cls.WIDTH, 6], fill=PALETTE["primary"])

        # Subtle background grid lines
        for x in range(0, cls.WIDTH, 80):
            draw.line([(x, 6), (x, cls.HEIGHT)], fill=(22, 32, 54), width=1)
        for y in range(6, cls.HEIGHT, 80):
            draw.line([(0, y), (cls.WIDTH, y)], fill=(22, 32, 54), width=1)

        # Header Title
        if title:
            font_title = cls.get_font(32, bold=True)
            draw.text((60, 45), title, fill=PALETTE["text_primary"], font=font_title)

        # Subtitle / Caption
        if subtitle:
            font_sub = cls.get_font(18, bold=False)
            draw.text((60, 88), subtitle, fill=PALETTE["text_muted"], font=font_sub)

        # Topic / Stage Tag
        if tag:
            font_tag = cls.get_font(14, bold=True)
            tag_text = tag.upper().replace("_", " ")
            # Pill badge on right
            draw.rounded_rectangle([cls.WIDTH - 240, 45, cls.WIDTH - 60, 80], radius=8, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=1)
            draw.text((cls.WIDTH - 225, 53), tag_text[:20], fill=PALETTE["primary"], font=font_tag)

        return img, draw

    @classmethod
    def draw_arrow(cls, draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], color: Tuple[int, int, int] = PALETTE["primary"], width: int = 3):
        """Draws a crisp directional vector arrow between two points."""
        draw.line([start, end], fill=color, width=width)
        # Arrowhead
        x1, y1 = start
        x2, y2 = end
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 14
        arrow_angle = math.pi / 6

        p1 = (x2 - arrow_len * math.cos(angle - arrow_angle), y2 - arrow_len * math.sin(angle - arrow_angle))
        p2 = (x2 - arrow_len * math.cos(angle + arrow_angle), y2 - arrow_len * math.sin(angle + arrow_angle))
        draw.polygon([end, p1, p2], fill=color)

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic") -> str:
        """Renders a single high-resolution frame. Subclasses should override with archetype visuals."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img, draw = cls.create_canvas(title=scene.visual_spec.title or scene.caption, subtitle=scene.caption, tag=scene.purpose if isinstance(scene.purpose, str) else scene.purpose.value)
        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def render_animated_clip(
        cls,
        scene: SceneSpec,
        output_clip_path: str,
        duration: float = 5.0,
        fps: int = 30
    ) -> str:
        """
        Renders a sequence of animated frames and compiles them via FFmpeg into an MP4 clip.
        Default implementation generates dynamic keyframes showing progressive reveals.
        """
        os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
        temp_dir = output_clip_path + "_frames"
        os.makedirs(temp_dir, exist_ok=True)

        total_frames = max(30, int(duration * fps))
        frame_paths: List[str] = []

        for frame_idx in range(total_frames):
            progress = frame_idx / float(total_frames)
            frame_path = os.path.join(temp_dir, f"frame_{frame_idx:04d}.png")
            cls._render_animation_frame(scene, progress, frame_path)
            frame_paths.append(frame_path)

        # Compile via FFmpeg
        compile_frames_to_animated_clip(frame_paths, output_clip_path, fps=fps, width=cls.WIDTH, height=cls.HEIGHT)

        # Cleanup temp frames
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        return output_clip_path

    @classmethod
    def _render_animation_frame(cls, scene: SceneSpec, progress: float, output_path: str):
        """Renders one frame along the progress trajectory (0.0 to 1.0). Subclasses override."""
        cls.render_scene(scene, output_path)
