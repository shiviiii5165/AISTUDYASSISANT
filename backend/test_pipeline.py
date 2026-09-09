import asyncio
import os
import sys

# Set path so imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.orchestrator import generate_presentation_pipeline

async def run_test():
    config = PresentationConfig(
        topic="The Evolution of TCP Congestion Control",
        slide_count=12,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
    )
    user_id = "test_user_123"

    print(f"Starting test for: {config.topic} with {config.slide_count} slides.")

    try:
        spec, pptx_bytes = await generate_presentation_pipeline(config, user_id)
        
        print("\n--- Pipeline Completed Successfully ---")
        print(f"Total Slides Generated: {len(spec.slides)}")
        
        patterns = []
        examples = []
        openers = []
        
        for idx, slide in enumerate(spec.slides):
            print(f"\n[Slide {slide.slide_no}] {slide.title}")
            print(f"  Pattern: {slide.content_pattern}")
            patterns.append(slide.content_pattern)
            
            ex = slide.example[:100].replace('\n', ' ') if slide.example else "None"
            print(f"  Example: {ex}...")
            examples.append(slide.example)
            
            if slide.body_bullets:
                first_bullet = slide.body_bullets[0]
                opener = " ".join(first_bullet.split()[:3])
                openers.append(opener)
                print(f"  Opener: {opener}...")
                
        # Simple local validation output
        print("\n--- Validation Report ---")
        consecutive_patterns = sum(1 for i in range(1, len(patterns)) if patterns[i] == patterns[i-1])
        print(f"Consecutive identical patterns: {consecutive_patterns} (should be 0)")
        
        # Check openers duplication
        duplicate_openers = len(openers) - len(set(openers))
        print(f"Duplicate first-3-word openers: {duplicate_openers} (should be 0)")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
