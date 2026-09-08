"""
Phase 1 Verification: Eyebrow Tag renders correctly across all templates.
Generates a small test deck with section_labels to visually confirm the
eyebrow tag pill appears above slide titles.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme

# Import all 5 template renderers
from app.services.presentation.engine.templates.academic import render_academic_slide
from app.services.presentation.engine.templates.minimal import render_minimal_slide
from app.services.presentation.engine.templates.technical import render_technical_slide
from app.services.presentation.engine.templates.editorial import render_editorial_slide
from app.services.presentation.engine.templates.visual_learning import render_visual_learning_slide

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "scratch", "phase1_eyebrow_tag_test.pptx")

def main():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    theme = get_theme("blue_professional")
    renderers = [
        ("Academic", render_academic_slide),
        ("Minimal", render_minimal_slide),
        ("Technical", render_technical_slide),
        ("Editorial", render_editorial_slide),
        ("Visual Learning", render_visual_learning_slide),
    ]

    total_slides = len(renderers) * 3  # 3 slides per template

    slide_idx = 0
    for template_name, render_func in renderers:
        # Slide A: with section_label
        slide_idx += 1
        slide_spec_with_label = {
            "type": "concept",
            "title": f"Supervised Learning: Core Mechanisms & Training Pipeline",
            "key_message": "Supervised learning maps labeled input-output pairs through iterative gradient descent optimization.",
            "body_bullets": [
                "Training data consists of feature vectors paired with ground-truth labels",
                "Loss function measures prediction error — MSE for regression, cross-entropy for classification",
                "Gradient descent iteratively adjusts weights to minimize loss across mini-batches",
                "Overfitting controlled via regularization (L1/L2), dropout, and early stopping",
            ],
            "example": "Google's BERT model trained on 3.3B words using masked language modeling — 97.1% accuracy on MNLI.",
            "speaker_notes": "Walk through the training loop step by step.",
            "section_label": "TYPE 1",
        }
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        render_func(slide=slide, slide_spec=slide_spec_with_label, theme=theme,
                    slide_number=slide_idx, total_slides=total_slides, deck_title="ML Types Test")

        # Slide B: with different section_label
        slide_idx += 1
        slide_spec_apps = {
            "type": "concept",
            "title": "Real-World Applications of Supervised Learning",
            "key_message": "Supervised learning powers medical imaging, fraud detection, and NLP at production scale.",
            "body_bullets": [
                "Medical Diagnosis: CNN detects diabetic retinopathy with 97.5% sensitivity (Google Health, 2019)",
                "Fraud Detection: Random forests flag $21B in fraudulent transactions annually (Visa/Mastercard)",
                "Natural Language Processing: GPT-4 scores 90th percentile on the bar exam",
            ],
            "example": "",
            "speaker_notes": "",
            "section_label": "TYPE 1 — APPLICATIONS",
        }
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        render_func(slide=slide, slide_spec=slide_spec_apps, theme=theme,
                    slide_number=slide_idx, total_slides=total_slides, deck_title="ML Types Test")

        # Slide C: WITHOUT section_label (should NOT show eyebrow tag)
        slide_idx += 1
        slide_spec_no_label = {
            "type": "concept",
            "title": "Key Takeaways & Summary",
            "key_message": "Three types of machine learning address different problem structures.",
            "body_bullets": [
                "Supervised: labeled data, prediction tasks",
                "Unsupervised: unlabeled data, pattern discovery",
                "Reinforcement: agent-environment interaction, reward maximization",
            ],
            "example": "",
            "speaker_notes": "",
            # No section_label — eyebrow tag should NOT appear
        }
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        render_func(slide=slide, slide_spec=slide_spec_no_label, theme=theme,
                    slide_number=slide_idx, total_slides=total_slides, deck_title="ML Types Test")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    prs.save(OUTPUT_PATH)
    print(f"[SUCCESS] Phase 1 test deck saved to: {OUTPUT_PATH}")
    print(f"  Total slides: {len(prs.slides)} (5 templates x 3 slides)")
    print(f"  Slides WITH eyebrow tag: 10 (2 per template)")
    print(f"  Slides WITHOUT eyebrow tag: 5 (1 per template)")

if __name__ == "__main__":
    main()
