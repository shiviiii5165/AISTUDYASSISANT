"""
Gold-Standard Linked List Benchmark Visualizer
==============================================
Visually demonstrates dynamic pointer structures and node updates:
1. Node Anatomy: [data | next] compartments with address references
2. HEAD pointer & node traversal
3. Insertion at Beginning: new_node.next = head, head = new_node
4. Insertion in Middle (20 -> 30, insert 25):
   - Phase 1: 25.next connects to 30 (25.next = 20.next)
   - Phase 2: 20.next breaks old link and connects to 25 (20.next = 25)
   - Visual emphasis: highlights why updating 20.next first destroys the chain!
5. Deletion & link bypassing
6. Array vs Linked List memory representation
"""
import os
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec


class LinkedListVisualizer(BaseVisualizer):
    """Gold-standard reference visualizer for data structures and pointer transitions."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        caption = scene.caption.lower()
        purpose = scene.purpose if isinstance(scene.purpose, str) else scene.purpose.value

        # Select visual mode based on scene purpose or title
        if "node" in caption or "anatomy" in caption:
            return cls._render_node_anatomy(scene, output_path, progress)
        elif "insertion" in caption or "insert" in caption:
            return cls._render_insertion_middle(scene, output_path, progress)
        elif "traversal" in caption or "head" in caption:
            return cls._render_traversal(scene, output_path, progress)
        elif "array" in caption or "trade" in caption or "pitfall" in caption:
            return cls._render_array_comparison(scene, output_path, progress)
        else:
            return cls._render_insertion_middle(scene, output_path, progress)

    @classmethod
    def _render_node_anatomy(cls, scene: SceneSpec, output_path: str, progress: float) -> str:
        img, draw = cls.create_canvas(
            title="Node Anatomy: [data | next]",
            subtitle="Each node contains a data payload and a pointer to the next memory address",
            tag="DATA STRUCTURE"
        )

        # Draw large node at center
        node_x = 420
        node_y = 240
        node_w = 440
        node_h = 220

        # Outer Node Box
        draw.rounded_rectangle([node_x, node_y, node_x + node_w, node_y + node_h], radius=16, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=3)

        # Internal Divider
        mid_x = node_x + (node_w // 2)
        draw.line([(mid_x, node_y), (mid_x, node_y + node_h)], fill=PALETTE["card_border"], width=3)

        font_label = cls.get_font(20, bold=True)
        font_val = cls.get_font(36, bold=True)
        font_sub = cls.get_font(16, bold=False)

        # Left Compartment: DATA
        draw.text((node_x + 50, node_y + 30), "DATA", fill=PALETTE["text_muted"], font=font_label)
        draw.text((node_x + 75, node_y + 85), "20", fill=PALETTE["accent_green"], font=font_val)
        draw.text((node_x + 35, node_y + 160), "Integer Payload", fill=PALETTE["text_muted"], font=font_sub)

        # Right Compartment: NEXT POINTER
        draw.text((mid_x + 50, node_y + 30), "NEXT", fill=PALETTE["text_muted"], font=font_label)
        draw.text((mid_x + 35, node_y + 85), "0x7F4A", fill=PALETTE["primary"], font=font_val)
        draw.text((mid_x + 25, node_y + 160), "Memory Reference", fill=PALETTE["text_muted"], font=font_sub)

        # Pointer arrow emerging from NEXT
        arrow_start = (node_x + node_w + 10, node_y + node_h // 2)
        arrow_end = (node_x + node_w + 160, node_y + node_h // 2)
        cls.draw_arrow(draw, arrow_start, arrow_end, color=PALETTE["primary"], width=4)
        draw.text((node_x + node_w + 30, node_y + node_h // 2 - 35), "points to next node", fill=PALETTE["primary"], font=font_sub)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_insertion_middle(cls, scene: SceneSpec, output_path: str, progress: float) -> str:
        """
        Visually teaches the insertion of node 25 between 20 and 30:
        Progress 0.0 - 0.35: 20 -> 30 exists, 25 appears below.
        Progress 0.35 - 0.70: 25.next links to 30 (highlighted in emerald green).
        Progress 0.70 - 1.00: 20.next redirects from 30 to 25. Final chain: 20 -> 25 -> 30!
        """
        img, draw = cls.create_canvas(
            title="Node Insertion & Pointer Order",
            subtitle="Crucial Order: Connect 25.next -> 30 FIRST before updating 20.next -> 25",
            tag="POINTER TRANSITION"
        )

        font_node = cls.get_font(24, bold=True)
        font_sub = cls.get_font(16, bold=False)
        font_alert = cls.get_font(18, bold=True)

        # 1. Draw Existing Nodes 20 and 30
        # Node 20
        n20_x, n20_y = 200, 220
        draw.rounded_rectangle([n20_x, n20_y, n20_x + 160, n20_y + 100], radius=12, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=3)
        draw.text((n20_x + 35, n20_y + 35), "[ 20 | • ]", fill=PALETTE["text_primary"], font=font_node)

        # Node 30
        n30_x, n30_y = 780, 220
        draw.rounded_rectangle([n30_x, n30_y, n30_x + 160, n30_y + 100], radius=12, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=3)
        draw.text((n30_x + 35, n30_y + 35), "[ 30 | • ]", fill=PALETTE["text_primary"], font=font_node)

        # New Node 25 (Positioned centrally below)
        n25_x, n25_y = 490, 440
        draw.rounded_rectangle([n25_x, n25_y, n25_x + 160, n25_y + 100], radius=12, fill=(38, 52, 75), outline=PALETTE["accent_green"], width=3)
        draw.text((n25_x + 35, n25_y + 35), "[ 25 | • ]", fill=PALETTE["accent_green"], font=font_node)
        draw.text((n25_x + 20, n25_y + 115), "New Node (25)", fill=PALETTE["accent_green"], font=font_sub)

        # Animated Link Transitions based on progress
        if progress < 0.40:
            # Direct link 20 -> 30
            cls.draw_arrow(draw, (n20_x + 160, n20_y + 50), (n30_x, n30_y + 50), color=PALETTE["primary"], width=4)
            draw.text((420, 180), "Original: 20 -> 30", fill=PALETTE["text_muted"], font=font_sub)
        elif progress < 0.75:
            # Phase 1: 25.next connects to 30!
            cls.draw_arrow(draw, (n20_x + 160, n20_y + 50), (n30_x, n30_y + 50), color=PALETTE["card_border"], width=2)
            cls.draw_arrow(draw, (n25_x + 160, n25_y + 50), (n30_x + 20, n30_y + 100), color=PALETTE["accent_green"], width=5)
            # Step Badge
            draw.rounded_rectangle([320, 150, 820, 195], radius=8, fill=PALETTE["card_bg"], outline=PALETTE["accent_green"], width=2)
            draw.text((340, 162), "STEP 1: Connect 25.next = 20.next (points 25 -> 30)", fill=PALETTE["accent_green"], font=font_alert)
        else:
            # Phase 2: 20.next connects to 25, 25.next connected to 30!
            cls.draw_arrow(draw, (n20_x + 160, n20_y + 80), (n25_x, n25_y + 50), color=PALETTE["accent_green"], width=5)
            cls.draw_arrow(draw, (n25_x + 160, n25_y + 50), (n30_x + 20, n30_y + 100), color=PALETTE["accent_green"], width=5)
            # Step Badge
            draw.rounded_rectangle([320, 150, 820, 195], radius=8, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=2)
            draw.text((340, 162), "STEP 2: Update 20.next = 25 (Chain is 20 -> 25 -> 30!)", fill=PALETTE["primary"], font=font_alert)

        # Misconception Warning Box at Bottom
        draw.rounded_rectangle([120, 600, cls.WIDTH - 120, 675], radius=10, fill=(45, 25, 30), outline=PALETTE["accent_rose"], width=2)
        draw.text((140, 615), "CRITICAL PITFALL: If you did '20.next = 25' first, the link to 30 is LOST forever!", fill=PALETTE["accent_rose"], font=font_alert)
        draw.text((140, 642), "Node 30 and all remaining nodes would become orphaned in memory (Memory Leak).", fill=PALETTE["text_muted"], font=font_sub)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_traversal(cls, scene: SceneSpec, output_path: str, progress: float) -> str:
        img, draw = cls.create_canvas(
            title="HEAD Pointer & Chain Traversal",
            subtitle="Traversal visits node-by-node sequentially until pointer == NULL",
            tag="ALGORITHM TRACE"
        )

        font_node = cls.get_font(22, bold=True)
        font_sub = cls.get_font(15, bold=False)

        # HEAD Box
        draw.rounded_rectangle([80, 260, 190, 340], radius=10, fill=PALETTE["accent_blue"])
        draw.text((105, 285), "HEAD", fill=PALETTE["text_primary"], font=font_node)

        # Nodes: 10 -> 20 -> 30 -> NULL
        node_values = ["10", "20", "30", "NULL"]
        start_x = 260
        gap = 180

        # Draw arrow from HEAD to first node
        cls.draw_arrow(draw, (190, 300), (start_x, 300), color=PALETTE["primary"], width=3)

        for i, val in enumerate(node_values):
            nx = start_x + i * gap
            is_null = (val == "NULL")

            box_border = PALETTE["accent_rose"] if is_null else PALETTE["primary"]
            draw.rounded_rectangle([nx, 260, nx + 120, 340], radius=10, fill=PALETTE["card_bg"], outline=box_border, width=2)
            draw.text((nx + 25, 285), val, fill=box_border if is_null else PALETTE["text_primary"], font=font_node)

            # Connector to next
            if i < len(node_values) - 1:
                cls.draw_arrow(draw, (nx + 120, 300), (nx + gap, 300), color=PALETTE["primary"], width=3)

        # Traversal Code snippet
        draw.rounded_rectangle([200, 440, cls.WIDTH - 200, 560], radius=10, fill=PALETTE["card_bg"], outline=PALETTE["card_border"], width=1)
        font_code = cls.get_font(16, bold=True)
        draw.text((230, 460), "Node* curr = head;", fill=PALETTE["accent_green"], font=font_code)
        draw.text((230, 490), "while (curr != NULL) {", fill=PALETTE["primary"], font=font_code)
        draw.text((270, 520), "curr = curr->next;  // Move scanner forward", fill=PALETTE["text_primary"], font=font_code)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_array_comparison(cls, scene: SceneSpec, output_path: str, progress: float) -> str:
        img, draw = cls.create_canvas(
            title="Linked List vs Array: Memory & Complexity",
            subtitle="Comparing Contiguous Memory vs Pointer-Based Node Structures",
            tag="COMPARISON"
        )

        font_h = cls.get_font(20, bold=True)
        font_td = cls.get_font(16, bold=False)

        # Array Block (Left)
        draw.rounded_rectangle([100, 180, 580, 580], radius=12, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=2)
        draw.text((140, 210), "ARRAY (Contiguous Memory)", fill=PALETTE["primary"], font=font_h)

        # Array graphical blocks
        for b_idx in range(4):
            bx = 140 + b_idx * 90
            draw.rectangle([bx, 270, bx + 80, 340], fill=(38, 52, 75), outline=PALETTE["primary"], width=2)
            draw.text((bx + 25, 290), f"[{b_idx}]", fill=PALETTE["text_primary"], font=font_td)

        draw.text((140, 380), "• Instant O(1) random index access", fill=PALETTE["accent_green"], font=font_td)
        draw.text((140, 420), "• Expensive O(N) middle insertion/shift", fill=PALETTE["accent_rose"], font=font_td)
        draw.text((140, 460), "• Fixed size allocated up front", fill=PALETTE["text_muted"], font=font_td)

        # Linked List Block (Right)
        draw.rounded_rectangle([680, 180, 1160, 580], radius=12, fill=PALETTE["card_bg"], outline=PALETTE["accent_green"], width=2)
        draw.text((720, 210), "LINKED LIST (Dynamic Nodes)", fill=PALETTE["accent_green"], font=font_h)

        # Scattered node links
        draw.rounded_rectangle([720, 270, 830, 340], radius=8, fill=(38, 52, 75), outline=PALETTE["accent_green"], width=2)
        draw.text((740, 295), "Node A", fill=PALETTE["text_primary"], font=font_td)

        cls.draw_arrow(draw, (830, 305), (920, 305), color=PALETTE["accent_green"], width=2)

        draw.rounded_rectangle([920, 270, 1030, 340], radius=8, fill=(38, 52, 75), outline=PALETTE["accent_green"], width=2)
        draw.text((940, 295), "Node B", fill=PALETTE["text_primary"], font=font_td)

        draw.text((720, 380), "• Instant O(1) insertion given pointer", fill=PALETTE["accent_green"], font=font_td)
        draw.text((720, 420), "• Slow O(N) sequential search", fill=PALETTE["accent_rose"], font=font_td)
        draw.text((720, 460), "• Dynamic memory allocation on heap", fill=PALETTE["text_muted"], font=font_td)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_animation_frame(cls, scene: SceneSpec, progress: float, output_path: str):
        cls.render_scene(scene, output_path, progress=progress)
