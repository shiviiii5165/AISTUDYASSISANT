"""
Graph & 2D Curve Plot Visualizer Archetype
==========================================
Renders 2D scientific and mathematical plots, curves, coordinate systems,
and data relations using Matplotlib/Pillow (e.g. F=ma, Supply & Demand, Derivative Slopes).
"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec, PlotData


class GraphPlotVisualizer(BaseVisualizer):
    """Renders GRAPH_PLOT archetype."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        pdata: PlotData = scene.visual_spec.plot_data
        if not pdata or not pdata.series:
            # Fallback linear plot F = ma
            import numpy as np
            xs = [0, 2, 4, 6, 8, 10]
            ys = [0, 10, 20, 30, 40, 50]
            title = scene.visual_spec.title or "F = m * a (Force vs Acceleration)"
            xlabel = "Acceleration a (m/s²)"
            ylabel = "Net Force F (Newtons)"
            label = "Mass m = 5 kg"
        else:
            xs = pdata.series[0].x_values or [0, 1, 2, 3, 4]
            ys = pdata.series[0].y_values or [0, 2, 4, 6, 8]
            title = pdata.title or scene.visual_spec.title or "Scientific Relationship Plot"
            xlabel = pdata.x_label or "X Axis"
            ylabel = pdata.y_label or "Y Axis"
            label = pdata.series[0].label or "Function Curve"

        # Render plot to in-memory PNG
        fig, ax = plt.subplots(figsize=(10, 5.2), dpi=100)
        fig.patch.set_facecolor("#0F172A")
        ax.set_facecolor("#1E293B")

        # Plot curve
        ax.plot(xs, ys, color="#38BDF8", linewidth=3, marker="o", markersize=8, markerfacecolor="#10B981", label=label)
        ax.set_title(title, color="#F8FAFC", fontsize=16, fontweight="bold", pad=15)
        ax.set_xlabel(xlabel, color="#94A3B8", fontsize=12)
        ax.set_ylabel(ylabel, color="#94A3B8", fontsize=12)

        # Style ticks and grid
        ax.tick_params(colors="#94A3B8", labelsize=10)
        ax.grid(True, linestyle="--", alpha=0.25, color="#64748B")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

        ax.legend(facecolor="#1E293B", edgecolor="#38BDF8", labelcolor="#F8FAFC")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        plot_img = Image.open(buf)

        # Composite onto main canvas
        canvas, draw = cls.create_canvas(title=scene.visual_spec.title or scene.caption, subtitle=scene.caption, tag="GRAPH PLOT")
        # Center plot on canvas
        px = (cls.WIDTH - plot_img.width) // 2
        py = 170
        canvas.paste(plot_img, (px, py))

        canvas.save(output_path, "PNG")
        return output_path
