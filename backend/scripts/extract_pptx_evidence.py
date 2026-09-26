import json
import os
import sys
from pathlib import Path
from pptx import Presentation

backend_dir = Path(__file__).resolve().parent.parent
evidence_dir = backend_dir / "evidence" / "universal_proof"

topics = [
    "quantum_entanglement.pptx",
    "human_kidney_function.pptx",
    "binary_search_trees.pptx",
    "break_even_analysis.pptx",
    "ancient_egyptian_civilization.pptx",
    "conditional_probability.pptx",
    "principles_of_contract_law.pptx",
    "soil_erosion.pptx"
]

results = {}

for filename in topics:
    pptx_path = evidence_dir / filename
    if not pptx_path.exists():
        print(f"File not found: {pptx_path}")
        continue
    
    prs = Presentation(str(pptx_path))
    deck_data = {
        "filename": filename,
        "file_size_bytes": pptx_path.stat().st_size,
        "slide_count": len(prs.slides),
        "slides": []
    }
    
    for s_idx, slide in enumerate(prs.slides):
        slide_info = {
            "slide_no": s_idx + 1,
            "texts": [],
            "tables": [],
            "notes": ""
        }
        
        # Extract shapes
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    txt = paragraph.text.strip()
                    if txt:
                        slide_info["texts"].append(txt)
            if shape.has_table:
                table_data = []
                for row in shape.table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                slide_info["tables"].append(table_data)
                
        # Extract notes
        if slide.has_notes_slide:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()
            slide_info["notes"] = notes_text
            
        deck_data["slides"].append(slide_info)
        
    results[filename] = deck_data
    print(f"Extracted {filename}: {len(deck_data['slides'])} slides, size={deck_data['file_size_bytes']} bytes")

out_json = evidence_dir / "extracted_pptx_evidence.json"
out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nWrote full extracted evidence to {out_json}")
