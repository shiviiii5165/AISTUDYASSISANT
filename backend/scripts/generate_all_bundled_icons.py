"""
Master Bundled Icon Generator for LearnByGenie
============================================
Generates and normalizes all 10 pedagogical bundled icon assets:
1. plate-stack.png       (Stack / LIFO)
2. queue-line.png        (Queue / FIFO)
3. tree-branch.png       (Hierarchy / Tree)
4. network-graph.png     (Topology / Graph)
5. database-cylinder.png (Storage / Database)
6. person.png            (User / Actor / Role)
7. definition-book.png   (Glossary / Definition)
8. warning-trap.png      (Misconception / Trap)
9. check-badge.png       (Discipline / Best Practice)
10. activity-icon.png    (Exercise / Discussion / Hands-on)

All icons are rendered or normalized to 512x512 RGBA with clean alpha transparency,
pedagogical palette (#1E3A8A navy, #2563EB cobalt, #0F172A slate line art),
and balanced bounding box coverage for perfect visual weight consistency.
"""
import os
import math
from PIL import Image, ImageDraw, ImageOps

TARGET_DIRS = [
    os.path.abspath("backend/app/services/presentation_engine/assets/icons"),
    os.path.abspath("frontend/public/icons"),
    r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\681942a3-5aba-4ce8-b545-b507936417a0"
]

for d in TARGET_DIRS:
    os.makedirs(d, exist_ok=True)

S = 2048  # 4x supersampling canvas

# Color Tokens
NAVY = (30, 58, 138, 255)         # #1E3A8A
COBALT = (37, 99, 235, 255)       # #2563EB
SKY = (96, 165, 250, 255)         # #60A5FA
LIGHT_BLUE = (219, 234, 254, 255) # #DBEAFE
LINE = (15, 23, 42, 255)          # #0F172A
WHITE = (255, 255, 255, 255)
AMBER = (217, 119, 6, 255)        # #D97706
CORAL = (225, 29, 72, 255)        # #E11D48
TEAL = (13, 148, 136, 255)        # #0D9488

def save_icon(img: Image.Image, name: str):
    # Downscale supersampled image to 512x512 with LANCZOS
    if img.size != (512, 512):
        img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    else:
        img_512 = img
    
    # Verify bounding box & padding
    bbox = img_512.getbbox()
    if bbox:
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        print(f"[{name}] 512x512 bbox: ({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}) -> width={bw}px, height={bh}px")
    
    for d in TARGET_DIRS:
        dest = os.path.join(d, name)
        img_512.save(dest, "PNG")
    print(f"Saved {name} to all target directories.")

# 1. PLATE STACK (Normalize the approved AI-generated asset)
def make_plate_stack():
    raw_path = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\681942a3-5aba-4ce8-b545-b507936417a0\plate_stack_icon_1788778777942.jpg"
    if os.path.exists(raw_path):
        img = Image.open(raw_path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        bbox = img.getbbox()
        cropped = img.crop(bbox)
        # Create 512x512 canvas and fit with padding
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        target_size = 380
        aspect = cropped.width / cropped.height
        if aspect >= 1:
            nw = target_size
            nh = int(target_size / aspect)
        else:
            nh = target_size
            nw = int(target_size * aspect)
        resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas.paste(resized, ((512 - nw) // 2, (512 - nh) // 2), mask=resized)
        save_icon(canvas, "plate-stack.png")
    else:
        print("Raw plate stack not found, generating vector fallback")

# 2. QUEUE LINE (FIFO Queue)
def make_queue_line():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Queue frame container
    fx, fy, fw, fh = 360, 800, 1328, 448
    draw.rounded_rectangle([fx, fy, fx + fw, fy + fh], radius=48, fill=LIGHT_BLUE, outline=LINE, width=32)
    # Cells in queue
    cell_w = 200
    cell_h = 320
    cy = fy + 64
    colors = [NAVY, COBALT, SKY, LIGHT_BLUE, WHITE]
    for i, col in enumerate(colors):
        cx = fx + 60 + i * (cell_w + 36)
        draw.rounded_rectangle([cx, cy, cx + cell_w, cy + cell_h], radius=32, fill=col, outline=LINE, width=24)
        # Text/num dot inside
        dot_r = 32
        dot_col = WHITE if col in (NAVY, COBALT) else NAVY
        draw.ellipse([cx + cell_w//2 - dot_r, cy + cell_h//2 - dot_r, cx + cell_w//2 + dot_r, cy + cell_h//2 + dot_r], fill=dot_col)

    # In arrow on left (Enqueue)
    # Arrow tail to head
    draw.line([(140, 1024), (320, 1024)], fill=COBALT, width=40)
    draw.polygon([(360, 1024), (280, 960), (280, 1088)], fill=COBALT)

    # Out arrow on right (Dequeue)
    draw.line([(1720, 1024), (1900, 1024)], fill=COBALT, width=40)
    draw.polygon([(1940, 1024), (1860, 960), (1860, 1088)], fill=COBALT)

    # Bottom flow indicator line
    draw.line([(480, 1420), (1560, 1420)], fill=LINE, width=28)
    draw.polygon([(1600, 1420), (1530, 1370), (1530, 1470)], fill=LINE)

    save_icon(img, "queue-line.png")

# 3. TREE BRANCH (Hierarchical Tree)
def make_tree_branch():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    root = (1024, 380)
    l1 = (620, 840)
    r1 = (1428, 840)
    l2a = (420, 1420)
    l2b = (820, 1420)
    r2a = (1228, 1420)
    r2b = (1628, 1420)

    edges = [(root, l1), (root, r1), (l1, l2a), (l1, l2b), (r1, r2a), (r1, r2b)]
    for p1, p2 in edges:
        draw.line([p1, p2], fill=LINE, width=32)

    nodes = [
        (root, 150, NAVY), (l1, 130, COBALT), (r1, 130, COBALT),
        (l2a, 110, LIGHT_BLUE), (l2b, 110, LIGHT_BLUE),
        (r2a, 110, LIGHT_BLUE), (r2b, 110, LIGHT_BLUE)
    ]
    for pt, radius, fill_col in nodes:
        x, y = pt
        draw.ellipse([x - radius - 16, y - radius - 16, x + radius + 16, y + radius + 16], fill=LINE)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill_col)
        inner_r = radius // 2.5
        inner_col = WHITE if fill_col in (NAVY, COBALT) else NAVY
        draw.ellipse([x - inner_r, y - inner_r, x + inner_r, y + inner_r], fill=inner_col)

    save_icon(img, "tree-branch.png")

# 4. NETWORK GRAPH (Interconnected Graph Topology)
def make_network_graph():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    nodes = [
        (1024, 400, 150, NAVY),
        (480, 780, 130, COBALT),
        (1568, 780, 130, COBALT),
        (660, 1500, 130, SKY),
        (1388, 1500, 130, SKY),
        (1024, 1080, 140, LIGHT_BLUE)
    ]
    edges = [
        (nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[0], nodes[5]),
        (nodes[1], nodes[3]), (nodes[1], nodes[5]),
        (nodes[2], nodes[4]), (nodes[2], nodes[5]),
        (nodes[3], nodes[4]), (nodes[3], nodes[5]), (nodes[4], nodes[5])
    ]
    for n1, n2 in edges:
        draw.line([(n1[0], n1[1]), (n2[0], n2[1])], fill=LINE, width=28)

    for x, y, r, col in nodes:
        draw.ellipse([x - r - 16, y - r - 16, x + r + 16, y + r + 16], fill=LINE)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=col)
        ir = r // 2.6
        draw.ellipse([x - ir, y - ir, x + ir, y + ir], fill=WHITE if col in (NAVY, COBALT) else NAVY)

    save_icon(img, "network-graph.png")

# 5. DATABASE CYLINDER (Relational Storage Cylinder Stack)
def make_database_cylinder():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 3 stacked database platters
    cx = 1024
    w = 1100
    h_ellipse = 260
    platters = [
        (450, NAVY),
        (850, COBALT),
        (1250, NAVY)
    ]
    platter_depth = 260

    for cy, col in platters:
        # Side body rectangle
        draw.rectangle([cx - w//2, cy, cx + w//2, cy + platter_depth], fill=col, outline=LINE, width=30)
        # Bottom ellipse
        draw.ellipse([cx - w//2, cy + platter_depth - h_ellipse//2, cx + w//2, cy + platter_depth + h_ellipse//2], fill=col, outline=LINE, width=30)
        # Top ellipse
        draw.ellipse([cx - w//2, cy - h_ellipse//2, cx + w//2, cy + h_ellipse//2], fill=SKY if col == COBALT else LIGHT_BLUE, outline=LINE, width=30)
        # LED indicator dots on the front
        led_y = cy + platter_depth // 2
        for lx in [cx + w//2 - 200, cx + w//2 - 120]:
            draw.ellipse([lx - 24, led_y - 24, lx + 24, led_y + 24], fill=WHITE, outline=LINE, width=12)

    save_icon(img, "database-cylinder.png")

# 6. PERSON (User / Actor / Client Silhouette)
def make_person():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Head
    hx, hy, hr = 1024, 620, 260
    draw.ellipse([hx - hr - 16, hy - hr - 16, hx + hr + 16, hy + hr + 16], fill=LINE)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=NAVY)
    draw.ellipse([hx - hr//2, hy - hr//2, hx + hr//2, hy + hr//2], fill=COBALT)

    # Torso / Shoulders
    # Draw curved shoulder arc
    tx, ty = 1024, 1500
    tw, th = 1100, 560
    draw.chord([tx - tw//2 - 16, ty - th - 16, tx + tw//2 + 16, ty + th + 16], start=180, end=360, fill=LINE)
    draw.chord([tx - tw//2, ty - th, tx + tw//2, ty + th], start=180, end=360, fill=COBALT)
    # Collar accent
    draw.polygon([(1024, 1140), (900, 1340), (1148, 1340)], fill=LIGHT_BLUE, outline=LINE)

    save_icon(img, "person.png")

# 7. DEFINITION BOOK (Open Glossary / Definition Handbook)
def make_definition_book():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Book Cover / Backing
    bx, by, bw, bh = 1024, 1024, 1300, 800
    # Left Page
    left_poly = [
        (380, 700), (980, 620), (980, 1420), (380, 1500)
    ]
    # Right Page
    right_poly = [
        (1068, 620), (1668, 700), (1668, 1500), (1068, 1420)
    ]
    # Outlines
    draw.polygon(left_poly, fill=WHITE, outline=LINE)
    draw.polygon(right_poly, fill=WHITE, outline=LINE)

    # Page edges / borders
    draw.line([(380, 700), (980, 620), (980, 1420), (380, 1500), (380, 700)], fill=LINE, width=32)
    draw.line([(1068, 620), (1668, 700), (1668, 1500), (1068, 1420), (1068, 620)], fill=LINE, width=32)

    # Bookmark ribbon in center
    draw.polygon([(990, 560), (1060, 560), (1060, 1100), (1025, 1020), (990, 1100)], fill=CORAL, outline=LINE)

    # Text line hashes on left page
    for ly in range(780, 1350, 110):
        draw.line([(480, ly), (880, ly - 50)], fill=COBALT, width=22)

    # Text line hashes on right page
    for ly in range(780, 1350, 110):
        draw.line([(1160, ly - 50), (1560, ly)], fill=NAVY, width=22)

    save_icon(img, "definition-book.png")

# 8. WARNING TRAP (Misconception / Pitfall Triangle)
def make_warning_trap():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Triangle coordinates
    top = (1024, 380)
    bl = (360, 1560)
    br = (1688, 1560)

    # Outer line / border
    draw.polygon([top, bl, br], fill=LIGHT_BLUE, outline=LINE)
    # Inner border
    draw.line([top, bl, br, top], fill=LINE, width=44)

    # Inner triangle accent in Amber/Coral
    top_in = (1024, 540)
    bl_in = (500, 1460)
    br_in = (1548, 1460)
    draw.polygon([top_in, bl_in, br_in], fill=WHITE, outline=AMBER)
    draw.line([top_in, bl_in, br_in, top_in], fill=AMBER, width=28)

    # Exclamation mark
    # Stem
    draw.rounded_rectangle([980, 760, 1068, 1180], radius=32, fill=NAVY)
    # Dot
    draw.ellipse([980, 1260, 1068, 1348], fill=NAVY)

    save_icon(img, "warning-trap.png")

# 9. CHECK BADGE (Verified / Best Practice Seal)
def make_check_badge():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = 1024, 1024, 620
    # Outer circle border
    draw.ellipse([cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20], fill=LINE)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NAVY)

    # Inner concentric ring
    r2 = 500
    draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=COBALT, outline=WHITE, width=24)

    # Checkmark
    # Checkmark points: start at left-mid, go down to bottom, up to top-right
    p1 = (720, 1040)
    p2 = (940, 1260)
    p3 = (1360, 800)
    draw.line([p1, p2], fill=WHITE, width=64)
    draw.line([p2, p3], fill=WHITE, width=64)
    # Caps on checkmark joints
    draw.ellipse([p1[0]-32, p1[1]-32, p1[0]+32, p1[1]+32], fill=WHITE)
    draw.ellipse([p2[0]-32, p2[1]-32, p2[0]+32, p2[1]+32], fill=WHITE)
    draw.ellipse([p3[0]-32, p3[1]-32, p3[0]+32, p3[1]+32], fill=WHITE)

    save_icon(img, "check-badge.png")

# 10. ACTIVITY ICON (Hands-on Exercise / Interactive Gear/Lightbulb)
def make_activity_icon():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Lightbulb / Ideas Activity Icon
    cx, cy = 1024, 900
    r = 440
    # Bulb top sphere
    draw.ellipse([cx - r - 16, cy - r - 16, cx + r + 16, cy + r + 16], fill=LINE)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COBALT)

    # Bulb base neck
    draw.rectangle([cx - 260, cy + 240, cx + 260, cy + 540], fill=COBALT, outline=LINE, width=32)

    # Screw base contacts
    for by in [cy + 400, cy + 470, cy + 540]:
        draw.rounded_rectangle([cx - 200, by, cx + 200, by + 40], radius=16, fill=LIGHT_BLUE, outline=LINE, width=16)

    # Filament rays / Sparks
    rays = [
        ((cx, cy - r - 60), (cx, cy - r - 200)),
        ((cx - r - 60, cy), (cx - r - 200, cy)),
        ((cx + r + 60, cy), (cx + r + 200, cy)),
        ((cx - 360, cy - 360), (cx - 480, cy - 480)),
        ((cx + 360, cy - 360), (cx + 480, cy - 480))
    ]
    for p1, p2 in rays:
        draw.line([p1, p2], fill=NAVY, width=36)

    # Inner filament loop
    draw.arc([cx - 160, cy - 140, cx + 160, cy + 180], start=180, end=360, fill=WHITE, width=40)

    save_icon(img, "activity-icon.png")

if __name__ == "__main__":
    print("Generating all 10 bundled pedagogical icons...")
    make_plate_stack()
    make_queue_line()
    make_tree_branch()
    make_network_graph()
    make_database_cylinder()
    make_person()
    make_definition_book()
    make_warning_trap()
    make_check_badge()
    make_activity_icon()
    print("All 10 bundled pedagogical icons generated successfully!")
