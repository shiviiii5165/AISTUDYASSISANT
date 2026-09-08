"""Phase 7 verification: example_grid + topic_icons render test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation_engine import SlideContent
from app.services.presentation_engine.renderers.example_grid import render_example_grid
from app.services.presentation_engine.renderers.topic_icons import resolve_topic_icon

prs = Presentation()
prs.slide_width = SLIDE_WIDTH
prs.slide_height = SLIDE_HEIGHT
theme = get_theme("blue_professional")

# Slide 1: 4 items (2x2 grid) - ML applications
c1 = SlideContent(
    title="Real-World Applications of Machine Learning",
    body_bullets=[
        "Medical Diagnosis: Deep learning detects diabetic retinopathy with 97.5% sensitivity",
        "Fraud Detection: Visa AI screens 500M+ daily transactions preventing $25B annual fraud",
        "Autonomous Vehicles: Tesla Autopilot processes 2300 frames/sec from 8 cameras",
        "Natural Language: GPT-4 scores 90th percentile on the bar exam",
    ],
)
s1 = prs.slides.add_slide(prs.slide_layouts[6])
render_example_grid(s1, c1, theme, slide_number=1, total_slides=2)

# Slide 2: cross-domain
c2 = SlideContent(
    title="Applications Across Industries",
    body_bullets=[
        "Agriculture: Precision farming drones analyze crop health via multispectral imaging",
        "Finance: Algorithmic trading handles 70% of US equity volume",
        "Manufacturing: Predictive maintenance reduces downtime by 50% at Siemens",
        "Education: Adaptive learning platforms personalize curricula for 100M+ students",
    ],
)
s2 = prs.slides.add_slide(prs.slide_layouts[6])
render_example_grid(s2, c2, theme, slide_number=2, total_slides=2)

os.makedirs(os.path.join(os.path.dirname(__file__), "..", "scratch"), exist_ok=True)
out = os.path.join(os.path.dirname(__file__), "..", "scratch", "phase7_example_grid.pptx")
prs.save(out)
print(f"[SUCCESS] Phase 7 test deck saved: {out}")
print("  Slide 1: ML applications (4 items, 2x2 grid)")
print("  Slide 2: Cross-domain examples (4 items, 2x2 grid)")

# Test icon resolution
test_cases = [
    "Medical Diagnosis with deep learning",
    "Financial fraud detection systems",
    "Autonomous vehicle navigation",
    "Agricultural crop monitoring",
    "Some obscure unmatched term xyz123",
]
print()
for t in test_cases:
    result = resolve_topic_icon(t)
    status = os.path.basename(result) if result else "None (fallback to stock photo)"
    print(f'  Icon for "{t[:40]}...": {status}')
