import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.presentation.visual_schemas import Phase3LayoutFamily, ContentDensity
from tests.held_out_corpus import HELD_OUT_TOPICS, compile_held_out_deck, _TOPIC_SLIDE_FAMILIES
from app.services.presentation.composition_renderer import render_composed_slide
from app.services.presentation.design_dna import _build_academic_clean_dna, _THEME_PALETTES
from pptx import Presentation
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT

print("CANONICAL_PHASE3_LAYOUT_FAMILY_MEMBERS:")
canonical_members = list(Phase3LayoutFamily)
for m in canonical_members:
    print(f"  {m.name} = \"{m.value}\"")

occurrences = Counter()
unique_slides = defaultdict(list)
render_success = Counter()
fallback_counts = Counter()
repair_counts = Counter()

prs = Presentation()
prs.slide_width = SLIDE_WIDTH
prs.slide_height = SLIDE_HEIGHT

for idx in range(len(HELD_OUT_TOPICS)):
    contexts, manifest, audits, repairs = compile_held_out_deck(idx)
    topic_id = HELD_OUT_TOPICS[idx]["id"]
    dna = _build_academic_clean_dna(_THEME_PALETTES["blue_professional"], ContentDensity.MEDIUM)

    for i, ctx in enumerate(contexts):
        plan = ctx.composition_plan
        fam = plan.layout_family
        occurrences[fam] += 1
        slide_id = f"T{idx+1:02d}_S{ctx.slide_no:02d}"
        unique_slides[fam].append(slide_id)

        # Requested family from topic schedule
        req_fam = _TOPIC_SLIDE_FAMILIES[idx][i]
        if fam != req_fam:
            fallback_counts[fam] += 1

        repair_res = repairs[ctx.slide_no]
        if len(repair_res.repair_actions) > 0:
            repair_counts[fam] += 1

        # Test render
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        res = render_composed_slide(prs, slide, ctx, manifest, dna, enforce_audit_gate=False)
        if res.success:
            render_success[fam] += 1

print("\nMACHINE_GENERATED_COVERAGE_TABLE:")
header = f"{'Canonical Enum Value':<30} | {'Count':<5} | {'Render Success':<14} | {'Fallbacks':<9} | {'Repairs':<7} | {'Sample Slide IDs'}"
print(header)
print("-" * 115)

total_occurrences = 0
all_exercised = True

for m in canonical_members:
    cnt = occurrences[m]
    total_occurrences += cnt
    succ = render_success[m]
    fb = fallback_counts[m]
    rep = repair_counts[m]
    samples = ", ".join(unique_slides[m][:3]) + ("..." if len(unique_slides[m]) > 3 else "")
    if cnt == 0:
        all_exercised = False
    print(f"{m.value:<30} | {cnt:<5} | {succ:<14} | {fb:<9} | {rep:<7} | {samples}")

print("-" * 115)
print(f"PRIMARY_LAYOUT_OCCURRENCE_SUM = {total_occurrences}")
print(f"ALL_20_FAMILIES_EXERCISED = {all_exercised}")
