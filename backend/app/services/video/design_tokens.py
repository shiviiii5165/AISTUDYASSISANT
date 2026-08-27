"""
TeachGenie — Shared Design Tokens for PPT & Video
=================================================
Unifies typography, color palettes, spacing, border radiuses, and component
styles across Presentations and Educational Videos for visual continuity.
"""
from typing import Dict, Any

DESIGN_TOKENS: Dict[str, Dict[str, Any]] = {
    "academic": {
        "name": "Academic Clean",
        "bg_color": "#F8FAFC",
        "primary": "#2563EB",       # Royal Blue
        "secondary": "#1E293B",     # Slate Dark
        "accent": "#DBEAFE",        # Light Blue
        "text_dark": "#0F172A",
        "text_muted": "#64748B",
        "card_bg": "#FFFFFF",
        "border": "#E2E8F0",
        "font_heading": "Arial, Helvetica, sans-serif",
        "font_body": "Arial, Helvetica, sans-serif",
        "border_radius": 12,
    },
    "technical": {
        "name": "Technical Deep Dive",
        "bg_color": "#0F172A",      # Slate 900
        "primary": "#38BDF8",       # Sky Blue
        "secondary": "#E2E8F0",     # Light Slate
        "accent": "#1E293B",        # Card Dark
        "text_dark": "#F8FAFC",
        "text_muted": "#94A3B8",
        "card_bg": "#1E293B",
        "border": "#334155",
        "font_heading": "Courier New, monospace",
        "font_body": "Arial, sans-serif",
        "border_radius": 8,
    },
    "modern_explainer": {
        "name": "Modern Explainer",
        "bg_color": "#FAFAFA",
        "primary": "#7C3AED",       # Violet 600
        "secondary": "#18181B",     # Zinc 900
        "accent": "#EDE9FE",        # Violet 100
        "text_dark": "#18181B",
        "text_muted": "#71717A",
        "card_bg": "#FFFFFF",
        "border": "#E4E4E7",
        "font_heading": "Arial, sans-serif",
        "font_body": "Arial, sans-serif",
        "border_radius": 16,
    },
    "visual_learning": {
        "name": "Visual Learning",
        "bg_color": "#F0FDF4",      # Emerald 50
        "primary": "#059669",       # Emerald 600
        "secondary": "#064E3B",     # Emerald 900
        "accent": "#D1FAE5",        # Emerald 100
        "text_dark": "#064E3B",
        "text_muted": "#4B5563",
        "card_bg": "#FFFFFF",
        "border": "#A7F3D0",
        "font_heading": "Arial, sans-serif",
        "font_body": "Arial, sans-serif",
        "border_radius": 16,
    },
    "cinematic": {
        "name": "Cinematic Documentary",
        "bg_color": "#09090B",      # Zinc 950
        "primary": "#F59E0B",       # Amber 500
        "secondary": "#FAFAFA",
        "accent": "#27272A",
        "text_dark": "#FAFAFA",
        "text_muted": "#A1A1AA",
        "card_bg": "#18181B",
        "border": "#27272A",
        "font_heading": "Georgia, serif",
        "font_body": "Arial, sans-serif",
        "border_radius": 8,
    }
}


def get_design_tokens(style_name: str) -> Dict[str, Any]:
    """Retrieves design tokens with safe fallback to academic."""
    return DESIGN_TOKENS.get(style_name.lower(), DESIGN_TOKENS["academic"])
