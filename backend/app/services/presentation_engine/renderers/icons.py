"""
TeachGenie Presentation Engine — Bundled Thematic Icon Renderer
==============================================================
Loads and renders bundled high-resolution static PNG icon assets for structural
CS concepts and pedagogical badges. Zero runtime API dependencies, 100% deterministic layout.
"""
import os
from typing import Optional
from pptx.slide import Slide
from pptx.util import Emu

ICONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
)

ICON_ALIASES = {
    "plate-stack": "plate-stack.png",
    "stack": "plate-stack.png",
    "lifo": "plate-stack.png",
    "queue-line": "queue-line.png",
    "queue": "queue-line.png",
    "fifo": "queue-line.png",
    "tree-branch": "tree-branch.png",
    "tree": "tree-branch.png",
    "hierarchy": "tree-branch.png",
    "network-graph": "network-graph.png",
    "graph": "network-graph.png",
    "topology": "network-graph.png",
    "database-cylinder": "database-cylinder.png",
    "database": "database-cylinder.png",
    "storage": "database-cylinder.png",
    "person": "person.png",
    "user": "person.png",
    "actor": "person.png",
    "definition-book": "definition-book.png",
    "book": "definition-book.png",
    "glossary": "definition-book.png",
    "warning-trap": "warning-trap.png",
    "warning": "warning-trap.png",
    "trap": "warning-trap.png",
    "pitfall": "warning-trap.png",
    "check-badge": "check-badge.png",
    "check": "check-badge.png",
    "badge": "check-badge.png",
    "discipline": "check-badge.png",
    "best-practice": "check-badge.png",
    "activity-icon": "activity-icon.png",
    "activity": "activity-icon.png",
    "exercise": "activity-icon.png",
    "workshop": "activity-icon.png"
}

def get_bundled_icon_path(icon_name: str) -> Optional[str]:
    """Resolve normalized bundled icon path by name or alias."""
    clean_name = icon_name.lower().strip().replace("_", "-")
    filename = ICON_ALIASES.get(clean_name, f"{clean_name}.png")
    path = os.path.join(ICONS_DIR, filename)
    if os.path.isfile(path):
        return path
    # Try direct without extension
    if not clean_name.endswith(".png"):
        path_png = os.path.join(ICONS_DIR, f"{clean_name}.png")
        if os.path.isfile(path_png):
            return path_png
    return None

def render_bundled_icon(
    slide: Slide,
    icon_name: str,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu
):
    """Embed the bundled static PNG icon into the slide deterministically."""
    path = get_bundled_icon_path(icon_name)
    if not path or not os.path.isfile(path):
        return None
    try:
        return slide.shapes.add_picture(path, left, top, width, height)
    except Exception as e:
        print(f"[ICONS] Warning: Failed to render icon {icon_name}: {e}")
        return None
