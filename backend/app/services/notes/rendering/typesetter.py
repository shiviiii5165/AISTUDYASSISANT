"""
LearnByGenie Document Renderer — Semantic Math & Chemistry Typesetter
===================================================================
Converts raw mathematical equations, inline expressions, and chemical formulas
into accessible, deterministic, print-ready HTML/CSS and Unicode representations.
Prevents raw LaTeX markup leakage into student-visible text while strictly preserving
correct scientific notation:
- Fractions, roots, superscripts, subscripts, Greek letters, operators, arrows
- Molecular species (H2O, NH3, SO4^2-, Na+, Cl-, SF6, etc.)
- Orbital hybridizations (sp, sp2, sp3, sp3d, sp3d2)
- Chemical bonds (sigma, pi)
"""
import re
import html
from typing import Dict, List, Tuple, Optional


class SemanticTypesetter:
    """Deterministic mathematical and chemical typesetter for student-ready artifacts."""

    GREEK_MAP = {
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
        r'\Delta': 'Δ', r'\epsilon': 'ε', r'\theta': 'θ', r'\lambda': 'λ',
        r'\mu': 'μ', r'\pi': 'π', r'\rho': 'ρ', r'\sigma': 'σ',
        r'\Sigma': 'Σ', r'\tau': 'τ', r'\phi': 'φ', r'\omega': 'ω',
        r'\Omega': 'Ω'
    }

    OPERATOR_MAP = {
        r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
        r'\qquad': '  ', r'\quad': ' ', r'\,': ' ', r'\;': ' ',
        r'\leq': '≤', r'\geq': '≥', r'\neq': '≠', r'\approx': '≈',
        r'\le': '≤', r'\ge': '≥', r'\ne': '≠',
        r'\equiv': '≡', r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
        r'\rightarrow': '→', r'\leftarrow': '←', r'\leftrightarrow': '↔',
        r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\Leftrightarrow': '⇔',
        r'\cdot': '·', r'\degree': '°', r'^\circ': '°'
    }

    HYBRIDIZATIONS = [
        ('sp3d2', 'sp<sup>3</sup>d<sup>2</sup>'),
        ('sp^3d^2', 'sp<sup>3</sup>d<sup>2</sup>'),
        ('sp^{3}d^{2}', 'sp<sup>3</sup>d<sup>2</sup>'),
        ('sp3d', 'sp<sup>3</sup>d'),
        ('sp^3d', 'sp<sup>3</sup>d'),
        ('sp^{3}d', 'sp<sup>3</sup>d'),
        ('sp3', 'sp<sup>3</sup>'),
        ('sp^3', 'sp<sup>3</sup>'),
        ('sp^{3}', 'sp<sup>3</sup>'),
        ('sp2', 'sp<sup>2</sup>'),
        ('sp^2', 'sp<sup>2</sup>'),
        ('sp^{2}', 'sp<sup>2</sup>'),
        ('dsp2', 'dsp<sup>2</sup>'),
        ('dsp^2', 'dsp<sup>2</sup>'),
        ('d2sp3', 'd<sup>2</sup>sp<sup>3</sup>'),
        ('d^2sp^3', 'd<sup>2</sup>sp<sup>3</sup>'),
    ]

    # Specific molecular species (pattern, html_replacement)
    SPECIFIC_SPECIES = [
        (r'\bSO4\^?\{?2\-?\}?', 'SO<sub>4</sub><sup>2−</sup>'),
        (r'\bSO_4\^\{2\-\}', 'SO<sub>4</sub><sup>2−</sup>'),
        (r'\bSO4\(2\-\)', 'SO<sub>4</sub><sup>2−</sup>'),
        (r'\bPO4\^?\{?3\-?\}?', 'PO<sub>4</sub><sup>3−</sup>'),
        (r'\bCO3\^?\{?2\-?\}?', 'CO<sub>3</sub><sup>2−</sup>'),
        (r'\bNO3\^?\{?\-?\}?', 'NO<sub>3</sub><sup>−</sup>'),
        (r'\bNH4\^?\{?\+?\}?', 'NH<sub>4</sub><sup>+</sup>'),
        (r'\bH3O\^?\{?\+?\}?', 'H<sub>3</sub>O<sup>+</sup>'),
        (r'\bNa(?:\^\{?\+?\}|\+(?!\w))', 'Na<sup>+</sup>'),
        (r'\bCl(?:\^\{?\-?\}|\-(?!\w))', 'Cl<sup>−</sup>'),
        (r'\bCa(?:\^\{?2\+?\}|2\+(?!\w))', 'Ca<sup>2+</sup>'),
        (r'\bMg(?:\^\{?2\+?\}|2\+(?!\w))', 'Mg<sup>2+</sup>'),
        (r'\bAl(?:\^\{?3\+?\}|3\+(?!\w))', 'Al<sup>3+</sup>'),
        (r'\bH2O\b', 'H<sub>2</sub>O'),
        (r'\bH_2O\b', 'H<sub>2</sub>O'),
        (r'\bNH3\b', 'NH<sub>3</sub>'),
        (r'\bNH_3\b', 'NH<sub>3</sub>'),
        (r'\bCH4\b', 'CH<sub>4</sub>'),
        (r'\bCH_4\b', 'CH<sub>4</sub>'),
        (r'\bSF6\b', 'SF<sub>6</sub>'),
        (r'\bSF_6\b', 'SF<sub>6</sub>'),
        (r'\bPCl5\b', 'PCl<sub>5</sub>'),
        (r'\bPCl_5\b', 'PCl<sub>5</sub>'),
        (r'\bCO2\b', 'CO<sub>2</sub>'),
        (r'\bCO_2\b', 'CO<sub>2</sub>'),
        (r'\bO2\b', 'O<sub>2</sub>'),
        (r'\bO_2\b', 'O<sub>2</sub>'),
        (r'\bN2\b', 'N<sub>2</sub>'),
        (r'\bN_2\b', 'N<sub>2</sub>'),
        (r'\bH2\b', 'H<sub>2</sub>'),
        (r'\bH_2\b', 'H<sub>2</sub>'),
        (r'\bCl2\b', 'Cl<sub>2</sub>'),
        (r'\bCl_2\b', 'Cl<sub>2</sub>'),
        (r'\bC2H4\b', 'C<sub>2</sub>H<sub>4</sub>'),
        (r'\bC2H2\b', 'C<sub>2</sub>H<sub>2</sub>'),
        (r'\bC6H6\b', 'C<sub>6</sub>H<sub>6</sub>'),
        (r'\bH2SO4\b', 'H<sub>2</sub>SO<sub>4</sub>'),
        (r'\bHNO3\b', 'HNO<sub>3</sub>'),
        (r'\bCaCO3\b', 'CaCO<sub>3</sub>'),
        (r'\bNaCl\b', 'NaCl'),
    ]

    @classmethod
    def extract_balanced_brace(cls, s: str, start_pos: int) -> Tuple[Optional[str], int]:
        """Extracts content between balanced braces { ... } starting at start_pos."""
        idx = start_pos
        while idx < len(s) and s[idx].isspace():
            idx += 1
        if idx >= len(s) or s[idx] != '{':
            return None, start_pos

        depth = 0
        content_start = idx + 1
        for i in range(idx, len(s)):
            if s[i] == '{':
                depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0:
                    return s[content_start:i], i + 1
        return None, start_pos

    @classmethod
    def replace_latex_fractions(cls, clean: str) -> str:
        """Recursively parses and replaces \frac{num}{den} handling arbitrary brace nesting."""
        while True:
            pos = clean.find(r'\frac')
            if pos == -1:
                break
            num, after_num = cls.extract_balanced_brace(clean, pos + 5)
            if num is None:
                # If unbraced like \frac 1 2, handle or break
                m_simple = re.match(r'\\frac\s*([0-9a-zA-Z])\s*([0-9a-zA-Z])', clean[pos:])
                if m_simple:
                    num_val = m_simple.group(1)
                    den_val = m_simple.group(2)
                    frac_html = f'<span class="fraction"><span class="num">{num_val}</span><span class="den">{den_val}</span></span>'
                    clean = clean[:pos] + frac_html + clean[pos + len(m_simple.group(0)):]
                    continue
                break
            den, after_den = cls.extract_balanced_brace(clean, after_num)
            if den is None:
                break
            num_html = cls._convert_latex_math_to_html(num, is_block=False)
            den_html = cls._convert_latex_math_to_html(den, is_block=False)
            frac_html = f'<span class="fraction"><span class="num">{num_html}</span><span class="den">{den_html}</span></span>'
            clean = clean[:pos] + frac_html + clean[after_den:]
        return clean

    @classmethod
    def typeset_chemistry(cls, text: str) -> str:
        """Typesets chemical formulas, species, orbital hybridization, and bonds."""
        res = text

        # 1. Deduplicate redundant parenthetical definitions like "sigma bond (σ bond)"
        res = re.sub(r'\b(?:sigma|σ)[\s\-]*bond\s*\(\s*(?:[σ\\]*sigma|σ)[\s\-]*bond\s*\)', 'σ bond', res, flags=re.IGNORECASE)
        res = re.sub(r'\b(?:pi|π)[\s\-]*bond\s*\(\s*(?:[π\\]*pi|π)[\s\-]*bond\s*\)', 'π bond', res, flags=re.IGNORECASE)

        # 2. LaTeX commands with leading backslash in text
        res = re.sub(r'\\pi\b', 'π', res)
        res = re.sub(r'\\sigma\b', 'σ', res)

        # 3. Bonds: sigma / pi with strict phrasal boundaries (never touching English words like overlapping, spins, Raspberry Pi)
        res = re.sub(r'\bpi[\s\-]+bonds?\b', lambda m: 'π bonds' if 'bonds' in m.group(0).lower() else 'π bond', res, flags=re.IGNORECASE)
        res = re.sub(r'\bsigma[\s\-]+bonds?\b', lambda m: 'σ bonds' if 'bonds' in m.group(0).lower() else 'σ bond', res, flags=re.IGNORECASE)
        res = re.sub(r'\bpi[\s\-]+(electrons?|orbitals?|systems?|frameworks?|interactions?|backbones?)\b', r'π \1', res, flags=re.IGNORECASE)
        res = re.sub(r'\bsigma[\s\-]+(electrons?|orbitals?|frameworks?|overlaps?|backbones?)\b', r'σ \1', res, flags=re.IGNORECASE)

        # 4. Orbital hybridizations
        for pat, rep in cls.HYBRIDIZATIONS:
            res = re.sub(r'\b' + re.escape(pat) + r'\b', rep, res, flags=re.IGNORECASE)
        # Unicode superscript representations like sp², sp³, sp³d, sp³d²
        res = re.sub(r'\bsp²\b', 'sp<sup>2</sup>', res)
        res = re.sub(r'\bsp³\b', 'sp<sup>3</sup>', res)
        res = re.sub(r'\bsp³d\b', 'sp<sup>3</sup>d', res)
        res = re.sub(r'\bsp³d²\b', 'sp<sup>3</sup>d<sup>2</sup>', res)

        # 5. Known specific species with protected boundaries
        # Sulfate, phosphate, carbonate, etc.
        res = re.sub(r'\bSO4\^?\{?2\-?\}?', 'SO<sub>4</sub><sup>2−</sup>', res)
        res = re.sub(r'\bSO_4\^\{2\-\}', 'SO<sub>4</sub><sup>2−</sup>', res)
        res = re.sub(r'\bSO4\(2\-\)', 'SO<sub>4</sub><sup>2−</sup>', res)
        res = re.sub(r'\bPO4\^?\{?3\-?\}?', 'PO<sub>4</sub><sup>3−</sup>', res)
        res = re.sub(r'\bCO3\^?\{?2\-?\}?', 'CO<sub>3</sub><sup>2−</sup>', res)
        res = re.sub(r'\bNO3\^?\{?\-?\}?', 'NO<sub>3</sub><sup>−</sup>', res)
        res = re.sub(r'\bNH4\^?\{?\+?\}?', 'NH<sub>4</sub><sup>+</sup>', res)
        res = re.sub(r'\bH3O\^?\{?\+?\}?', 'H<sub>3</sub>O<sup>+</sup>', res)

        # Ions with negative lookbehind: P-Cl, C-Cl, H-Cl covalent bonds are strictly protected
        res = re.sub(r'(?<![A-Za-z]\-)\bCl(?:\^\{?[\-−]?\}?|<sup>[\-−]</sup>|[\-−](?!\w))', 'Cl<sup>−</sup>', res)
        res = re.sub(r'(?<![A-Za-z]\-)\bNa(?:\^\{?\+?\}?|<sup>\+</sup>|\+(?!\w))', 'Na<sup>+</sup>', res)
        res = re.sub(r'(?<![A-Za-z]\-)\bCa(?:\^\{?2\+?\}?|2\+(?!\w))', 'Ca<sup>2+</sup>', res)
        res = re.sub(r'(?<![A-Za-z]\-)\bMg(?:\^\{?2\+?\}?|2\+(?!\w))', 'Mg<sup>2+</sup>', res)
        res = re.sub(r'(?<![A-Za-z]\-)\bAl(?:\^\{?3\+?\}?|3\+(?!\w))', 'Al<sup>3+</sup>', res)

        # Common molecular formulas
        for pat, rep in cls.SPECIFIC_SPECIES:
            if pat.startswith((r'\bSO4', r'\bPO4', r'\bCO3', r'\bNO3', r'\bNH4', r'\bH3O', r'\bNa', r'\bCl', r'\bCa', r'\bMg', r'\bAl')):
                continue  # Handled above with protected boundary
            res = re.sub(pat, rep, res)

        # 6. Multi-element formulas like C6H6, BeCl2, BF3, CCl4, SF6, XeF4, etc.
        def sub_chem_species(m):
            s = m.group(0)
            if s.startswith(('sp', 'dsp', 'd2sp')):
                return s
            return re.sub(r'([A-Z][a-z]?)(\d+)', r'\1<sub>\2</sub>', s)

        res = re.sub(r'\b(?:[A-Z][a-z]?\d*){2,}\b', sub_chem_species, res)

        # 7. General inorganic single-element formula subscripting (e.g., O2, N2, H2, Cl2)
        def sub_element_digits(m):
            elem = m.group(1)
            digits = m.group(2)
            return f"{elem}<sub>{digits}</sub>"

        res = re.sub(r'\b([A-Z][a-z]?)([2-9]|1[0-9])\b', sub_element_digits, res)

        return res

    @classmethod
    def _convert_latex_math_to_html(cls, expr: str, is_block: bool = False) -> str:
        """Converts raw LaTeX math expression into high-fidelity semantic HTML."""
        clean = expr.strip()
        # Strip outer $$ or $ if present
        if clean.startswith("$$") and clean.endswith("$$"):
            clean = clean[2:-2].strip()
        elif clean.startswith("$") and clean.endswith("$"):
            clean = clean[1:-1].strip()

        # Clean LaTeX environments like aligned, matrix, pmatrix, cases
        clean = re.sub(r'\\begin\{(?:aligned|align\*?|matrix|pmatrix|bmatrix|cases)\}', '', clean)
        clean = re.sub(r'\\end\{(?:aligned|align\*?|matrix|pmatrix|bmatrix|cases)\}', '', clean)
        clean = clean.replace('&', '')
        clean = re.sub(r'\\\\\s*', '<br>', clean)

        # Handle \text{...}
        clean = re.sub(r'\\text\{([^}]+)\}', r'\1', clean)

        # Handle \frac{numerator}{denominator} with arbitrary nesting
        clean = cls.replace_latex_fractions(clean)

        # Handle square roots \sqrt{...}
        clean = re.sub(r'\\sqrt\{([^}]+)\}', r'√<span class="radicand">\1</span>', clean)

        # Greek symbols and operators
        for cmd, sym in cls.GREEK_MAP.items():
            clean = clean.replace(cmd, sym)
        for cmd, sym in cls.OPERATOR_MAP.items():
            clean = clean.replace(cmd, sym)

        # Superscripts ^{...} or ^x
        clean = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', clean)
        clean = re.sub(r'\^([0-9a-zA-Z+\-°])', r'<sup>\1</sup>', clean)

        # Subscripts _{...} or _x
        clean = re.sub(r'\_\{([^}]+)\}', r'<sub>\1</sub>', clean)
        clean = re.sub(r'\_([0-9a-zA-Z+\-])', r'<sub>\1</sub>', clean)

        # Remove remaining rogue LaTeX commands that might linger
        clean = re.sub(r'\\[a-zA-Z]+', '', clean)

        # Wrap in semantic math container
        if is_block:
            return f'<div class="math-block"><span class="equation-box">{clean}</span></div>'
        else:
            return f'<span class="math-inline">{clean}</span>'

    @classmethod
    def typeset_math(cls, text: str) -> str:
        """Finds block $$...$$ and inline $...$ expressions and converts them to semantic HTML."""
        # 1. Process block math $$ ... $$
        def block_repl(m):
            expr = m.group(1)
            return cls._convert_latex_math_to_html(expr, is_block=True)

        res = re.sub(r'\$\$(.*?)\$\$', block_repl, text, flags=re.DOTALL)

        # 2. Process inline math $ ... $ with strict currency defense ($50, $20 is never math)
        def inline_repl(m):
            content = m.group(1)
            # Currency check: if content starts with digits and contains no math operators or backslashes
            if re.match(r'^\d+(?:\.\d+)?(?:\s+(?:and|or|to|for|is|are|in)\s+)?', content) and not any(op in content for op in ('\\', '^', '_', '=', '+', '-', '*', '/', '<', '>', '±', '√', '≤', '≥', '≠')):
                return m.group(0)
            return cls._convert_latex_math_to_html(content, is_block=False)

        res = re.sub(r'(?<!\$)\$(?!\s)(.+?)(?<!\s)\$(?!\$)', inline_repl, res)

        # 3. Process un-bracketed \frac{...}{...} in prose
        if r'\frac' in res:
            res = cls.replace_latex_fractions(res)

        # 4. Process un-bracketed \text{...} in prose
        res = re.sub(r'\\text\{([^}]+)\}', r'\1', res)

        # 5. Process un-bracketed operators and Greek symbols in prose
        for cmd, sym in cls.OPERATOR_MAP.items():
            if cmd in res:
                res = res.replace(cmd, sym)
        for cmd, sym in cls.GREEK_MAP.items():
            if cmd in res:
                res = res.replace(cmd, sym)

        # 6. Process un-bracketed superscripts and subscripts in prose
        res = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', res)
        res = re.sub(r'\_\{([^}]+)\}', r'<sub>\1</sub>', res)
        res = re.sub(r'(?<=[a-zA-Z])\_([0-9a-zA-Z+\-])(?!\w)', r'<sub>\1</sub>', res)
        res = re.sub(r'(?<=[a-zA-Z0-9])\^([0-9a-zA-Z+\-°])(?!\w)', r'<sup>\1</sup>', res)

        return res

    @classmethod
    def typeset_formula(cls, formula: str) -> str:
        """
        Typesets an equation or formula string into print-ready semantic HTML
        with proper numerator/denominator fraction vertical alignment.
        """
        if not formula:
            return ""
        res = formula.strip()

        # 1. Process any LaTeX math expressions (block $$, inline $, \frac, backslashes, _, ^)
        if '$' in res or '\\' in res or r'\frac' in res or '_' in res or '^' in res:
            res = cls.typeset_math(res)

        # 2. Handle inline fractions like "= (Nb - Na) / 2" or "(N_b - N_a) / 2" or "A / B"
        def frac_repl(m):
            prefix = m.group(1) or ''
            num = m.group(2).strip('() ')
            den = m.group(3).strip('() ')
            # Clean minus inside numerator
            num_clean = num.replace(' - ', ' − ')
            num_clean = re.sub(r'([A-Za-z0-9_>])\s*-\s*([A-Za-z0-9_<])', r'\1 − \2', num_clean)
            # Handle bonding/antibonding electron notation: N_b, Nb, N_a, Na
            num_clean = re.sub(r'\bN_?b\b', 'N<sub>b</sub>', num_clean)
            num_clean = re.sub(r'\bN_?a\b', 'N<sub>a</sub>', num_clean)
            return f'{prefix}<span class="fraction"><span class="num">{num_clean}</span><span class="den">{den}</span></span>'

        res = re.sub(r'(=?\s*)\(([^()]+)\)\s*/\s*([0-9a-zA-Z_]+)', frac_repl, res)

        # 3. Handle bonding/antibonding electron notation strictly when written as N_b or N_a
        res = re.sub(r'\bN_b\b', 'N<sub>b</sub>', res)
        res = re.sub(r'\bN_a\b', 'N<sub>a</sub>', res)

        # 4. Typeset chemistry if chemical formulas are present
        res = cls.typeset_chemistry(res)

        return res

    @classmethod
    def typeset_markdown(cls, text: str) -> str:
        """Full pipeline: Markdown formatting + Semantic Math + Chemistry typesetting."""
        if not text:
            return ""

        # First typeset math expressions so inner markup isn't mangled by markdown
        res = cls.typeset_math(text)

        # Process explicit formula fraction expressions like "Bond Order = (N_b - N_a) / 2"
        if " / " in res or "/2" in res:
            def md_frac_repl(m):
                prefix = m.group(1) or ''
                num = m.group(2).strip('() ')
                den = m.group(3).strip('() ')
                num_clean = num.replace(' - ', ' − ')
                num_clean = re.sub(r'([A-Za-z0-9_>])\s*-\s*([A-Za-z0-9_<])', r'\1 − \2', num_clean)
                num_clean = re.sub(r'\bN_?b\b', 'N<sub>b</sub>', num_clean)
                num_clean = re.sub(r'\bN_?a\b', 'N<sub>a</sub>', num_clean)
                return f'{prefix}<span class="fraction"><span class="num">{num_clean}</span><span class="den">{den}</span></span>'

            res = re.sub(r'(=?\s*)\(([^()]+)\)\s*/\s*([0-9a-zA-Z_]+)', md_frac_repl, res)

        # Typeset chemistry notation
        res = cls.typeset_chemistry(res)

        # Typeset standalone math variables: N_b, N_a
        res = re.sub(r'\bN_b\b', 'N<sub>b</sub>', res)
        res = re.sub(r'\bN_a\b', 'N<sub>a</sub>', res)

        # Bold **text**
        res = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', res)

        # Italic *text* (avoiding inner subscripts)
        res = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', res)

        # Inline code `code`
        res = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', res)

        return res

