"""Maps Hindi (Devanagari), Hinglish and everyday wording to curriculum terms for Gate 2.

This is a curated glossary for the MVP topics, not general translation; a word outside it
is left as is, so an unknown query still falls through to the safe fallback.
"""
from __future__ import annotations

from typing import Iterable

STOPWORDS_HI = frozenset("""
क्या है हैं कैसे क्यों और का के की को से में मे पर यह वह मुझे समझाओ बताओ कीजिए करें होता होती
tha thi hota hoti karo kare kaise kya samjhana samjhaiye bataiye
""".split())

_GROUPS: dict[str, tuple[str, ...]] = {
    "equation": ("समीकरण", "samikaran", "sameekaran"),
    "linear": ("रैखिक", "रेखीय", "rekhik", "rekhiya", "raikhik"),
    "quadratic": ("द्विघात", "dwighat", "dvighat", "doghat"),
    "polynomial": ("बहुपद", "bahupad"),
    "discriminant": ("विविक्तकर", "vivikatkar", "viviktakar"),
    "root": ("मूल", "mool", "zero", "zeroes", "zeros", "solution"),
    "variable": ("चर", "unknown"),
    "motion": ("गति", "gati", "moving", "moves"),
    "speed": ("चाल", "fast", "chaal", "tez", "तेज"),
    "velocity": ("वेग", "veg"),
    "acceleration": ("त्वरण", "tvaran", "twaran", "speeding"),
    "distance": ("दूरी", "doori", "duri"),
    "displacement": ("विस्थापन", "visthapan"),
    "mirror": ("दर्पण", "darpan", "aaina", "आईना"),
    "lens": ("लेंस", "lense"),
    "refraction": ("अपवर्तन", "apvartan", "bending", "bend", "bends"),
    "reflection": ("परावर्तन", "paravartan", "bounce", "bounces"),
    "light": ("प्रकाश", "prakash", "roshni", "रोशनी"),
    "power": ("क्षमता", "kshamta"),
    "current": ("धारा", "dhara"),
    "voltage": ("विभवांतर", "विभव", "vibhav", "vibhavantar", "potential"),
    "resistance": ("प्रतिरोध", "pratirodh"),
    "electricity": ("विद्युत", "बिजली", "vidyut", "bijli"),
}
_TERM_MAP = {variant: canonical for canonical, variants in _GROUPS.items() for variant in variants}


def normalize_terms(tokens: Iterable[str]) -> list[str]:
    return [_TERM_MAP.get(token, token) for token in tokens]
