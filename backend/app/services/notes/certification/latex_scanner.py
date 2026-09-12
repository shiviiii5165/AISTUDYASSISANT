"""
TeachGenie Artifact Certification — Raw LaTeX Scanner
=====================================================
Audits final rendered text (from PDF text extraction and DOM content) to detect
actual visible source markup leakage. Categorizes defects:
- RAW_LATEX_DELIMITER ($$, $)
- RAW_LATEX_COMMAND (\\frac, \\text{, \\sqrt, etc.)
- RAW_LATEX_ESCAPE
- BROKEN_SUPERSCRIPT (^{)
- BROKEN_SUBSCRIPT (_{)
- MATH_RENDER_FAILURE
Preserves valid Unicode symbols (σ, π, superscripts, subscripts) without false alarms.
"""
import re
from typing import List, Tuple
from .schemas import RenderingDefect, RenderingDefectType


class RawLatexScanner:
    """Detects raw LaTeX commands, delimiters, and broken typesetting in student artifacts."""

    LATEX_COMMANDS = [
        (r'\\frac\b', r'\frac fraction command'),
        (r'\\text\{', r'\text{ command'),
        (r'\\sqrt\b', r'\sqrt root command'),
        (r'\\begin\{', r'\begin environment'),
        (r'\\end\{', r'\end environment'),
        (r'\\mathbf\{', r'\mathbf command'),
        (r'\\mathrm\{', r'\mathrm command'),
        (r'\\sigma\b', r'\sigma Greek command (use Unicode σ)'),
        (r'\\pi\b', r'\pi Greek command (use Unicode π)'),
        (r'\\alpha\b', r'\alpha Greek command (use Unicode α)'),
        (r'\\beta\b', r'\beta Greek command (use Unicode β)'),
        (r'\\times\b', r'\times operator command (use Unicode ×)'),
        (r'\\rightarrow\b', r'\rightarrow command (use Unicode →)'),
        (r'\\cdot\b', r'\cdot command'),
        (r'\\left\(', r'\left( delimiter command'),
        (r'\\right\)', r'\right) delimiter command'),
    ]

    @classmethod
    def scan_text(cls, text: str, page_number: int = 1) -> List[RenderingDefect]:
        """Scans extracted text for raw LaTeX defects."""
        defects: List[RenderingDefect] = []

        if not text:
            return defects

        # 1. Detect Raw LaTeX Delimiters: $$ ... $$
        if "$$" in text:
            matches = re.findall(r'\$\$(.*?)\$\$', text)
            for m in matches:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.RAW_LATEX_DELIMITER,
                    page=page_number,
                    message=f"Raw LaTeX block delimiter '$$' leaked into student text: '$${m[:40]}$$'",
                    severity="critical",
                    snippet=m[:60]
                ))

        # 2. Context-Aware Inline Math Delimiters: $ ... $ (excluding currency like $50, $100)
        math_inline_matches = re.finditer(r'(?<!\$)\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\$)', text)
        for m in math_inline_matches:
            content = m.group(1).strip()
            # Currency heuristic: solely numbers or currency terms
            is_currency = bool(re.match(r'^\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:USD|dollars|cents|million|billion))?$', content, re.IGNORECASE))
            has_math_tokens = (
                any(c in content for c in ['=', '\\', '^', '_', '+', '-', '*', '/', '<', '>', '±', '≤', '≥', 'λ', 'μ', 'π', 'σ', 'Δ'])
                or bool(re.search(r'\b[a-zA-Z]\s*[=+\-*/]\s*[a-zA-Z0-9]', content))
            )
            if not is_currency and has_math_tokens:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.RAW_LATEX_DELIMITER,
                    page=page_number,
                    message=f"Raw inline LaTeX delimiter '$' leaked into student text: '${content[:40]}$'",
                    severity="critical",
                    snippet=m.group(0)[:60]
                ))

        # 3. Detect Raw LaTeX Commands
        for pat, desc in cls.LATEX_COMMANDS:
            matches = re.finditer(pat, text)
            for m in matches:
                start = max(0, m.start() - 15)
                end = min(len(text), m.end() + 25)
                context_snippet = text[start:end].replace('\n', ' ')
                defects.append(RenderingDefect(
                    type=RenderingDefectType.RAW_LATEX_COMMAND,
                    page=page_number,
                    message=f"Raw LaTeX command ({desc}) leaked into student-visible text.",
                    severity="critical",
                    snippet=context_snippet
                ))

        # 4. Broken Superscripts: ^{
        if "^{" in text:
            matches = re.finditer(r'\^\{([^}]+)\}', text)
            for m in matches:
                defects.append(RenderingDefect(
                    type=RenderingDefectType.BROKEN_SUPERSCRIPT,
                    page=page_number,
                    message=f"Broken unrendered superscript markup leaked: '^{{{m.group(1)}}}'",
                    severity="critical",
                    snippet=m.group(0)
                ))

        # 5. Broken Subscripts: _{ or }_
        if "_{" in text or "}_" in text:
            matches = re.finditer(r'\_\{([^}]+)\}|\}\{([^_}]+)\}\_', text)
            for m in matches:
                matched_val = m.group(1) or m.group(2)
                defects.append(RenderingDefect(
                    type=RenderingDefectType.BROKEN_SUBSCRIPT,
                    page=page_number,
                    message=f"Broken unrendered subscript markup leaked: '{m.group(0)}'",
                    severity="critical",
                    snippet=m.group(0)
                ))

        # 6. Math Render Failure Markers
        if "ParseError" in text or "Undefined control sequence" in text:
            defects.append(RenderingDefect(
                type=RenderingDefectType.MATH_RENDER_FAILURE,
                page=page_number,
                message="Typesetting engine parse error displayed in student artifact.",
                severity="critical",
                snippet=text[:80]
            ))

        return defects


# Alias for ergonomic importing
LaTeXScanner = RawLatexScanner
