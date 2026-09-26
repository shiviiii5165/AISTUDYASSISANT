"""
LearnByGenie — Text Fitter
=========================
Calculates text measurements to prevent overflow, clipping, and collisions.
Since python-pptx doesn't have a layout engine, we estimate it here.
"""
from pptx.util import Inches, Pt, Emu
from .tokens import TypeToken

def _to_inches(val) -> float:
    if hasattr(val, 'inches'):
        return val.inches
    return val / 914400.0

def estimate_text_height(
    text: str,
    token: TypeToken,
    width,
    word_wrap: bool = True,
    internal_margin_y = Inches(0.1),
    internal_margin_x = Inches(0.2),
    para_space_after_pt: float = 0.0,
    para_space_before_pt: float = 0.0,
) -> Emu:
    """
    Estimate the height required to render a string in PowerPoint.
    Pass para_space_after_pt / para_space_before_pt to account for per-paragraph
    spacing set by the caller (e.g. space_after=Pt(6), space_before=Pt(2) in add_bullet_list).
    """
    if not text:
        return Emu(0)

    font_size_pt = token.size.pt
    # Average character width ratio for typical fonts (Calibri, Georgia)
    char_width_ratio = 0.52
    if token.bold:
        char_width_ratio = 0.58

    avg_char_width_inches = (font_size_pt * char_width_ratio) / 72.0

    # Available width for text
    usable_width_inches = max(0.1, _to_inches(width) - _to_inches(internal_margin_x))
    chars_per_line = max(1, int(usable_width_inches / avg_char_width_inches))

    paragraphs = text.split('\n')
    lines = 0
    for paragraph in paragraphs:
        if not word_wrap:
            lines += 1
        else:
            length = len(paragraph)
            if length == 0:
                lines += 1
            else:
                # +1 ensures at least one line; buffer factor 1.15 accounts for
                # variable-width chars (wide Unicode, numbers) and subpixel rounding
                lines += int((length / chars_per_line) * 1.15) + 1

    line_height_inches = (font_size_pt * token.line_spacing) / 72.0

    # Per-paragraph spacing contribution (space_before + space_after converted to inches)
    para_spacing_per_para = (para_space_before_pt + para_space_after_pt) / 72.0
    para_spacing_total = len(paragraphs) * para_spacing_per_para

    # 15% safety buffer on the raw text height to absorb measurement inaccuracies
    text_height_inches = lines * line_height_inches * 1.15
    total_height_inches = text_height_inches + para_spacing_total + _to_inches(internal_margin_y)

    return Inches(total_height_inches)


def fit_text_to_box(
    text: str,
    token: TypeToken,
    width: Emu,
    max_height: Emu,
    min_font_pt: int = 11,
    word_wrap: bool = True,
    para_space_after_pt: float = 0.0,
    para_space_before_pt: float = 0.0,
) -> tuple[TypeToken, str]:
    """
    Attempts to fit text into a box by reducing font size.
    If it hits min_font_pt and still doesn't fit, it truncates the text.
    Returns the adapted TypeToken and the potentially truncated string.
    """
    if not text:
        return token, text

    # Clamp the floor to the token's starting size — a BADGE at 10pt
    # should never have a 14pt floor that skips the shrink loop entirely.
    effective_min = min(min_font_pt, int(token.size.pt))

    current_token = TypeToken(
        font_name=token.font_name,
        size=token.size,
        bold=token.bold,
        italic=token.italic,
        line_spacing=token.line_spacing
    )

    def _h(tok, txt):
        return estimate_text_height(
            txt, tok, width, word_wrap,
            para_space_after_pt=para_space_after_pt,
            para_space_before_pt=para_space_before_pt,
        )

    # Try shrinking font size
    while current_token.size.pt >= effective_min:
        if _h(current_token, text) <= max_height:
            return current_token, text

        # Reduce by 2pt
        new_pt = current_token.size.pt - 2
        if new_pt < effective_min:
            break

        current_token = TypeToken(
            font_name=current_token.font_name,
            size=Pt(new_pt),
            bold=current_token.bold,
            italic=current_token.italic,
            line_spacing=current_token.line_spacing
        )

    # If we get here, it still doesn't fit at min_font_pt. We must truncate.
    # We truncate paragraph by paragraph (for bullet lists), then word by word.
    paragraphs = text.split('\n')
    while len(paragraphs) > 1:
        paragraphs.pop()
        candidate = "\n".join(paragraphs) + "\n..."
        if _h(current_token, candidate) <= max_height:
            return current_token, candidate

    # Finally fall back to word-by-word truncation on whatever remains
    words = text.split(' ')
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words) + "..."
        if _h(current_token, candidate) <= max_height:
            return current_token, candidate

    return current_token, text
