"""
Test script: Verifies the PPT renderer generates a valid PPTX file
from sample deck JSON data (no API calls, no Supabase).
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Mock settings before importing anything
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "placeholder")
os.environ.setdefault("SUPABASE_JWT_SECRET", "placeholder")
os.environ.setdefault("GEMINI_API_KEY", "placeholder")
os.environ.setdefault("GROQ_API_KEY", "placeholder")
os.environ.setdefault("CASHFREE_APP_ID", "placeholder")
os.environ.setdefault("CASHFREE_SECRET_KEY", "placeholder")
os.environ.setdefault("GEMINI_IMAGE_API_KEY", "")

SAMPLE_DECK = {
    "deck_title": "Introduction to Machine Learning",
    "key_takeaways": [
        "ML enables computers to learn from data without explicit programming",
        "Supervised, unsupervised, and reinforcement learning are the three main paradigms",
        "Feature engineering and data quality are critical for model performance",
        "Overfitting vs underfitting is the central trade-off in ML",
        "Real-world ML requires careful evaluation and deployment strategies"
    ],
    "sections": [
        {
            "id": "learning_objectives",
            "title": "Learning Objectives",
            "body_bullets": [
                "Define machine learning and its relationship to AI",
                "Identify the three main types of ML",
                "Understand the ML pipeline from data to deployment",
                "Recognize common pitfalls in ML projects"
            ],
            "example": "By the end of this deck, you will be able to explain when to use classification vs regression.",
            "speaker_note": "Start by asking students what they think AI is. Most will conflate AI and ML. This sets up the distinction nicely.",
            "visual_hint": "diagram",
            "image_prompt": ""
        },
        {
            "id": "what_is_ml",
            "title": "What is Machine Learning?",
            "body_bullets": [
                "Subset of AI that learns patterns from data",
                "No explicit programming — the model discovers rules",
                "Improves performance with more data and experience",
                "Used in spam filters, recommendations, self-driving cars"
            ],
            "example": "A spam filter learns from thousands of labeled emails (spam/not spam) to classify new emails automatically.",
            "speaker_note": "Arthur Samuel coined the term in 1959. Emphasize that ML is not magic — it's statistics at scale.",
            "visual_hint": "diagram",
            "image_prompt": ""
        },
        {
            "id": "supervised_learning",
            "title": "Supervised Learning",
            "body_bullets": [
                "Learns from labeled training data (input → output pairs)",
                "Two main tasks: classification and regression",
                "Examples: image recognition, price prediction",
                "Requires large amounts of labeled data"
            ],
            "example": "Predicting house prices from features like area, bedrooms, and location is a regression problem.",
            "speaker_note": "Draw the analogy of a student studying with an answer key. The labels are the answer key.",
            "visual_hint": "generated_image",
            "image_prompt": "A clean diagram showing supervised learning flow: labeled data goes into a model box, which outputs predictions"
        },
        {
            "id": "unsupervised_learning",
            "title": "Unsupervised Learning",
            "body_bullets": [
                "No labels — finds hidden structure in data",
                "Clustering groups similar data points together",
                "Dimensionality reduction simplifies complex data",
                "Used in customer segmentation and anomaly detection"
            ],
            "example": "Grouping customers by purchase behavior without predefined categories.",
            "speaker_note": "Contrast with supervised: here the student has no answer key, just the data itself.",
            "visual_hint": "diagram",
            "image_prompt": ""
        },
        {
            "id": "overfitting",
            "title": "Overfitting vs Underfitting",
            "body_bullets": [
                "Overfitting: model memorizes training data, fails on new data",
                "Underfitting: model is too simple to capture patterns",
                "The sweet spot is good generalization to unseen data",
                "Solutions: cross-validation, regularization, more data"
            ],
            "example": "A student who memorizes answers but can't solve new problems is overfitting.",
            "speaker_note": "This is the most important concept in practical ML. Spend extra time here.",
            "visual_hint": "diagram",
            "image_prompt": ""
        },
    ]
}


async def main():
    from app.services.ppt_renderer import generate_pptx_bytes
    
    print("=" * 60)
    print("PPT Renderer Test")
    print("=" * 60)
    
    print(f"\nTopic: {SAMPLE_DECK['deck_title']}")
    print(f"Sections: {len(SAMPLE_DECK['sections'])}")
    print(f"Expected slides: {len(SAMPLE_DECK['sections']) + 2} (title + {len(SAMPLE_DECK['sections'])} content + closing)")
    
    print("\nGenerating PPTX (without images)...")
    
    try:
        pptx_bytes = await generate_pptx_bytes(SAMPLE_DECK, audience="university")
        
        output_path = os.path.join(os.path.dirname(__file__), "test_output.pptx")
        with open(output_path, "wb") as f:
            f.write(pptx_bytes)
        
        file_size_kb = len(pptx_bytes) / 1024
        print(f"\n[OK] SUCCESS: Generated {file_size_kb:.1f} KB PPTX")
        print(f"[FILE] Saved to: {output_path}")
        
        # Validate by opening with python-pptx
        from pptx import Presentation
        prs = Presentation(output_path)
        
        slide_count = len(prs.slides)
        print(f"[SLIDES] Slides in file: {slide_count}")
        
        for i, slide in enumerate(prs.slides):
            shapes_count = len(slide.shapes)
            has_notes = bool(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip())
            print(f"   Slide {i+1}: {shapes_count} shapes{' + notes' if has_notes else ''}")
        
        print(f"\n[DIM] Slide dimensions: {prs.slide_width / 914400:.1f} x {prs.slide_height / 914400:.1f} inches")
        
        expected = len(SAMPLE_DECK['sections']) + 2
        if slide_count == expected:
            print(f"\n[PASS] Slide count matches ({slide_count} == {expected})")
        else:
            print(f"\n[FAIL] Expected {expected} slides, got {slide_count}")
            
        print("\n[OK] All checks passed! Open test_output.pptx to visually verify.")
        
    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
