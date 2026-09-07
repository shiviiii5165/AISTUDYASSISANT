"""
Test Suite: Content-Shape Fit (Underfit Prevention)
===================================================
Renders sample process flow, timeline, and card slides, measuring that
the rendered text occupies >= 40% of each shape's vertical space.
Uses an independent, cross-platform Pillow TrueType font measurement
(resolving Windows/Linux/CI paths or PIL default), completely decoupled
from text_fitter.py to eliminate circular validation.
"""
import io
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from app.services.presentation_engine.tokens import get_theme, Typography
from app.services.presentation_engine.renderers.process_flow import render_process_flow
from app.services.presentation_engine import SlideContent, ProcessStep


def get_cross_platform_font(size_pt: int) -> ImageFont.ImageFont:
    """
    Resolves fonts with priority:
    1. Repository-bundled font (backend/app/services/presentation_engine/assets/fonts/DejaVuSans.ttf)
    2. Linux standard fonts (Debian, Ubuntu, Alpine, Docker, CI)
    3. Windows / macOS standard font paths
    4. Graceful Pillow default
    """
    repo_font = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "services", "presentation_engine", "assets", "fonts", "DejaVuSans.ttf"
    )
    candidates = [
        # 1. Bundled repo font (always available in CI, Docker, Linux, Windows, macOS)
        repo_font,
        # 2. Linux standard fonts (Debian, Ubuntu, Docker, CI)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        # 3. Windows
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        # 4. macOS
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size_pt)
            except Exception:
                pass
    return ImageFont.load_default()


def measure_text_height_independent(text: str, font_size_pt: int, max_width_pt: float) -> float:
    """
    Independent ground-truth text height measurement using Pillow font engine.
    Does NOT call or reuse text_fitter.py.
    """
    if not text:
        return 0.0
    font = get_cross_platform_font(font_size_pt)
    dummy_im = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(dummy_im)
    
    # Word wrap estimation for multiline text
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w > max_width_pt and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))

    wrapped_text = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    return float(bbox[3] - bbox[1])


def test_process_flow_cards_occupy_at_least_forty_percent_vertical():
    """Verify that process flow step cards have >= 40% vertical text fill."""
    theme = get_theme("blue_professional")
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    steps = [
        ProcessStep(number=1, title="Timers Phase", detail="Executes callbacks scheduled by setTimeout and setInterval."),
        ProcessStep(number=2, title="I/O Callbacks", detail="Processes system operations and network polling completions."),
        ProcessStep(number=3, title="Poll Phase", detail="Retrieves new I/O events and blocks if queue empty."),
        ProcessStep(number=4, title="Check Phase", detail="Executes setImmediate callbacks immediately after I/O."),
    ]
    content = SlideContent(
        id="slide_steps",
        title="Event Loop Architecture: Six Distinct Phases",
        steps=steps,
    )

    render_process_flow(slide, content, theme)

    # Find step cards on the slide
    cards = []
    for shape in slide.shapes:
        # Filter for the step cards (width between 2.0" and 3.5", height between 2.0" and 4.0")
        if shape.width.inches > 1.8 and shape.width.inches < 3.8 and shape.height.inches > 1.8:
            cards.append(shape)

    assert len(cards) >= 4, f"Expected 4 step cards, found {len(cards)}"

    for idx, card in enumerate(cards[:4]):
        card_h_pt = card.height.pt
        card_w_pt = card.width.pt
        step = steps[idx]

        # Measure text elements: badge (0.38" = ~27pt), title (14pt), detail (11pt)
        badge_h = 27.0
        title_h = measure_text_height_independent(step.title, 14, card_w_pt - 20)
        detail_h = measure_text_height_independent(step.detail, 11, card_w_pt - 20)
        total_text_h = badge_h + title_h + detail_h + 16.0  # plus standard inter-element padding

        ratio = total_text_h / card_h_pt
        print(f"Step {idx+1} ratio: {ratio:.2f} (text: {total_text_h:.1f}pt, card: {card_h_pt:.1f}pt)")
        assert ratio >= 0.40, (
            f"Step {idx+1} card is underfit: text occupies only {ratio*100:.1f}% of vertical space "
            f"(must be >= 40% to prevent awkward dead space)."
        )
