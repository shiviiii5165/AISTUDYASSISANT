"""
Non-ML Verification Deck Generator
=====================================
Generates two full decks for non-ML topics to verify that the new components
work correctly across topic domains:

1. "The French Revolution" (history/political science)
2. "Cellular Respiration" (biology/biochemistry)

Each deck exercises: eyebrow tags, concept_split, annotated_tiers, example_grid,
numbered_process (both variants), and definition_box patterns.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation_engine import SlideContent, ProcessStep, ComparisonColumn
from app.services.presentation_engine.renderers.eyebrow_tag import render_eyebrow_tag

# Import renderers
from app.services.presentation.engine.templates.academic import render_academic_slide
from app.services.presentation.engine.templates.editorial import render_editorial_slide
from app.services.presentation_engine.renderers.concept_split import render_concept_split
from app.services.presentation_engine.renderers.annotated_tiers import render_annotated_tiers
from app.services.presentation_engine.renderers.example_grid import render_example_grid
from app.services.presentation_engine.renderers.numbered_process import render_numbered_process
from app.services.presentation_engine.renderers.definition_box import render_definition_box
from app.services.presentation_engine.renderers.contrast_pair import render_contrast_pair

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "scratch")


def generate_french_revolution_deck():
    """Generate 'The French Revolution' verification deck."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    theme = get_theme("editorial_warm")
    total = 8

    # Slide 1: Hero slide (academic template with section_label)
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    render_academic_slide(
        slide=s1,
        slide_spec={
            "type": "hero",
            "title": "The French Revolution",
            "subtitle": "Liberty, Equality, and the Birth of Modern Democracy (1789-1799)",
            "key_message": "",
            "body_bullets": [],
        },
        theme=theme, slide_number=1, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 2: Definition slide with eyebrow tag "CHAPTER OVERVIEW"
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    render_editorial_slide(
        slide=s2,
        slide_spec={
            "type": "concept",
            "title": "What Was the French Revolution?",
            "section_label": "CHAPTER OVERVIEW",
            "key_message": "A decade-long upheaval that dismantled absolute monarchy and reshaped European political order.",
            "body_bullets": [
                "Absolute monarchy under Louis XVI collapsed under fiscal crisis and Enlightenment ideals",
                "Estates-General convened May 1789 — first time since 1614, exposing deep class divisions",
                "Declaration of the Rights of Man (Aug 1789) established universal rights as constitutional law",
                "Revolutionary period 1789-1799 produced 5 distinct governments before Napoleon's coup",
            ],
            "example": "The storming of the Bastille on July 14, 1789 — a medieval fortress-prison holding only 7 prisoners — became the enduring symbol of popular revolt against tyranny.",
        },
        theme=theme, slide_number=2, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 3: Annotated Tiers — Social Hierarchy (3 tiers = pyramid)
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    render_annotated_tiers(
        slide=s3,
        content=SlideContent(
            title="The Three Estates: France's Rigid Social Hierarchy",
            steps=[
                ProcessStep(number=1, title="First Estate: Clergy",
                           detail="~130,000 people (0.5%) — owned 10% of land, paid no taxes, controlled education"),
                ProcessStep(number=2, title="Second Estate: Nobility",
                           detail="~350,000 people (1.5%) — held military/judicial posts, exempt from most taxes"),
                ProcessStep(number=3, title="Third Estate: Everyone Else",
                           detail="~27 million (98%) — bourgeoisie, peasants, urban workers — bore full tax burden"),
            ],
        ),
        theme=theme, slide_number=3, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 4: Numbered Process — Key Events Timeline
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    render_numbered_process(
        slide=s4,
        content=SlideContent(
            title="Cascade of Revolutionary Events (1789-1793)",
            steps=[
                ProcessStep(number=1, title="Estates-General", detail="May 5, 1789 — Convened at Versailles; Third Estate demands doubled representation"),
                ProcessStep(number=2, title="Tennis Court Oath", detail="June 20, 1789 — National Assembly vows to draft constitution; defies royal authority"),
                ProcessStep(number=3, title="Storming of Bastille", detail="July 14, 1789 — Paris mob seizes fortress; monarchy's military grip shattered"),
                ProcessStep(number=4, title="Reign of Terror", detail="Sept 1793 - July 1794 — Committee of Public Safety executes 16,594 by guillotine"),
            ],
        ),
        theme=theme, slide_number=4, total_slides=total, deck_title="The French Revolution",
        prefer_thin_rule=True,  # Editorial theme = thin rule variant
    )

    # Slide 5: Concept Split — Robespierre (with fake image)
    from PIL import Image
    import io
    img = Image.new("RGB", (400, 300), color=(120, 80, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    fake_img = buf.getvalue()

    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    render_concept_split(
        slide=s5,
        content=SlideContent(
            title="Maximilien Robespierre: Architect of the Terror",
            key_insight="A provincial lawyer who became the Revolution's most powerful — and feared — figure, Robespierre weaponized virtue as justification for systematic political violence.",
            body_bullets=[
                "Committee of Public Safety: Directed France's war effort and internal purges from April 1793",
                "The Incorruptible: Lived ascetically in a carpenter's house while ordering thousands of executions",
                "Thermidorian Reaction: Arrested and guillotined July 28, 1794 — ending the Terror he created",
            ],
            image_bytes=fake_img,
        ),
        theme=theme, slide_number=5, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 6: Example Grid — Legacy/Impact across domains
    s6 = prs.slides.add_slide(prs.slide_layouts[6])
    render_example_grid(
        slide=s6,
        content=SlideContent(
            title="Applications & Legacy of Revolutionary Ideas",
            body_bullets=[
                "Law: Napoleonic Code (1804) — codified civil law in 36 countries, still in force in Louisiana and Quebec",
                "Government: Constitutional democracy replaced divine-right monarchy across Europe within 100 years",
                "Education: State-run secular schools replaced Church monopoly — model adopted globally",
                "Art: Romanticism movement (Delacroix's 'Liberty Leading the People') defined revolutionary visual culture",
            ],
        ),
        theme=theme, slide_number=6, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 7: Content slide with eyebrow "KEY DEBATE"
    s7 = prs.slides.add_slide(prs.slide_layouts[6])
    render_editorial_slide(
        slide=s7,
        slide_spec={
            "type": "concept",
            "title": "Was the Terror Justified?",
            "section_label": "KEY DEBATE",
            "key_message": "Historians remain divided: emergency measure saving the Republic, or totalitarian blueprint.",
            "body_bullets": [
                "Jacobin Defense: External wars (Austria, Prussia, Britain) + internal counter-revolution demanded extreme measures",
                "Liberal Critique: 16,594 executions violated the very rights the Revolution proclaimed",
                "Marxist Analysis: Class warfare by bourgeoisie against both aristocracy and emerging proletariat",
                "Modern Consensus: Terror radicalized by institutional momentum, not just ideology (Furet, 1981)",
            ],
        },
        theme=theme, slide_number=7, total_slides=total, deck_title="The French Revolution"
    )

    # Slide 8: Closing
    s8 = prs.slides.add_slide(prs.slide_layouts[6])
    render_editorial_slide(
        slide=s8,
        slide_spec={
            "type": "qa",
            "title": "Questions & Discussion",
            "key_message": "",
            "body_bullets": [
                "How do the ideals of 1789 compare to modern democratic movements?",
                "Was revolutionary violence a necessary cost of systemic change?",
            ],
        },
        theme=theme, slide_number=8, total_slides=total, deck_title="The French Revolution"
    )

    out = os.path.join(OUTPUT_DIR, "verification_french_revolution.pptx")
    prs.save(out)
    print(f"[SUCCESS] French Revolution deck: {out} ({len(prs.slides)} slides)")
    return out


def generate_cellular_respiration_deck():
    """Generate 'Cellular Respiration' verification deck."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    theme = get_theme("blue_professional")
    total = 8

    # Slide 1: Hero
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    render_academic_slide(
        slide=s1,
        slide_spec={
            "type": "hero",
            "title": "Cellular Respiration",
            "subtitle": "How Cells Convert Glucose to ATP — The Universal Energy Currency",
            "key_message": "",
            "body_bullets": [],
        },
        theme=theme, slide_number=1, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 2: Definition with eyebrow "CORE CONCEPT"
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    render_academic_slide(
        slide=s2,
        slide_spec={
            "type": "concept",
            "title": "What is Cellular Respiration?",
            "section_label": "CORE CONCEPT",
            "key_message": "C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + ~36-38 ATP — the complete oxidation of glucose.",
            "body_bullets": [
                "Exergonic process releasing ~2,870 kJ/mol of glucose — captured stepwise, not all at once",
                "Occurs in all living cells — mitochondria are the primary site in eukaryotes",
                "Three stages: Glycolysis (cytoplasm) → Krebs Cycle (matrix) → ETC (inner membrane)",
                "Net yield: 36-38 ATP per glucose molecule (theoretical max; actual ~30-32 in vivo)",
            ],
            "example": "A human at rest consumes ~250 mL O₂/min and produces ~200 mL CO₂/min, turning over ~40 kg of ATP daily — roughly equal to body weight.",
        },
        theme=theme, slide_number=2, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 3: Numbered Process — Three Stages
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    render_numbered_process(
        slide=s3,
        content=SlideContent(
            title="Three Stages of Cellular Respiration",
            steps=[
                ProcessStep(number=1, title="Glycolysis",
                           detail="Cytoplasm: Glucose → 2 pyruvate. Yields 2 ATP + 2 NADH. No O₂ required (anaerobic)."),
                ProcessStep(number=2, title="Krebs Cycle",
                           detail="Mitochondrial matrix: Acetyl-CoA → CO₂. Yields 2 ATP + 6 NADH + 2 FADH₂ per glucose."),
                ProcessStep(number=3, title="Electron Transport Chain",
                           detail="Inner membrane: NADH/FADH₂ → O₂. Yields 32-34 ATP via chemiosmosis (ATP synthase)."),
            ],
        ),
        theme=theme, slide_number=3, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 4: Annotated Tiers — Mitochondrial Structure (4 tiers = stacked)
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    render_annotated_tiers(
        slide=s4,
        content=SlideContent(
            title="Mitochondrial Architecture: Layers of Function",
            body_bullets=[
                "Outer Membrane: Freely permeable via porins — separates mitochondria from cytoplasm",
                "Intermembrane Space: H⁺ gradient reservoir — proton concentration 10× higher than matrix",
                "Inner Membrane: Cristae folds house ETC complexes I-IV and ATP synthase — impermeable to ions",
                "Matrix: Contains Krebs cycle enzymes, mtDNA (37 genes), and ribosomes for local protein synthesis",
            ],
        ),
        theme=theme, slide_number=4, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 5: Concept Split — ATP Synthase
    from PIL import Image
    import io
    img = Image.new("RGB", (400, 300), color=(40, 120, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    fake_img = buf.getvalue()

    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    render_concept_split(
        slide=s5,
        content=SlideContent(
            title="ATP Synthase: The World's Smallest Rotary Motor",
            key_insight="ATP synthase is a molecular turbine that spins at ~9,000 RPM, converting the proton motive force into chemical energy. Each 360° rotation produces 3 ATP molecules.",
            body_bullets=[
                "Molecular structure: F₀ subunit (membrane rotor) + F₁ subunit (catalytic head) — total ~600 kDa",
                "Chemiosmosis: H⁺ ions flow down concentration gradient through F₀, driving rotation of the γ-shaft",
                "Efficiency: ~65% energy conversion efficiency — far exceeding most human-engineered motors (~25%)",
            ],
            image_bytes=fake_img,
        ),
        theme=theme, slide_number=5, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 6: Example Grid — Real-World Applications
    s6 = prs.slides.add_slide(prs.slide_layouts[6])
    render_example_grid(
        slide=s6,
        content=SlideContent(
            title="Applications of Respiration Research",
            body_bullets=[
                "Medical: Cyanide poisoning blocks Complex IV — understanding ETC saved 94% of treated patients (CDC, 2019)",
                "Athletics: VO₂ max training increases mitochondrial density 40-50% in skeletal muscle (Holloszy, 1967)",
                "Agriculture: Controlled atmosphere storage slows fruit respiration, extending shelf life 3-5× (USDA)",
                "Biotechnology: Engineering yeast mitochondria for biofuel production — ethanol yield +28% (MIT, 2022)",
            ],
        ),
        theme=theme, slide_number=6, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 7: Content slide with eyebrow "TYPE 2 — ANAEROBIC"
    s7 = prs.slides.add_slide(prs.slide_layouts[6])
    render_academic_slide(
        slide=s7,
        slide_spec={
            "type": "concept",
            "title": "Anaerobic Respiration & Fermentation",
            "section_label": "TYPE 2 — ANAEROBIC",
            "key_message": "Without O₂, cells use fermentation to regenerate NAD⁺ — yielding only 2 ATP per glucose.",
            "body_bullets": [
                "Lactic acid fermentation: Pyruvate → lactate (muscle cells). Reversible; lactate recycled in liver (Cori cycle)",
                "Alcoholic fermentation: Pyruvate → ethanol + CO₂ (yeast, plants). Basis of brewing — $594B global industry",
                "Efficiency comparison: Aerobic yields 36 ATP vs fermentation's 2 ATP — 18× difference",
                "Evolutionary significance: Glycolysis evolved ~3.5 Bya in anaerobic conditions, before atmospheric O₂",
            ],
        },
        theme=theme, slide_number=7, total_slides=total, deck_title="Cellular Respiration"
    )

    # Slide 8: Closing
    s8 = prs.slides.add_slide(prs.slide_layouts[6])
    render_academic_slide(
        slide=s8,
        slide_spec={
            "type": "qa",
            "title": "Questions & Review",
            "key_message": "",
            "body_bullets": [
                "Why is the ETC responsible for 85% of ATP production?",
                "How does cyanide poisoning demonstrate the critical role of Complex IV?",
            ],
        },
        theme=theme, slide_number=8, total_slides=total, deck_title="Cellular Respiration"
    )

    out = os.path.join(OUTPUT_DIR, "verification_cellular_respiration.pptx")
    prs.save(out)
    print(f"[SUCCESS] Cellular Respiration deck: {out} ({len(prs.slides)} slides)")
    return out


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generate_french_revolution_deck()
    generate_cellular_respiration_deck()
