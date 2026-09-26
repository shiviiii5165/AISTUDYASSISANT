"""
LearnByGenie PPT vNEXT — Target Deck Regeneration & Inspection
===========================================================
Deck: 0b8744a9-b129-44f8-a85f-71d1f3b87d72.pptx
Topic: Node.js Architecture & Foundations
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from pptx import Presentation

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.presentation.schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind,
    DesignSystem
)
from app.services.presentation.content_agent import expand_presentation_content
from app.services.presentation.qa_agent import run_presentation_qa
from app.services.presentation.content_completeness_gate import audit_deck_content_completeness
from app.services.presentation.engine.builder import build_presentation_spec


async def main():
    print("[1/5] Loading cached plan and blueprints for 0b8744a9-b129-44f8-a85f-71d1f3b87d72...")
    trace_plan_path = backend_dir / "scratch" / "trace_plan.json"
    with open(trace_plan_path, "r", encoding="utf-8") as f:
        outline_data = json.load(f)

    config = PresentationConfig(
        topic="Node.js Architecture & Foundations",
        slide_count=10,
        audience="university",
        depth="full",
        design=DesignSystem.ACADEMIC_CLEAN,
        theme="blue_professional",
        enable_images=False,
        enable_diagrams=True,
    )
    user_id = "1774c162-7aa0-4162-89d3-51e0f0c1bdb3"

    print("[2/5] Running repaired Content Agent pipeline...")
    expanded_slides = await expand_presentation_content(config, user_id=user_id, outline_data=outline_data)
    print(f"      Expanded {len(expanded_slides)} slides.")

    print("[3/5] Running Structural QA Agent...")
    qa_slides = await run_presentation_qa(config, expanded_slides)
    print(f"      QA validated {len(qa_slides)} slides.")

    # Convert to PresentationSpec
    structured_slides = []
    for s in qa_slides:
        vspec_data = s.get("visual_spec") or {}
        vspec = VisualSpec(
            kind=VisualKind(vspec_data.get("kind", "none")) if isinstance(vspec_data.get("kind"), str) else VisualKind.NONE,
            asset_required=vspec_data.get("asset_required", False),
            image_prompt=vspec_data.get("image_prompt", ""),
            image_bytes=None,
        )
        slide_obj = SlideSpec(
            slide_no=s.get("slide_no", 1),
            type=s.get("type", "concept"),
            title=s.get("title", ""),
            subtitle=s.get("subtitle", ""),
            key_message=s.get("key_message", ""),
            body_bullets=s.get("body_bullets", []),
            example=s.get("example", ""),
            speaker_notes=s.get("speaker_notes", ""),
            content_pattern=s.get("content_pattern"),
            section_label=s.get("section_label"),
            visual=vspec,
            layers=s.get("layers", []),
            steps=s.get("steps", []),
            milestones=s.get("milestones", []),
            columns=s.get("columns", []),
            metrics=s.get("metrics", []),
            content=s.get("content"),
            quality_scores=s.get("quality_scores"),
            fit_risk=s.get("fit_risk"),
        )
        structured_slides.append(slide_obj)

    spec = PresentationSpec(
        title=outline_data.get("deck_title", config.topic),
        subtitle=outline_data.get("subtitle", ""),
        config=config,
        key_takeaways=outline_data.get("key_takeaways", []),
        slides=structured_slides,
        expansion_reason=outline_data.get("expansion_reason", ""),
    )

    print("[4/5] Auditing deck through Content Completeness Gate...")
    completeness_result = audit_deck_content_completeness(spec)
    print(f"      Completeness Gate Passed: {completeness_result.passed}")
    if not completeness_result.passed:
        print("      VIOLATIONS DETECTED:")
        for v in completeness_result.violations:
            print(f"      - {v}")
        raise RuntimeError(f"Completeness gate failed with {completeness_result.error_count} violations")

    print("[5/5] Rendering presentation into PPTX bytes via build_presentation_spec...")
    pptx_bytes = build_presentation_spec(spec)
    print(f"      Generated {len(pptx_bytes)} bytes of PPTX.")

    # Save to evidence and overwrite target file
    evidence_dir = backend_dir / "evidence" / "content_repair"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    repaired_evidence_path = evidence_dir / "0b8744a9-b129-44f8-a85f-71d1f3b87d72_repaired.pptx"
    repaired_evidence_path.write_bytes(pptx_bytes)
    print(f"      Saved evidence to: {repaired_evidence_path}")

    target_pptx_path = Path("E:/0b8744a9-b129-44f8-a85f-71d1f3b87d72.pptx")
    target_pptx_path.write_bytes(pptx_bytes)
    print(f"      Overwrote target at: {target_pptx_path}")

    # Inspect the saved PPTX
    import hashlib
    print("\n" + "="*80)
    print("INSPECTING SAVED REGENERATED PPTX")
    print("="*80)
    prs = Presentation(str(repaired_evidence_path))
    inspection_records = []
    for s_idx, slide in enumerate(prs.slides):
        slide_num = s_idx + 1
        spec_slide = structured_slides[s_idx] if s_idx < len(structured_slides) else None

        slide_texts = []
        slide_tables = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    txt = p.text.strip()
                    if txt:
                        slide_texts.append(txt)
            if shape.has_table:
                tbl_data = []
                for row in shape.table.rows:
                    row_cells = [c.text.strip() for c in row.cells]
                    tbl_data.append(row_cells)
                slide_tables.append(tbl_data)

        notes_text = ""
        if slide.has_notes_slide:
            notes_tf = slide.notes_slide.notes_text_frame
            if notes_tf:
                notes_text = notes_tf.text.strip()

        # Extract semantic fields
        slide_title = slide_texts[0] if slide_texts else (spec_slide.title if spec_slide else "")
        body_content = slide_texts[1:] if len(slide_texts) > 1 else []

        semantic_bindings = {
            "slide_no": slide_num,
            "type": spec_slide.type if spec_slide else "concept",
            "content_pattern": spec_slide.content_pattern if spec_slide else None,
            "key_message": spec_slide.key_message if spec_slide else "",
            "columns_count": len(spec_slide.columns) if spec_slide and spec_slide.columns else 0,
            "steps_count": len(spec_slide.steps) if spec_slide and spec_slide.steps else 0,
            "layers_count": len(spec_slide.layers) if spec_slide and spec_slide.layers else 0,
        }

        content_fingerprint = json.dumps({
            "title": slide_title,
            "body": body_content,
            "tables": slide_tables,
            "notes": notes_text,
        }, sort_keys=True)
        content_hash = hashlib.sha256(content_fingerprint.encode("utf-8")).hexdigest()

        print(f"\n--- Slide {slide_num}: {slide_title[:50]} ---")
        print(f"  Content Hash: {content_hash[:16]}...")
        print(f"  Body Elements: {len(body_content)}")
        print(f"  Tables Count: {len(slide_tables)}")
        if slide_tables:
            for t_idx, t in enumerate(slide_tables):
                print(f"    Table {t_idx+1} ({len(t)} rows x {len(t[0]) if t else 0} cols)")
                for r_idx, r in enumerate(t):
                    safe_r = [c[:40].encode('ascii', 'replace').decode() for c in r]
                    print(f"      Row {r_idx+1}: {safe_r}")
        print(f"  Notes Length: {len(notes_text.split())} words")

        inspection_records.append({
            "slide_number": slide_num,
            "title": slide_title,
            "body_content": body_content,
            "tables": slide_tables,
            "speaker_notes": notes_text,
            "semantic_bindings": semantic_bindings,
            "content_hash": content_hash,
        })

    inspection_path = backend_dir / "scratch" / "repaired_deck_inspection.json"
    with open(inspection_path, "w", encoding="utf-8") as f:
        json.dump(inspection_records, f, indent=2, ensure_ascii=False)
    print(f"\nInspection written to {inspection_path}")


if __name__ == "__main__":
    asyncio.run(main())
