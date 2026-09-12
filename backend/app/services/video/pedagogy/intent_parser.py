"""
Learning Intent Parser
======================
Extracts structured pedagogical parameters from natural language prompts:
- Topic name (cleaned of command syntax)
- Learner Level (Class 9-12, B.Tech, Undergrad, Graduate, Beginner)
- Target Language (English, Hindi, Hinglish)
- Duration (in seconds, e.g. "7 minutes" -> 420s)
- Explanation Depth ("overview", "normal", "deep_dive")
- Inferred Domain
"""
import re
from typing import Optional, Dict, Any
from ..schemas import LearningIntent, DomainCategory
from .domain_intelligence import DomainIntelligenceEngine


class LearningIntentParser:
    """Parses arbitrary user requests into strict LearningIntent."""

    @classmethod
    def parse(cls, prompt: str, default_duration: int = 300) -> LearningIntent:
        text = prompt.strip()
        lower = text.lower()

        # 1. Detect Duration
        duration_sec = default_duration
        dur_match = re.search(r'(\d+)\s*(?:minutes?|mins?|m\b)', lower)
        if dur_match:
            duration_sec = min(900, max(60, int(dur_match.group(1)) * 60))
        elif "1 minute" in lower or "1 min" in lower:
            duration_sec = 60
        elif "3 minute" in lower or "3 min" in lower:
            duration_sec = 180
        elif "5 minute" in lower or "5 min" in lower:
            duration_sec = 300
        elif "7 minute" in lower or "7 min" in lower:
            duration_sec = 420
        elif "10 minute" in lower or "10 min" in lower:
            duration_sec = 600
        elif "15 minute" in lower or "15 min" in lower:
            duration_sec = 900

        # 2. Detect Language
        language = "english"
        if "in hindi" in lower or re.search(r'\bhindi\b', lower):
            language = "hindi"
        elif "in hinglish" in lower or re.search(r'\bhinglish\b', lower):
            language = "hinglish"
        elif "in english" in lower or re.search(r'\benglish\b', lower):
            language = "english"
        elif any(w in lower for w in ("bhai", "smjha", "samjhao", "karo", "kyu", "kyun", "hoti", "hota", "hai", "kaise", "batana", "seekhna")):
            language = "hinglish"

        # 3. Detect Learner Level
        level = "B.Tech"
        if re.search(r'\bclass\s*9\b|\b9th\b', lower):
            level = "Class 9"
        elif re.search(r'\bclass\s*10\b|\b10th\b', lower):
            level = "Class 10"
        elif re.search(r'\bclass\s*11\b|\b11th\b', lower):
            level = "Class 11"
        elif re.search(r'\bclass\s*12\b|\b12th\b', lower):
            level = "Class 12"
        elif "b.tech" in lower or "btech" in lower or "engineering" in lower or "cs" in lower:
            level = "B.Tech"
        elif "first-year" in lower or "first year" in lower or "freshman" in lower:
            level = "first-year university student"
        elif "graduate" in lower or "masters" in lower or "phd" in lower:
            level = "Graduate"
        elif "undergrad" in lower or "college" in lower or "university" in lower:
            level = "Undergrad"
        elif "beginner" in lower or "basics" in lower or "from scratch" in lower:
            level = "Beginner"

        # 4. Detect Depth
        depth = "normal"
        if "deep dive" in lower or "in depth" in lower or "advanced" in lower or "thorough" in lower:
            depth = "deep_dive"
        elif "overview" in lower or "quick" in lower or "summary" in lower or "brief" in lower:
            depth = "overview"

        # 5. Extract Core Topic
        # Strip common prefixes and suffix command phrases
        topic_clean = text
        prefixes_to_strip = [
            r'^(?:please\s+)?teach\s+me\s+about\s+',
            r'^(?:please\s+)?teach\s+',
            r'^(?:please\s+)?explain\s+',
            r'^(?:please\s+)?make\s+a\s+video\s+on\s+',
            r'^(?:please\s+)?create\s+a\s+video\s+about\s+',
            r'^(?:please\s+)?generate\s+a\s+video\s+on\s+',
            r'^(?:what\s+is\s+)',
            r'^(?:how\s+does\s+)',
        ]
        for p in prefixes_to_strip:
            topic_clean = re.sub(p, '', topic_clean, flags=re.IGNORECASE)

        # Strip suffixes like "to a B.Tech beginner in Hinglish in 7 minutes"
        suffixes_to_strip = [
            r'\s+to\s+(?:a\s+)?(?:first-year|first\s+year|university|college|b\.?tech|beginner|class\s*\d+|student|undergrad|engineering).*$',
            r'\s+in\s+(?:hinglish|hindi|english).*$',
            r'\s+in\s+\d+\s*(?:minutes?|mins?|m).*$',
            r'\s+from\s+basics.*$',
            r'\s+with\s+examples.*$',
            r'\s+for\s+(?:beginners?|class\s*\d+|b\.?tech).*$'
        ]
        for s in suffixes_to_strip:
            topic_clean = re.sub(s, '', topic_clean, flags=re.IGNORECASE)

        topic_clean = topic_clean.strip(" .?!,")
        if not topic_clean:
            topic_clean = text.strip()

        # 6. Detect Domain
        domain, _ = DomainIntelligenceEngine.detect_domain(topic_clean, text)

        return LearningIntent(
            raw_prompt=prompt,
            topic=topic_clean,
            domain=domain,
            learner_level=level,
            language=language,
            duration_seconds=duration_sec,
            explanation_depth=depth,
        )
