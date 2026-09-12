"""
Timeline & Chronology Visualizer Archetype
==========================================
Renders chronological events, historical timelines, and cause-effect chains
(e.g., French Revolution, Computer Architecture Evolution, Scientific Discoveries).
Features horizontal timeline axis, milestone nodes, date badges, and progressive event reveals.
"""
from typing import List
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec, TimelineEvent


class TimelineVisualizer(BaseVisualizer):
    """Renders TIMELINE and CAUSE_EFFECT."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="TIMELINE"
        )

        events: List[TimelineEvent] = scene.visual_spec.timeline_events
        if not events:
            # Fallback mock events from bullets or defaults
            bullets = scene.visual_spec.bullets or ["Phase 1: Catalyst", "Phase 2: Turning Point", "Phase 3: Impact"]
            events = [
                TimelineEvent(time_label=f"Stage {i+1}", title=b, description="Key Historical Transformation")
                for i, b in enumerate(bullets[:4])
            ]

        n_events = min(4, len(events))
        axis_y = 360
        start_x = 120
        end_x = cls.WIDTH - 120
        step_x = (end_x - start_x) // max(1, n_events - 1)

        # Draw main axis line
        draw.line([(start_x, axis_y), (end_x, axis_y)], fill=PALETTE["card_border"], width=4)

        # Animated progress fill along the axis
        animated_end_x = int(start_x + (end_x - start_x) * progress)
        draw.line([(start_x, axis_y), (animated_end_x, axis_y)], fill=PALETTE["primary"], width=4)

        font_time = cls.get_font(15, bold=True)
        font_title = cls.get_font(18, bold=True)
        font_desc = cls.get_font(14, bold=False)

        for i in range(n_events):
            nx = start_x + i * step_x
            is_revealed = (nx <= animated_end_x)

            node_color = PALETTE["primary"] if is_revealed else PALETTE["card_border"]
            node_radius = 12 if is_revealed else 9

            # Node circle on axis
            draw.ellipse([nx - node_radius, axis_y - node_radius, nx + node_radius, axis_y + node_radius], fill=node_color, outline=PALETTE["bg"], width=3)

            # Alternate cards above and below the axis
            is_above = (i % 2 == 0)
            card_w = 220
            card_h = 130
            card_x1 = nx - (card_w // 2)
            card_x2 = card_x1 + card_w

            if is_above:
                card_y2 = axis_y - 25
                card_y1 = card_y2 - card_h
                # Connecting vertical tick
                draw.line([(nx, axis_y - node_radius), (nx, card_y2)], fill=node_color, width=2)
            else:
                card_y1 = axis_y + 25
                card_y2 = card_y1 + card_h
                # Connecting vertical tick
                draw.line([(nx, axis_y + node_radius), (nx, card_y1)], fill=node_color, width=2)

            if is_revealed:
                # Event card box
                draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=10, fill=PALETTE["card_bg"], outline=node_color, width=2)

                # Date Pill
                ev = events[i]
                draw.rounded_rectangle([card_x1 + 10, card_y1 + 10, card_x1 + 110, card_y1 + 35], radius=6, fill=PALETTE["accent_blue"])
                draw.text((card_x1 + 16, card_y1 + 14), ev.time_label[:14], fill=PALETTE["text_primary"], font=font_time)

                # Event Title
                draw.text((card_x1 + 12, card_y1 + 45), ev.title[:22], fill=PALETTE["text_primary"], font=font_title)

                # Description
                if ev.description:
                    draw.text((card_x1 + 12, card_y1 + 75), ev.description[:26], fill=PALETTE["text_muted"], font=font_desc)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_animation_frame(cls, scene: SceneSpec, progress: float, output_path: str):
        cls.render_scene(scene, output_path, progress=progress)
