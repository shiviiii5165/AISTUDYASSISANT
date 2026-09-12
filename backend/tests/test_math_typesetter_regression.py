"""
Regression tests for math typesetter defects:
- Raw LaTeX delimiters ($ and $$) leaking into student text
- Raw LaTeX commands (\\frac, \\text, \\sqrt, \\quad, \\neq) leaking into student text
- Formula box typesetting for inline LaTeX formulas
- Preservation of currency ($50, $20)
"""
import pytest
from app.services.notes.rendering.typesetter import SemanticTypesetter
from app.services.notes.certification.latex_scanner import RawLatexScanner


@pytest.mark.parametrize("input_str", [
    r"Standard Form: $ax^2 + bx + c = 0 \quad (a \neq 0)$",
    r"Discriminant ($D$): $D = b^2 - 4ac$",
    r"If $D < 0$: No real roots",
    r"$ax^2 + bx + c = 0$",
    r"$D = b^2 - 4ac$",
    r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \text{ and } x = -",
    r"F_{net} = m \cdot a",
    r"Bond Order = (N_b - N_a) / 2",
    r"Standard Form: $ax^2 + bx + c = 0 \qquad (a \ne 0)$",
    r"Roots: $x_1 \le x_2$",
    r"Newton's Second Law: F_{net} = m · a = dp/dt",
    r"Impulse-Momentum Theorem: J = F_{avg} · Δt = Δp",
    r"Maximum Static Friction: f_{s,max} = μ_s · N",
    r"Kinetic Friction: f_k = μ_k · N",
])
def test_typeset_formula_zero_defects(input_str: str):
    rendered = SemanticTypesetter.typeset_formula(input_str)
    defects = RawLatexScanner.scan_text(rendered)
    assert not defects, f"Defects detected in typeset_formula('{input_str}'): {[d.message for d in defects]}"


@pytest.mark.parametrize("input_str", [
    r"Standard Form: $ax^2 + bx + c = 0 \quad (a \neq 0)$",
    r"Discriminant ($D$): $D = b^2 - 4ac$",
    r"If $D < 0$: No real roots",
    r"$ax^2 + bx + c = 0$",
    r"$D = b^2 - 4ac$",
    r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \text{ and } x = -",
    r"Here is a formula: $D = b^2 - 4ac$ inside prose.",
])
def test_typeset_markdown_math_zero_defects(input_str: str):
    rendered = SemanticTypesetter.typeset_markdown(input_str)
    defects = RawLatexScanner.scan_text(rendered)
    assert not defects, f"Defects detected in typeset_markdown('{input_str}'): {[d.message for d in defects]}"


def test_currency_not_treated_as_math():
    text = "The textbook costs $50 and the notebook costs $20."
    rendered = SemanticTypesetter.typeset_markdown(text)
    assert "$50" in rendered
    assert "$20" in rendered
    assert "class=\"math-inline\"" not in rendered
