"""
Fast Concurrent Bundled Icon Generator via Pollinations.ai (Option A)
====================================================================
"""
import os
import sys
import asyncio
import urllib.parse
import httpx
from PIL import Image, ImageDraw

ICONS = [
    {"name": "person", "prompt": "flat vector icon, simple line art, person silhouette avatar, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "plate-stack", "prompt": "flat vector icon, simple line art, plate stack representing a stack data structure, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "tree-branch", "prompt": "flat vector icon, simple line art, hierarchical tree branch nodes data structure, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "network-graph", "prompt": "flat vector icon, simple line art, network graph topology connected nodes, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "database-cylinder", "prompt": "flat vector icon, simple line art, database cylinder server storage icon, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "queue-line", "prompt": "flat vector icon, simple line art, queue line representing FIFO queue data structure, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "definition-book", "prompt": "flat vector icon, simple line art, open book glossary definition icon, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "warning-trap", "prompt": "flat vector icon, simple line art, warning triangle misconception pitfall icon, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "check-badge", "prompt": "flat vector icon, simple line art, round award badge with checkmark discipline icon, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"},
    {"name": "activity-icon", "prompt": "flat vector icon, simple line art, classroom exercise hands-on activity icon, transparent background, single accent color #1E3A8A, minimal, no text, centered, isolated on white"}
]

TARGET_DIR = os.path.abspath("backend/app/services/presentation_engine/assets/icons")
PUBLIC_DIR = os.path.abspath("frontend/public/icons")
SCRATCH_DIR = os.path.abspath("scratch/icons")
ARTIFACT_DIR = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\681942a3-5aba-4ce8-b545-b507936417a0\icons"

for d in [TARGET_DIR, PUBLIC_DIR, SCRATCH_DIR, ARTIFACT_DIR]:
    os.makedirs(d, exist_ok=True)

async def fetch_one(client: httpx.AsyncClient, item: dict):
    name = item["name"]
    prompt = item["prompt"]
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true&seed=42"
    print(f"Starting fetch for '{name}'...", flush=True)
    
    for attempt in range(2):
        try:
            res = await client.get(url, timeout=30.0)
            if res.status_code == 200:
                for directory in [TARGET_DIR, PUBLIC_DIR, SCRATCH_DIR, ARTIFACT_DIR]:
                    with open(os.path.join(directory, f"{name}.png"), "wb") as f:
                        f.write(res.content)
                print(f"[OK] Downloaded {name}.png ({len(res.content)} bytes)", flush=True)
                return (name, os.path.join(TARGET_DIR, f"{name}.png"))
        except Exception as e:
            print(f"[RETRY] {name} attempt {attempt+1} failed: {e}", flush=True)
            await asyncio.sleep(2)
            
    print(f"[FAILED] {name} could not be downloaded", flush=True)
    return None

async def main():
    limits = httpx.Limits(max_connections=5, max_keepalive_connections=5)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [fetch_one(client, item) for item in ICONS]
        results = await asyncio.gather(*tasks)

    valid = [r for r in results if r is not None]
    print(f"\nCompleted {len(valid)} / {len(ICONS)} icons.", flush=True)

    # Build 2x5 contact sheet
    card_w, card_h = 320, 360
    grid_img = Image.new("RGB", (card_w * 5, card_h * 2), (248, 250, 252))
    draw = ImageDraw.Draw(grid_img)

    for idx, (name, path) in enumerate(valid):
        row = idx // 5
        col = idx % 5
        x = col * card_w
        y = row * card_h

        draw.rectangle([x + 10, y + 10, x + card_w - 10, y + card_h - 10], fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        try:
            icon = Image.open(path).convert("RGBA")
            icon = icon.resize((240, 240), Image.Resampling.LANCZOS)
            grid_img.paste(icon, (x + 40, y + 30), mask=icon)
        except Exception as err:
            print(f"Error drawing icon {name}: {err}")

        draw.text((x + 20, y + 300), name.upper(), fill=(30, 58, 138))

    contact_path = os.path.join(TARGET_DIR, "all_10_icons_preview.png")
    grid_img.save(contact_path)
    grid_img.save(os.path.join(ARTIFACT_DIR, "all_10_icons_preview.png"))
    grid_img.save(r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\681942a3-5aba-4ce8-b545-b507936417a0\all_10_icons_preview.png")
    grid_img.save(os.path.join(PUBLIC_DIR, "all_10_icons_preview.png"))
    grid_img.save(os.path.abspath("all_10_icons_preview.png"))
    print(f"[MONTAGE CREATED] Saved to {contact_path}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
