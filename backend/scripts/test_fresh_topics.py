import asyncio
import os
import sys
import time
from pathlib import Path
from pptx import Presentation

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.orchestrator import generate_presentation_pipeline

async def test_topic(topic: str, slide_count: int = 10):
    print(f"\n=======================================================")
    print(f"Testing Topic: {topic} (slides: {slide_count})")
    print(f"=======================================================")
    cfg = PresentationConfig(
        topic=topic,
        slide_count=slide_count,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
        theme="blue_professional",
        enable_images=False,
        enable_diagrams=True,
    )
    start_t = time.time()
    try:
        spec, pptx_bytes = await generate_presentation_pipeline(cfg, user_id="test_runner")
        elapsed = time.time() - start_t
        print(f"SUCCESS in {elapsed:.2f}s! Deck Title: '{spec.title}', Slides: {len(spec.slides)}, PPTX size: {len(pptx_bytes)} bytes")
        
        # Save PPTX to evidence dir
        out_dir = backend_dir / "evidence" / "universal_proof"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = topic.lower().replace(" ", "_").replace("-", "_") + ".pptx"
        file_path = out_dir / safe_name
        file_path.write_bytes(pptx_bytes)
        print(f"Saved to {file_path}")

        # Reopen with python-pptx
        prs = Presentation(str(file_path))
        print(f"Reopened PPTX successfully! Number of slides in PPTX: {len(prs.slides)}")
        
        # Inspect slide intents and titles
        for idx, slide in enumerate(spec.slides):
            print(f"  Slide {idx+1}: [{slide.type}] {slide.title}")
            print(f"     Key Message: {slide.key_message[:80]}...")
            print(f"     Bullets: {len(slide.body_bullets)}, Steps: {len(slide.steps)}, Cols: {len(slide.columns)}")

        return True, spec, file_path
    except Exception as e:
        elapsed = time.time() - start_t
        print(f"FAILED in {elapsed:.2f}s with error: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

if __name__ == "__main__":
    test_topic_name = sys.argv[1] if len(sys.argv) > 1 else "Binary Search Trees"
    asyncio.run(test_topic(test_topic_name))
