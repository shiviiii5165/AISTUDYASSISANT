"""
Test Suite: Bundled Icon Set Image-Level Consistency
====================================================
Verifies image-level consistency across all 10 bundled PNG icon assets:
1. All 10 expected PNG files exist in `backend/app/services/presentation_engine/assets/icons/`.
2. Resolution: Exactly 512x512 pixels with an RGBA color mode.
3. Alpha transparency: Genuine transparent background (alpha == 0) and solid foreground content.
4. Visual weight & padding: Bounding box of content occupies a balanced proportion
   of the 512x512 canvas (between 40% and 95% of width and height) so no icon appears
   tiny or oddly cropped.
5. Palette alignment: Non-transparent pixels follow pedagogical theme tones
   (navy #1E3A8A, cobalt, or dark neutral strokes/fills).
"""
import os
import pytest
from PIL import Image

ICONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "app", "services", "presentation_engine", "assets", "icons")
)

EXPECTED_ICONS = [
    "plate-stack.png",
    "queue-line.png",
    "tree-branch.png",
    "network-graph.png",
    "database-cylinder.png",
    "person.png",
    "definition-book.png",
    "warning-trap.png",
    "check-badge.png",
    "activity-icon.png"
]

def test_all_10_icons_exist():
    """Verify all 10 icon files exist in the bundled assets directory."""
    assert os.path.isdir(ICONS_DIR), f"Icons directory not found: {ICONS_DIR}"
    missing = [name for name in EXPECTED_ICONS if not os.path.isfile(os.path.join(ICONS_DIR, name))]
    assert not missing, f"Missing bundled icons: {missing}"

def test_icon_dimensions_and_alpha_transparency():
    """Verify each icon is exactly 512x512 with RGBA mode and real transparency."""
    for name in EXPECTED_ICONS:
        path = os.path.join(ICONS_DIR, name)
        if not os.path.exists(path):
            pytest.skip(f"Asset {name} not yet generated")
        with Image.open(path) as img:
            assert img.size == (512, 512), f"{name} size is {img.size}, expected (512, 512)"
            assert img.mode == "RGBA", f"{name} mode is {img.mode}, expected RGBA"

            # Check alpha channel presence and transparency
            alpha = img.split()[-1]
            extrema = alpha.getextrema()
            assert extrema[0] == 0, f"{name} must have transparent background pixels (min alpha == 0)"
            assert extrema[1] > 180, f"{name} must have solid content pixels (max alpha > 180)"

def test_icon_visual_weight_and_padding():
    """Verify bounding box occupies consistent visual weight without being clipped or shrunken."""
    for name in EXPECTED_ICONS:
        path = os.path.join(ICONS_DIR, name)
        assert os.path.exists(path), f"Asset {name} does not exist"
        with Image.open(path) as img:
            bbox = img.getbbox()
            assert bbox is not None, f"{name} bounding box is None (empty image)"
            left, upper, right, lower = bbox
            content_w = right - left
            content_h = lower - upper

            # Canvas is 512x512. Major dimension must be between 250px and 490px (50% to 95% of canvas)
            major_dim = max(content_w, content_h)
            minor_dim = min(content_w, content_h)
            assert 250 <= major_dim <= 490, (
                f"{name} major dimension ({major_dim}px) is outside balanced range [250, 490]"
            )
            assert minor_dim >= 150, (
                f"{name} minor dimension ({minor_dim}px) is too small (< 150px)"
            )
            # Ensure safe padding from extreme canvas edges
            assert left >= 10 and upper >= 10 and right <= 502 and lower <= 502, (
                f"{name} touches canvas boundary without margin: bbox={bbox}"
            )

def test_icon_color_palette_alignment():
    """Sample non-transparent pixels and verify palette aligns with navy/blue/slate tokens."""
    for name in EXPECTED_ICONS:
        path = os.path.join(ICONS_DIR, name)
        if not os.path.exists(path):
            pytest.skip(f"Asset {name} not yet generated")
        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            pixels = list(rgba.getdata())
            # Filter non-transparent pixels
            colored = [p for p in pixels if p[3] > 100]
            assert len(colored) > 1000, f"{name} has too few opaque pixels ({len(colored)})"

            # Check for dominant dark/navy/blue presence
            # In pedagogical theme: navy (#1E3A8A), cobalt, or dark line (#0F172A)
            # A valid icon should have significant presence of dark lines or blue-dominant tones
            blue_or_dark_count = 0
            for r, g, b, a in colored:
                is_dark_line = (r < 70 and g < 80 and b < 90)
                is_blue_tinted = (b >= r - 10 and b >= g - 10 and b > 50)
                is_white_fill = (r > 220 and g > 220 and b > 220)
                if is_dark_line or is_blue_tinted or is_white_fill:
                    blue_or_dark_count += 1

            consistency_ratio = blue_or_dark_count / len(colored)
            assert consistency_ratio >= 0.70, (
                f"{name} color palette consistency is {consistency_ratio:.2%}, "
                f"expected >= 70% blue/navy/dark-neutral alignment"
            )
