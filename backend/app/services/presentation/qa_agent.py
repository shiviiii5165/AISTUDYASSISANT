"""
QA Agent & Slide-Level Repair Loop
==================================
1. Python Structural QA (Zero Token Cost): Checks bounds, word counts, bullet counts, slide count.
2. Targeted AI Patch Loop: If a single slide is defective, patches only that specific slide.
"""
from app.core.logging import logger
import json
from typing import List, Dict, Any, Tuple
from app.services.ai import router
from .schemas import PresentationConfig
from .prompts import SLIDE_PATCH_SYSTEM_PROMPT


def inspect_slide_structure(slide: Dict[str, Any]) -> List[str]:
    """Pure Python validation of slide bounds and density (0 tokens)."""
    issues = []
    bullets = slide.get("body_bullets", [])
    title = slide.get("title", "")
    
    if not title.strip():
        issues.append("Title is empty.")
    elif len(title) > 90:
        issues.append(f"Title is too long ({len(title)} chars). Max 80 chars.")

    if len(bullets) > 6:
        issues.append(f"Too many bullets ({len(bullets)}). Recommended max 5.")

    for i, b in enumerate(bullets):
        if len(str(b)) > 110:
            issues.append(f"Bullet {i+1} is too long ({len(str(b))} chars). Max 80-90 chars.")

    # Total word count across slide
    all_words = " ".join([
        title,
        " ".join(str(x) for x in bullets),
        slide.get("example", ""),
        slide.get("key_message", ""),
    ]).split()

    if len(all_words) > 180:
        issues.append(f"Slide word count is high ({len(all_words)} words). Move details to speaker_notes.")

    return issues


def auto_heal_slide_python(slide: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic Python cleanup without invoking LLM (0 tokens)."""
    # 1. Truncate excess bullets to max 5 and move overflow to speaker notes
    bullets = slide.get("body_bullets", [])
    if len(bullets) > 5:
        excess = bullets[5:]
        slide["body_bullets"] = bullets[:5]
        extra_note = "\n\nAdditional points:\n" + "\n".join(f"• {b}" for b in excess)
        slide["speaker_notes"] = (slide.get("speaker_notes", "") + extra_note).strip()

    # 2. Trim bullet length if slightly over
    trimmed_bullets = []
    for b in slide.get("body_bullets", []):
        b_str = str(b).strip()
        if len(b_str) > 90:
            cut = b_str[:85]
            last_sp = cut.rfind(" ")
            if last_sp > 50:
                cut = cut[:last_sp]
            trimmed_bullets.append(cut + "...")
        else:
            trimmed_bullets.append(b_str)
    slide["body_bullets"] = trimmed_bullets

    # 3. Trim title if overly long
    title = slide.get("title", "")
    if len(title) > 80:
        cut_title = title[:75]
        last_sp = cut_title.rfind(" ")
        if last_sp > 40:
            cut_title = cut_title[:last_sp]
        slide["title"] = cut_title

    return slide


async def run_presentation_qa(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Executes Python structural QA, auto-heals overflow, and performs targeted AI repair
    if a slide has major semantic issues.
    """
    # 1. Enforce exact slide count assertion
    if len(slides) != config.slide_count:
        if len(slides) > config.slide_count:
            slides = slides[:config.slide_count]
        else:
            while len(slides) < config.slide_count:
                num = len(slides) + 1
                slides.append({
                    "slide_no": num,
                    "type": "concept",
                    "title": f"Summary & Key Takeaway {num}",
                    "key_message": "Core takeaway summary point.",
                    "body_bullets": ["Key educational insight", "Synthesized understanding"],
                    "speaker_notes": "Key takeaway context.",
                })

    # 2. Run Python QA & Auto-Healing on each slide
    repaired_slides = []
    for s in slides:
        healed = auto_heal_slide_python(s)
        issues = inspect_slide_structure(healed)

        # 3. If major unresolved issues remain, invoke targeted single-slide AI repair
        if len(issues) >= 3:
            try:
                patch_res = await router.generate_json(
                    task="repair",
                    messages=[
                        {"role": "system", "content": SLIDE_PATCH_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Fix issues in this slide:\nSlide Content:\n{json.dumps(healed, indent=2)}\n\nIssues:\n" + "\n".join(issues)},
                    ],
                    temperature=0.2,
                    max_tokens=2000,
                )
                if patch_res and patch_res.get("title"):
                    # Preserve original visual_spec
                    patch_res["visual_spec"] = healed.get("visual_spec")
                    patch_res["slide_no"] = healed.get("slide_no")
                    healed = auto_heal_slide_python(patch_res)
            except Exception as e:
                logger.error(f"[QA Agent] AI slide patch failed for slide {s.get('slide_no')}: {e}")

        repaired_slides.append(healed)

    return repaired_slides
