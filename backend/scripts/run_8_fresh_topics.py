import asyncio
import os
import sys
import time
import json
from pathlib import Path
from pptx import Presentation

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.orchestrator import generate_presentation_pipeline

TOPICS = [
    {"topic": "Quantum Entanglement", "discipline": "Physics", "expected_pattern": "mechanisms / non-locality / bell's theorem"},
    {"topic": "Human Kidney Function", "discipline": "Physiology", "expected_pattern": "nephron process / filtration / reabsorption"},
    {"topic": "Binary Search Trees", "discipline": "Computer Science", "expected_pattern": "tree topology / traversal / balancing"},
    {"topic": "Ancient Egyptian Civilization", "discipline": "History", "expected_pattern": "chronology / nile / kingdom periods"},
    {"topic": "Break-Even Analysis", "discipline": "Business / Finance", "expected_pattern": "fixed/variable costs / margin / volume"},
    {"topic": "Conditional Probability", "discipline": "Mathematics", "expected_pattern": "bayes / sample space / independence"},
    {"topic": "Principles of Contract Law", "discipline": "Law", "expected_pattern": "offer / acceptance / consideration / breach"},
    {"topic": "Soil Erosion", "discipline": "Environmental Science", "expected_pattern": "wind/water mechanics / degradation / conservation"},
]

async def run_single_topic(t_info: dict, out_dir: Path):
    topic = t_info["topic"]
    discipline = t_info["discipline"]
    print(f"\n=====================================================================")
    print(f"STARTING PRODUCTION GENERATION: {topic} ({discipline})")
    print(f"=====================================================================")
    
    cfg = PresentationConfig(
        topic=topic,
        slide_count=10,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
        theme="blue_professional",
        enable_images=False,
        enable_diagrams=True,
    )
    
    start_t = time.time()
    try:
        spec, pptx_bytes = await generate_presentation_pipeline(cfg, user_id="universal_engine_test")
        elapsed = time.time() - start_t
        
        safe_name = topic.lower().replace(" ", "_").replace("-", "_") + ".pptx"
        file_path = out_dir / safe_name
        file_path.write_bytes(pptx_bytes)
        
        # Re-open with python-pptx
        prs = Presentation(str(file_path))
        slide_count_pptx = len(prs.slides)
        
        # Analyze structure and intents
        intents = [s.type.value if hasattr(s.type, "value") else str(s.type) for s in spec.slides]
        unique_intents = list(dict.fromkeys(intents))
        
        # Extract slide details
        slides_detail = []
        for idx, slide in enumerate(spec.slides):
            slides_detail.append({
                "slide_no": idx + 1,
                "type": slide.type.value if hasattr(slide.type, "value") else str(slide.type),
                "title": slide.title,
                "key_message": slide.key_message,
                "bullets_count": len(slide.body_bullets),
                "steps_count": len(slide.steps),
                "columns_count": len(slide.columns),
                "notes_word_count": len(slide.speaker_notes.split()) if slide.speaker_notes else 0,
            })
            
        print(f"SUCCESS: '{topic}' in {elapsed:.1f}s | Slides: {slide_count_pptx} | PPTX Size: {len(pptx_bytes)} bytes")
        print(f"  Intents: {intents}")
        
        return {
            "topic": topic,
            "discipline": discipline,
            "status": "PASS",
            "elapsed_seconds": round(elapsed, 2),
            "file_path": str(file_path),
            "pptx_bytes": len(pptx_bytes),
            "slide_count": slide_count_pptx,
            "intents": intents,
            "unique_intents": unique_intents,
            "slides_detail": slides_detail,
        }
    except Exception as e:
        elapsed = time.time() - start_t
        print(f"FAILED: '{topic}' in {elapsed:.1f}s with error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "topic": topic,
            "discipline": discipline,
            "status": "FAIL",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e),
        }

async def main():
    out_dir = backend_dir / "evidence" / "universal_proof"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    for t_info in TOPICS:
        res = await run_single_topic(t_info, out_dir)
        results.append(res)
        # Write incremental report
        report_file = out_dir / "fresh_topics_summary.json"
        report_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
        
    print("\n=====================================================================")
    print("FINAL SUMMARY REPORT")
    print("=====================================================================")
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"Total Topics: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}")
    for r in results:
        status_icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{status_icon}] {r['topic']} ({r['discipline']}) - {r.get('elapsed_seconds', 0)}s")

if __name__ == "__main__":
    asyncio.run(main())
