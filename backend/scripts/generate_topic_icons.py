"""
Batch Icon Generator — Topic-Agnostic Icon Library (Option A: AI-Generated)
=============================================================================
Generates ~50 topic-agnostic PNG icons using Google's Gemini image generation API.
This matches the same AI pipeline and quality bar as the already-approved
CS-structure icons (e.g. plate-stack.png).

Usage:
    python scripts/generate_topic_icons.py

Each icon is generated with a consistent prompt template producing clean,
modern flat-style vector icons on white circular backgrounds — professional
quality suitable for presentation slides.

Icons that already exist on disk are skipped (idempotent). To regenerate,
delete the target file first.

IMPORTANT: This script requires the GOOGLE_API_KEY environment variable
or uses the same API routing as the main application.
"""
import os
import sys
import time
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..",
    "app", "services", "presentation_engine", "assets", "icons", "topic"
)

# ═══════════════════════════════════════════════════════════════════════════
# ICON SPECIFICATIONS: filename -> human-readable description for AI prompt
# ═══════════════════════════════════════════════════════════════════════════

ICON_SPECS = {
    # Healthcare & Medicine
    "medical-cross.png": "a red medical cross symbol, healthcare/medicine",
    "dna-helix.png": "a DNA double helix strand, genetics/molecular biology",
    "microscope.png": "a laboratory microscope, research/biology",
    "heartbeat.png": "a heart with an ECG/heartbeat line, cardiology/vital signs",
    "pill-capsule.png": "a medicine pill capsule, pharmaceuticals/treatment",

    # Finance & Business
    "chart-upward.png": "an upward trending bar chart with arrow, financial growth/market",
    "coin-stack.png": "a stack of coins, money/currency/economics",
    "briefcase.png": "a business briefcase, corporate/enterprise",
    "handshake.png": "two hands shaking, partnership/collaboration/deal",

    # Technology & Computing
    "circuit-board.png": "a circuit board with chip traces, hardware/electronics",
    "cloud-server.png": "a cloud with server rack inside, cloud computing/hosting",
    "shield-lock.png": "a shield with a lock icon, cybersecurity/encryption",
    "robot-arm.png": "a robotic arm, robotics/automation/industrial",
    "neural-network.png": "a brain with neural network nodes and connections, AI/deep learning",
    "code-bracket.png": "code brackets angle brackets, programming/software development",

    # Education
    "graduation-cap.png": "a graduation cap/mortarboard, education/university/academic",
    "open-book.png": "an open book with pages, reading/knowledge/library",

    # Environment & Nature
    "leaf-eco.png": "a green leaf, environment/ecology/sustainability",
    "solar-panel.png": "a solar panel with sun rays, renewable energy/solar power",
    "water-drop.png": "a water droplet, hydrology/water/ocean/marine",
    "globe-earth.png": "a globe showing Earth continents, global/world/geography",

    # Transportation
    "car-vehicle.png": "a car/automobile side profile, vehicle/transportation",
    "airplane.png": "an airplane in flight, aviation/aerospace/airline",
    "satellite.png": "a satellite orbiting in space, space technology/GPS/navigation",

    # Communication
    "signal-tower.png": "a radio signal tower with waves, wireless/telecom/broadcast",
    "speech-bubble.png": "a speech bubble/chat bubble, language/NLP/conversation",

    # Agriculture & Food
    "wheat-grain.png": "wheat stalks/grain, agriculture/farming/crops",
    "food-plate.png": "a plate with food and utensils, nutrition/culinary/cooking",

    # Law & Government
    "scales-justice.png": "scales of justice balanced, law/legal/ethics",
    "government-building.png": "a government building with columns and dome, parliament/democracy",

    # Science
    "atom-model.png": "an atom model with electron orbits, physics/quantum/nuclear",
    "beaker-chemistry.png": "a chemistry beaker/flask with liquid, chemistry/chemical reaction",
    "telescope.png": "a telescope pointed at stars, astronomy/space/cosmos",

    # Manufacturing & Industry
    "factory-gear.png": "a factory with mechanical gear, manufacturing/production/industrial",
    "wrench-tool.png": "a wrench/spanner tool, engineering/mechanical/maintenance",

    # Art & Culture
    "palette-brush.png": "an artist palette with paintbrush, art/design/creative",
    "music-note.png": "a musical note, music/audio/sound",
    "camera-lens.png": "a camera with lens, photography/film/visual media",

    # Sports & Fitness
    "trophy-cup.png": "a golden trophy cup, sports/competition/championship",

    # Weather & Climate
    "thermometer.png": "a thermometer showing temperature, climate/weather/thermal",

    # Math & Statistics
    "graph-chart.png": "a line graph/scatter plot with data points, statistics/data analytics",
    "calculator.png": "a calculator with buttons, mathematics/calculation/arithmetic",

    # History
    "hourglass.png": "an hourglass with sand flowing, history/time/timeline",
    "scroll-document.png": "an ancient scroll/parchment document, document/archive/manuscript",
}

# Consistent prompt template matching the CS-structure icon style
PROMPT_TEMPLATE = (
    "A clean, modern flat-style icon of {description}, on a white circular background. "
    "Minimalist professional design suitable for educational presentation slides. "
    "Centered composition, simple clean lines, no text, high contrast. "
    "Style: flat vector icon, isometric, consistent with a professional design system."
)


async def generate_single_icon(filename: str, description: str) -> bool:
    """Generate a single icon using the AI image generation API."""
    output_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_path):
        return False  # Skip existing

    prompt = PROMPT_TEMPLATE.format(description=description)

    try:
        # Use the same AI router used by the main application
        from app.services.ai import router

        # Generate image via Gemini image generation
        image_bytes = await router.generate_image(prompt=prompt)

        if image_bytes and len(image_bytes) > 100:
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f"  [OK] {filename}")
            return True
        else:
            print(f"  [SKIP] {filename}: empty response")
            return False

    except Exception as e:
        print(f"  [ERROR] {filename}: {e}")
        return False


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generated = 0
    skipped = 0
    errors = 0

    for filename, description in ICON_SPECS.items():
        output_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(output_path):
            skipped += 1
            continue

        success = await generate_single_icon(filename, description)
        if success:
            generated += 1
        else:
            errors += 1

        # Rate limit: 2 second delay between API calls
        await asyncio.sleep(2.0)

    print(f"\n[DONE] Generated: {generated}, Skipped (existing): {skipped}, Errors: {errors}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Total icon specs: {len(ICON_SPECS)}")


if __name__ == "__main__":
    asyncio.run(main())
