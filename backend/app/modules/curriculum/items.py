"""Generated free-response item bank.

Items are computed from templates, so each answer is correct by construction, and free
response means c = 0 (no guessing floor). The b values are PROVISIONAL difficulty
estimates per template, not calibrated parameters. `traps` map a known wrong value to the
misconception that produces it, which lets the classifier name it without an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from itertools import product
from typing import Callable, Iterator

from app.modules.learning_core.irt import IRTItem

PER_TEMPLATE = 40


@dataclass(frozen=True)
class Item:
    item_id: str
    concept_id: str
    prompt: str
    answer: str
    unit: str
    b: float
    start_equation: str = ""
    traps: dict[str, str] = field(default_factory=dict)

    @property
    def irt(self) -> IRTItem:
        return IRTItem(self.item_id, b=self.b, a=1.2, c=0.0)

    def public_view(self) -> dict[str, object]:
        """What a student may see; never includes the answer or traps."""
        return {
            "item_id": self.item_id,
            "concept_id": self.concept_id,
            "prompt": self.prompt,
            "unit": self.unit,
            "start_equation": self.start_equation,
        }


def _num(value: Fraction | int | float) -> str:
    fraction = Fraction(value).limit_denominator(100000)
    if fraction.denominator == 1:
        return str(fraction.numerator)
    return f"{fraction.numerator}/{fraction.denominator}"


Row = tuple[str, Fraction | int, str, dict[str, Fraction | int | float], str]


def _linear_one() -> Iterator[tuple[float, Callable[[], Iterator[Row]]]]:
    def easy():
        for a, x in product(range(2, 12), range(1, 12)):
            eq = f"x + {a} = {a + x}"
            yield f"Solve {eq}.", x, "", {-x: "E07", a + (a + x): "E07"}, eq

    def mid():
        for a, b, x in product(range(2, 7), range(1, 6), range(2, 8)):
            eq = f"{a}x + {b} = {a * x + b}"
            trap = {Fraction(a * x + 2 * b, a): "E07"}
            yield f"Solve {eq}.", x, "", trap, eq

    def hard():
        for a, c, b, x in product(range(5, 9), range(2, 5), range(1, 4), range(2, 5)):
            d = (a - c) * x + b
            eq = f"{a}x + {b} = {c}x + {d}"
            yield f"Solve {eq}.", x, "", {Fraction(d - b, a + c): "E07"}, eq

    return iter([(-1.5, easy), (-0.6, mid), (0.3, hard)])


def _polynomials():
    def easy():
        for a, b, k in product(range(2, 6), range(1, 7), range(1, 6)):
            value = a * k + b
            yield f"Find p({k}) when p(x) = {a}x + {b}.", value, "", {}, ""

    def mid():
        for a, x in product(range(1, 10), range(1, 8)):
            yield (f"Using (x + {a})^2 = x^2 + 2({a})x + {a}^2, find the value when x = {x}.",
                   (x + a) ** 2, "", {x * x + a * a: "E04"}, "")

    def hard():
        for a, b in product(range(11, 31), range(1, 9)):
            yield (f"Use a^2 - b^2 = (a + b)(a - b) to find {a}^2 - {b}^2.",
                   a * a - b * b, "", {(a - b) ** 2: "E03"}, "")

    return iter([(-1.0, easy), (0.0, mid), (0.8, hard)])


def _linear_two():
    def easy():
        for b, x, y in product(range(1, 5), range(1, 8), range(1, 8)):
            c = x + b * y
            yield f"In x + {b}y = {c}, find y when x = {x}.", y, "", {}, f"{x} + {b}y = {c}"

    def mid():
        for a, b, x, y in product(range(2, 5), range(2, 5), range(1, 5), range(1, 5)):
            c = a * x + b * y
            yield (f"In {a}x + {b}y = {c}, find y when x = {x}.", y, "",
                   {Fraction(c - x, b): "E05"}, f"{a}*{x} + {b}y = {c}")

    def hard():
        for a, b, x, y in product(range(3, 7), range(2, 6), range(-3, 0), range(2, 6)):
            c = a * x + b * y
            yield (f"In {a}x + {b}y = {c}, find y when x = {x}.", y, "",
                   {Fraction(c + a * x, b): "E07"}, f"{a}*({x}) + {b}y = {c}")

    return iter([(-0.8, easy), (0.1, mid), (0.9, hard)])


def _pair_linear():
    def easy():
        for x, y in product(range(2, 12), range(1, 9)):
            yield (f"Solve x + y = {x + y} and x - y = {x - y}. Find x.", x, "",
                   {y: "E09"}, f"x + y + x - y = {x + y} + {x - y}")

    def mid():
        for a, x, y in product(range(2, 6), range(1, 8), range(1, 6)):
            yield (f"Solve {a}x + y = {a * x + y} and x + y = {x + y}. Find x.", x, "",
                   {y: "E09"}, "")

    def hard():
        for a, b, x, y in product(range(2, 5), range(2, 5), range(1, 6), range(1, 6)):
            if a == b:
                continue
            yield (f"Solve {a}x + {b}y = {a * x + b * y} and {b}x + {a}y = {b * x + a * y}. Find x + y.",
                   x + y, "", {}, "")

    return iter([(-0.2, easy), (0.5, mid), (1.3, hard)])


def _quadratic():
    def easy():
        for a, b, c in product(range(1, 5), range(1, 9), range(1, 6)):
            yield (f"Find the discriminant of {a}x^2 + {b}x + {c} = 0.", b * b - 4 * a * c, "",
                   {b * b + 4 * a * c: "E07", b - 4 * a * c: "E04"}, "")

    def mid():
        for r, s in product(range(1, 10), range(1, 10)):
            if r >= s:
                continue
            yield (f"Find the larger root of (x - {r})(x - {s}) = 0.", s, "",
                   {r: "E10", -s: "E07"}, "")

    def hard():
        for r, s in product(range(1, 10), range(1, 10)):
            if r >= s:
                continue
            yield (f"Find the larger root of x^2 - {r + s}x + {r * s} = 0.", s, "",
                   {r: "E10", -s: "E07"}, f"x^2 - {r + s}x + {r * s} = 0")

    return iter([(0.0, easy), (0.6, mid), (1.3, hard)])


def _motion():
    def easy():
        for v, t in product(range(2, 20), range(2, 12)):
            yield (f"A runner covers {v * t} m in {t} s. Find the speed.", v, "m/s",
                   {v * t * t: "E03"}, "")

    def mid():
        for d, t in product(range(10, 60, 5), range(2, 12)):
            yield (f"A cyclist rides {d} m east and {d} m back in {t} s. Find the average velocity.",
                   0, "m/s", {Fraction(2 * d, t): "E01"}, "")

    def hard():
        for d1, d2, t in product(range(30, 80, 10), range(10, 30, 5), range(2, 8)):
            yield (f"A car goes {d1} m east, then {d2} m west, in {t} s. Find the average velocity eastward.",
                   Fraction(d1 - d2, t), "m/s", {Fraction(d1 + d2, t): "E01"}, "")

    return iter([(-0.8, easy), (0.2, mid), (1.0, hard)])


def _eq_motion():
    def easy():
        for u, a, t in product(range(0, 6), range(1, 5), range(2, 7)):
            yield (f"Find v when u = {u} m/s, a = {a} m/s^2 and t = {t} s.", u + a * t, "m/s",
                   {u - a * t: "E07"}, "")

    def mid():
        for u, v, t in product(range(0, 5), range(10, 20, 2), (2, 4)):
            yield (f"A body speeds up from {u} m/s to {v} m/s in {t} s. Find the acceleration.",
                   Fraction(v - u, t), "m/s^2", {Fraction(v + u, t): "E07"}, "")

    def hard():
        for u, a, t in product(range(0, 6), (2, 4, 6), range(2, 7)):
            yield (f"Find s when u = {u} m/s, a = {a} m/s^2 and t = {t} s.",
                   u * t + Fraction(a * t * t, 2), "m", {u * t + a * t * t: "E04"}, "")

    return iter([(-0.2, easy), (0.4, mid), (1.1, hard)])


def _mirrors():
    def easy():
        for f in range(5, 50):
            yield (f"A spherical mirror has focal length {f} cm in magnitude. Find its radius of curvature in magnitude.",
                   2 * f, "cm", {Fraction(f, 2): "E03"}, "")

    def mid():
        for v, u in product(range(10, 50, 5), range(5, 45, 5)):
            yield (f"For a mirror, v = {v} cm and u = -{u} cm. Find the magnification m = -v/u.",
                   Fraction(v, u), "", {-Fraction(v, u): "E07"}, "")

    def hard():
        for f, k in product(range(5, 45, 5), (2, 3, 4, 5, 6)):
            u, value = k * f, Fraction(k * f, k - 1)
            yield (f"A concave mirror has f = -{f} cm. An object is at u = -{u} cm. Find v.",
                   -value, "cm", {value: "E07"}, "")

    return iter([(-1.0, easy), (0.3, mid), (1.4, hard)])


def _lenses():
    def easy():
        for f in (5, 10, 20, 25, 50, 100, 200):
            for scale in range(1, 7):
                yield (f"A lens has focal length {f * scale} cm. Find its power in dioptre.",
                       Fraction(100, f * scale), "D", {Fraction(1, f * scale): "E12"}, "")

    def mid():
        for v in (1.0, 1.25, 1.5, 2.0, 2.4):
            for k in range(1, 9):
                yield (f"Light travels at {v * k}x10^8 m/s in medium A and {v}x10^8 m/s in medium B. "
                       f"Find the refractive index of B with respect to A.", k, "",
                       {Fraction(1, k): "E03"}, "")

    def hard():
        for f, k in product(range(5, 45, 5), (2, 3, 4, 5, 6)):
            u, value = k * f, Fraction(k * f, k - 1)
            yield (f"A convex lens has f = {f} cm. An object is at u = -{u} cm. Find v.",
                   value, "cm", {-value: "E07"}, "")

    return iter([(-0.4, easy), (0.1, mid), (1.3, hard)])


def _ohms():
    def easy():
        for i, r in product(range(1, 9), range(2, 12)):
            yield f"Find V when I = {i} A and R = {r} ohm.", i * r, "V", {Fraction(i, r): "E06"}, ""

    def mid():
        for v, r in product(range(6, 36, 3), (2, 3, 4, 5, 6)):
            yield (f"Find I when V = {v} V and R = {r} ohm.", Fraction(v, r), "A",
                   {v * r: "E06"}, "")

    def hard():
        for v, r1, r2 in product((12, 24, 36), (2, 4, 6), (1, 2, 3, 4, 6)):
            yield (f"Two resistors of {r1} ohm and {r2} ohm are in series across {v} V. Find the current.",
                   Fraction(v, r1 + r2), "A", {Fraction(v, r1): "E01"}, "")

    return iter([(-1.2, easy), (-0.2, mid), (0.9, hard)])


_FAMILIES = {
    "m8_linear_one": _linear_one,
    "m9_polynomials": _polynomials,
    "m9_linear_two": _linear_two,
    "m10_pair_linear": _pair_linear,
    "m10_quadratic": _quadratic,
    "s9_motion": _motion,
    "s9_eq_motion": _eq_motion,
    "s10_mirrors": _mirrors,
    "s10_lenses": _lenses,
    "s10_ohms": _ohms,
}


@lru_cache(maxsize=1)
def all_items() -> tuple[Item, ...]:
    items: list[Item] = []
    for concept_id, family in _FAMILIES.items():
        for level, (b, template) in enumerate(family()):
            seen: set[str] = set()
            for prompt, answer, unit, traps, start in template():
                if prompt in seen or len(seen) >= PER_TEMPLATE:
                    continue
                seen.add(prompt)
                items.append(Item(
                    item_id=f"{concept_id}.L{level}.{len(seen):03d}",
                    concept_id=concept_id,
                    prompt=prompt,
                    answer=_num(answer),
                    unit=unit,
                    b=b + 0.01 * (len(seen) % 21 - 10),  # Avoid ties during selection.
                    start_equation=start,
                    traps={_num(k): v for k, v in traps.items() if _num(k) != _num(answer)},
                ))
    return tuple(items)


@lru_cache(maxsize=1)
def _by_id() -> dict[str, Item]:
    return {item.item_id: item for item in all_items()}


def get_item(item_id: str) -> Item | None:
    return _by_id().get(item_id)


def items_for(concept_id: str) -> list[Item]:
    return [item for item in all_items() if item.concept_id == concept_id]
