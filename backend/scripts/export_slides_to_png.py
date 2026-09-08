"""
PPTX to PNG Screenshot Renderer
=================================
Uses PowerPoint COM automation (win32com) to export slides as high-quality PNGs.
Renders actual PowerPoint output — not a simulation.
"""
import os
import sys
import time
import glob

def pptx_to_png(pptx_path, output_dir, width=1920):
    """Export all slides from a PPTX as PNG images using PowerPoint COM."""
    import win32com.client
    import pythoncom

    pythoncom.CoInitialize()

    pptx_abs = os.path.abspath(pptx_path)
    out_abs = os.path.abspath(output_dir)
    os.makedirs(out_abs, exist_ok=True)

    ppt_app = None
    presentation = None

    try:
        ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True  # Must be visible for COM automation

        presentation = ppt_app.Presentations.Open(pptx_abs, WithWindow=False)
        time.sleep(1)

        slide_count = presentation.Slides.Count
        print(f"  Exporting {slide_count} slides from {os.path.basename(pptx_path)}...")

        for i in range(1, slide_count + 1):
            slide = presentation.Slides(i)
            out_file = os.path.join(out_abs, f"slide_{i:02d}.png")
            slide.Export(out_file, "PNG", width, int(width * 0.5625))  # 16:9 aspect
            print(f"    Slide {i}/{slide_count} -> {os.path.basename(out_file)}")

        return slide_count

    except Exception as e:
        print(f"  [ERROR] PowerPoint export failed: {e}")
        return 0

    finally:
        if presentation:
            try:
                presentation.Close()
            except Exception:
                pass
        if ppt_app:
            try:
                ppt_app.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    artifacts_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..",
        "..", "..", "..",
        r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\312bb8e5-197c-44b6-aaf5-05368c386f19\screenshots"
    ))
    # Simpler path
    artifacts_dir = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\312bb8e5-197c-44b6-aaf5-05368c386f19\screenshots"
    os.makedirs(artifacts_dir, exist_ok=True)

    pptx_files = {
        "phase1_eyebrow_tag_test.pptx": "eyebrow_tag",
        "phase3_numbered_variants.pptx": "numbered_variants",
        "phase4_concept_split.pptx": "concept_split",
        "phase5_annotated_tiers.pptx": "annotated_tiers",
        "phase7_example_grid.pptx": "example_grid",
    }

    for pptx_name, prefix in pptx_files.items():
        pptx_path = os.path.join(base_dir, pptx_name)
        if not os.path.exists(pptx_path):
            print(f"  [SKIP] {pptx_name} not found")
            continue

        out_dir = os.path.join(artifacts_dir, prefix)
        count = pptx_to_png(pptx_path, out_dir)
        print(f"  [DONE] {pptx_name}: {count} slides exported\n")

    print(f"\nAll screenshots saved to: {artifacts_dir}")


if __name__ == "__main__":
    main()
