import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.brief_builder import build_presentation_brief
from app.services.presentation.topic_ontology_agent import generate_topic_intelligence
from app.services.presentation.planner_agent import plan_presentation_vnext
from app.services.presentation.content_agent import expand_presentation_content
from app.services.presentation.qa_agent import run_presentation_qa

async def main():
    cfg = PresentationConfig(
        topic="Conditional Probability",
        slide_count=10,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
    )
    brief = build_presentation_brief(cfg)
    topic_intel = await generate_topic_intelligence(cfg, user_id="test")
    outline = await plan_presentation_vnext(brief, topic_intelligence=topic_intel, user_id="test")
    slides = await expand_presentation_content(cfg, user_id="test", outline_data=outline)
    print("--- SLIDES AFTER EXPAND_PRESENTATION_CONTENT ---")
    for idx, s in enumerate(slides):
        print(f"Slide {idx+1}: type={s.get('type')} title={s.get('title')}")
        print(f"  steps={s.get('steps')}")
        print(f"  content.process_steps={s.get('content', {}).get('process_steps') if isinstance(s.get('content'), dict) else []}")

    qa_slides = await run_presentation_qa(cfg, slides)
    print("\n--- SLIDES AFTER RUN_PRESENTATION_QA ---")
    for idx, s in enumerate(qa_slides):
        print(f"Slide {idx+1}: type={s.get('type')} title={s.get('title')}")
        print(f"  steps={s.get('steps')}")
        print(f"  content.process_steps={s.get('content', {}).get('process_steps') if isinstance(s.get('content'), dict) else []}")

if __name__ == "__main__":
    asyncio.run(main())
