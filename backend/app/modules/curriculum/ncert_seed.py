"""Class 8-10 MVP concept content, written originally for Learn Genie.

Text is not copied from NCERT books. Citation ids point to the chapter that teaches the
idea (2023-24 rationalised numbering), and must be checked against the books in use.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Concept:
    concept_id: str
    class_level: int
    subject: str
    chapter: str
    title: str
    citation_id: str
    prerequisites: tuple[str, ...]
    siblings: tuple[str, ...]
    definition: str
    key_idea: str
    formula: str
    common_mistake: str
    keywords: tuple[str, ...]
    worked_problem: str
    worked_steps: tuple[str, ...]  # Equations for maths, formula lines for science.
    worked_notes: tuple[str, ...]
    socratic: tuple[str, ...]
    simulation: str
    extra_terms: tuple[str, ...] = field(default=())

    def card(self) -> dict[str, str]:
        """The five-block concept card."""
        return {
            "definition": self.definition,
            "key_idea": self.key_idea,
            "formula": self.formula,
            "worked_example": f"{self.worked_problem} " + " ; ".join(self.worked_steps),
            "common_mistake": self.common_mistake,
        }


CONCEPTS: tuple[Concept, ...] = (
    Concept(
        "m8_linear_one", 8, "Mathematics", "Linear Equations in One Variable",
        "Solving linear equations in one variable", "NCERT-C8-MATH-CH02-LINEAR-ONE-VARIABLE",
        (), ("m9_polynomials",),
        "A linear equation in one variable has a single unknown raised only to power 1, such as 3x + 2 = 11.",
        "Whatever you do to one side you must do to the other, so the balance is kept while the variable is isolated.",
        "ax + b = c gives x = (c - b)/a",
        "When a term crosses the equals sign its sign must change; forgetting this gives a sign slip.",
        ("balance", "variable", "isolate", "sides", "transpose"),
        "Solve 3x + 2 = 11.", ("3x + 2 = 11", "3x = 9", "x = 3"),
        ("Start with the given equation.", "Subtract 2 from both sides.", "Divide both sides by 3."),
        ("What single operation would remove the constant from the left side?",
         "What must you do to the right side to keep the balance?",
         "How can you check your value of x by substituting it back?"),
        "AlgebraStepBuilder", ("linear", "equation", "solve", "unknown"),
    ),
    Concept(
        "m9_polynomials", 9, "Mathematics", "Polynomials",
        "Polynomials and algebraic identities", "NCERT-C9-MATH-CH02-POLYNOMIALS",
        ("m8_linear_one",), ("m9_linear_two",),
        "A polynomial is a sum of terms with whole-number powers of a variable; its value at x = k is p(k).",
        "Identities such as (a + b)^2 hold for every value, so they turn long multiplication into a pattern.",
        "(a + b)^2 = a^2 + 2ab + b^2 and a^2 - b^2 = (a + b)(a - b)",
        "Writing (a + b)^2 as a^2 + b^2 drops the middle term 2ab.",
        ("terms", "degree", "identity", "expand", "value"),
        "Expand (x + 3)^2.", ("(x + 3)^2 = x^2 + 2*3*x + 3^2", "(x + 3)^2 = x^2 + 6x + 9"),
        ("Apply the square-of-a-sum identity.", "Simplify each term."),
        ("Which identity matches the shape of this expression?",
         "What is the middle term and where does it come from?",
         "How could you test your expansion with x = 1?"),
        "CoordinateGraphPlotter", ("polynomial", "polynomials", "identity", "identities", "algebra", "algebraic", "expression", "factor"),
    ),
    Concept(
        "m9_linear_two", 9, "Mathematics", "Linear Equations in Two Variables",
        "Linear equations in two variables", "NCERT-C9-MATH-CH04-LINEAR-TWO-VARIABLES",
        ("m8_linear_one",), ("m9_polynomials", "m10_pair_linear"),
        "An equation ax + by = c has many solutions; each solution is a pair (x, y) lying on a straight line.",
        "Fixing one variable turns the equation into a one-variable equation you already know how to solve.",
        "ax + by = c",
        "Substituting a value but forgetting its coefficient, such as replacing 2x with x's value alone.",
        ("solutions", "pair", "line", "graph", "substitute"),
        "Find y when x = 2 in 3x + 2y = 12.", ("3*2 + 2y = 12", "2y = 6", "y = 3"),
        ("Substitute x = 2.", "Subtract 6 from both sides.", "Divide both sides by 2."),
        ("What does one solution of this equation look like on a graph?",
         "How many solutions do you expect, and why?",
         "What happens to y as x increases?"),
        "CoordinateGraphPlotter", ("linear", "equation", "equations", "two", "variables", "graph"),
    ),
    Concept(
        "m10_pair_linear", 10, "Mathematics", "Pair of Linear Equations in Two Variables",
        "Solving a pair of linear equations", "NCERT-C10-MATH-CH03-PAIR-LINEAR",
        ("m9_linear_two",), ("m10_quadratic",),
        "A pair of linear equations shares one solution when their lines cross at a single point.",
        "Elimination adds or subtracts the equations so that one variable disappears.",
        "x + y = s and x - y = d give x = (s + d)/2",
        "Subtracting equations without changing the sign of every term in the second equation.",
        ("elimination", "substitution", "intersect", "consistent", "pair"),
        "Solve x + y = 7 and x - y = 3.", ("x + y + x - y = 7 + 3", "2x = 10", "x = 5"),
        ("Add the two equations.", "Simplify; y is eliminated.", "Divide both sides by 2."),
        ("Which variable is easiest to eliminate here, and why?",
         "What does your solution mean for the two lines on a graph?",
         "How would you check the pair of values in both equations?"),
        "CoordinateGraphPlotter", ("pair", "simultaneous", "elimination", "substitution", "linear", "equations"),
    ),
    Concept(
        "m10_quadratic", 10, "Mathematics", "Quadratic Equations",
        "Quadratic equations", "NCERT-C10-MATH-CH04-QUADRATIC",
        ("m9_polynomials", "m8_linear_one"), ("m10_pair_linear",),
        "A quadratic equation has the form ax^2 + bx + c = 0 with a not zero, and can have two, one or no real roots.",
        "The discriminant b^2 - 4ac decides how many real roots exist before you solve anything.",
        "x = (-b ± sqrt(b^2 - 4ac)) / 2a",
        "Taking only one root, or flipping signs when reading roots from factors: (x - 3) gives x = 3, not -3.",
        ("roots", "discriminant", "factorise", "formula", "real"),
        "Solve x^2 - 5x + 6 = 0.", ("x^2 - 5x + 6 = 0", "(x - 2)(x - 3) = 0"),
        ("Start with the given equation.", "Factorise; the roots are x = 2 and x = 3."),
        ("What two numbers multiply to give c and add to give b?",
         "What does the discriminant tell you before you begin?",
         "Why can a quadratic have two answers when a linear equation has one?"),
        "CoordinateGraphPlotter", ("quadratic", "roots", "discriminant", "factorisation", "factorization", "parabola"),
    ),
    Concept(
        "s9_motion", 9, "Science", "Motion", "Speed, velocity and displacement",
        "NCERT-C9-SCI-CH07-MOTION-DESCRIBING",
        (), ("s9_eq_motion",),
        "Distance is the path length; displacement is the straight-line change in position with direction.",
        "Speed uses distance but velocity uses displacement, so a round trip has zero average velocity.",
        "speed = distance / time ; velocity = displacement / time",
        "Treating distance and displacement as the same when the path is not straight.",
        ("distance", "displacement", "speed", "velocity", "direction"),
        "A car travels 100 m in 20 s. Find its speed.", ("s = 100/20", "s = 5"),
        ("Use speed = distance / time.", "Divide: the speed is 5 m/s."),
        ("Is the path here a straight line? Why does that matter?",
         "What would a round trip do to the displacement?",
         "How would you draw this motion on a distance-time graph?"),
        "CoordinateGraphPlotter", ("motion", "speed", "velocity", "distance", "displacement", "time"),
    ),
    Concept(
        "s9_eq_motion", 9, "Science", "Motion", "Equations of uniformly accelerated motion",
        "NCERT-C9-SCI-CH07-MOTION-EQUATIONS",
        ("s9_motion", "m8_linear_one"), ("s9_motion",),
        "Uniform acceleration means velocity changes by equal amounts in equal time intervals.",
        "Three equations link u, v, a, s and t; pick the one that contains your unknown and your known values.",
        "v = u + at ; s = ut + (1/2)at^2 ; v^2 = u^2 + 2as",
        "Forgetting the 1/2 in s = ut + (1/2)at^2.",
        ("acceleration", "uniform", "initial", "final", "equations"),
        "A bike starts at u = 2 m/s and accelerates at a = 3 m/s^2 for t = 4 s. Find v.",
        ("v = 2 + 3*4", "v = 14"),
        ("Use v = u + at.", "Calculate: the final velocity is 14 m/s."),
        ("Which quantities are known, and which is unknown?",
         "Which equation contains exactly those quantities?",
         "What would a negative acceleration mean here?"),
        "CoordinateGraphPlotter", ("acceleration", "accelerated", "equations", "motion", "kinematics"),
    ),
    Concept(
        "s10_mirrors", 10, "Science", "Light: Reflection and Refraction", "Spherical mirrors",
        "NCERT-C10-SCI-CH09-LIGHT-MIRRORS",
        ("m8_linear_one",), ("s10_lenses",),
        "A spherical mirror is part of a reflecting sphere; concave mirrors converge light and convex mirrors diverge it.",
        "Measure every distance from the pole using the sign convention, then apply the mirror formula.",
        "1/v + 1/u = 1/f ; R = 2f ; m = -v/u",
        "Dropping the negative sign of an object distance measured against the incident light.",
        ("pole", "focus", "concave", "convex", "sign"),
        "An object is at u = -30 cm from a concave mirror with f = -15 cm. Find v.",
        ("1/v = 1/(-15) - 1/(-30)", "1/v = -1/30", "v = -30"),
        ("Rearrange the mirror formula.", "Combine the fractions.", "Invert: the image is 30 cm in front."),
        ("Where does the incident light come from, and what sign does that give u?",
         "Which sign does f take for a concave mirror?",
         "What does a negative v tell you about the image?"),
        "RayOpticsBench", ("mirror", "mirrors", "reflection", "concave", "convex", "focal", "optics", "image"),
    ),
    Concept(
        "s10_lenses", 10, "Science", "Light: Reflection and Refraction", "Refraction and lenses",
        "NCERT-C10-SCI-CH09-LIGHT-REFRACTION",
        ("s10_mirrors",), ("s10_mirrors",),
        "Refraction is the bending of light as it changes speed between media; a lens uses it to form images.",
        "Refractive index compares speeds; lens power is the reciprocal of focal length in metres.",
        "n = c / v ; 1/v - 1/u = 1/f ; P = 1/f",
        "Using the mirror formula's plus sign for a lens, or f in centimetres when finding power.",
        ("refractive", "index", "lens", "power", "bending"),
        "A lens has focal length f = 0.5 m. Find its power.", ("P = 1/0.5", "P = 2"),
        ("Use P = 1/f with f in metres.", "Calculate: the power is 2 dioptre."),
        ("Why does light bend when its speed changes?",
         "What unit must f be in before finding power?",
         "How does the lens formula differ from the mirror formula?"),
        "RayOpticsBench", ("refraction", "lens", "lenses", "refractive", "power", "optics", "light", "dioptre"),
    ),
    Concept(
        "s10_ohms", 10, "Science", "Electricity", "Ohm's law",
        "NCERT-C10-SCI-CH11-ELECTRICITY-OHMS-LAW",
        ("m8_linear_one",), ("s10_lenses",),
        "Ohm's law says the current through a conductor is proportional to the potential difference across it at constant temperature.",
        "Resistance is the constant ratio V/I, so a graph of V against I is a straight line through the origin.",
        "V = I*R",
        "Rearranging incorrectly, for example I = V*R instead of I = V/R.",
        ("current", "voltage", "resistance", "proportional", "conductor"),
        "Find the current when V = 12 V and R = 4 ohm.", ("I = 12/4", "I = 3"),
        ("Rearrange V = IR to I = V/R.", "Calculate: the current is 3 A."),
        ("If voltage doubles at fixed resistance, what happens to current?",
         "What does the slope of a V-I graph represent?",
         "Which quantity are you solving for?"),
        "VirtualScienceLab", ("ohm", "ohms", "current", "voltage", "resistance", "electricity", "circuit"),
    ),
)

CONCEPTS_BY_ID = {concept.concept_id: concept for concept in CONCEPTS}
PREREQUISITES = {c.concept_id: c.prerequisites for c in CONCEPTS}


def concepts_for_class(student_class: int, subject: str | None = None) -> list[Concept]:
    return [
        c for c in CONCEPTS
        if c.class_level <= student_class and (subject is None or c.subject == subject)
    ]


def build_chunks() -> list[dict[str, object]]:
    """One retrievable chunk per concept-card block, each carrying its citation."""
    chunks: list[dict[str, object]] = []
    for concept in CONCEPTS:
        for block, text in concept.card().items():
            chunks.append({
                "chunk_id": f"{concept.concept_id}:{block}",
                "concept_id": concept.concept_id,
                "class_level": concept.class_level,
                "subject": concept.subject,
                "citation_id": concept.citation_id,
                "title": concept.title,
                "block": block,
                "text": text,
                "search_terms": " ".join(concept.keywords + concept.extra_terms),
            })
    return chunks
