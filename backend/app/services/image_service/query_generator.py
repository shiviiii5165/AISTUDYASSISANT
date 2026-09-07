"""
Image Service — Query Generator
=================================
Builds effective photographic search queries from slide content.
Strips non-photographic academic terms and appends scene/object modifiers
for better stock photo matches.
"""
import re
from typing import Dict, Any, Optional


# Terms that don't help find good stock photos
NON_PHOTOGRAPHIC_TERMS = {
    "algorithm", "theorem", "overview", "introduction", "conclusion",
    "summary", "analysis", "methodology", "approach", "framework",
    "paradigm", "architecture", "implementation", "specification",
    "abstraction", "encapsulation", "polymorphism", "inheritance",
    "interface", "module", "component", "function", "variable",
    "constant", "parameter", "argument", "class", "object",
    "method", "property", "attribute", "instance", "constructor",
    "destructor", "operator", "expression", "statement", "loop",
    "condition", "recursion", "iteration", "enumeration", "type",
    "syntax", "semantics", "compilation", "runtime", "debugging",
    "testing", "optimization", "complexity", "efficiency", "scalability",
    "review", "assessment", "evaluation", "objectives", "outcomes",
    "prerequisites", "references", "bibliography", "appendix",
    "chapter", "section", "subsection", "slide", "presentation",
    "lecture", "tutorial", "workshop", "seminar", "unit",
    "key takeaways", "learning objectives", "quiz", "exercise",
}

# Scene modifiers that improve stock photo search quality
TOPIC_MODIFIERS = {
    "technology": "technology office workspace",
    "science": "science laboratory research",
    "business": "business professional meeting",
    "education": "education classroom learning",
    "medical": "medical healthcare hospital",
    "engineering": "engineering construction blueprint",
    "environment": "environment nature sustainability",
    "finance": "finance charts trading",
    "art": "art creative studio",
    "history": "history historical archive",
    "law": "law justice courthouse",
    "psychology": "psychology brain mind",
    "sports": "sports athlete competition",
    "food": "food cuisine cooking",
    "travel": "travel destination landscape",
    "music": "music instruments performance",
}


class QueryGenerator:
    """
    Generates effective photographic search queries from slide content.
    Combines slide title, key_message, and example text into a search-optimized query.
    """

    @staticmethod
    def generate_query(slide_dict: Dict[str, Any], topic: str = "") -> str:
        """
        Build a photographic search query from slide content.

        Priority sources (in order):
        1. Explicit image_query from content agent (already optimized)
        2. key_message text (most descriptive)
        3. Title + example text combination
        4. First body bullet as fallback

        Args:
            slide_dict: The slide dictionary with content fields
            topic: The overall presentation topic (for context)

        Returns:
            A clean, photographic search query string
        """
        # 1. Use existing image_query if available (content agent already generated it)
        image_query = (slide_dict.get("image_query") or "").strip()
        if image_query and len(image_query) > 5:
            return QueryGenerator._clean_query(image_query)

        # 2. Build from key_message
        key_message = (slide_dict.get("key_message") or "").strip()
        if key_message and len(key_message) > 10:
            cleaned = QueryGenerator._extract_photographic_terms(key_message)
            if cleaned:
                return cleaned

        # 3. Build from title + example
        title = (slide_dict.get("title") or "").strip()
        example = (slide_dict.get("example") or "").strip()

        parts = []
        if title:
            cleaned_title = QueryGenerator._extract_photographic_terms(title)
            if cleaned_title:
                parts.append(cleaned_title)

        if example and len(example) > 10:
            # Extract concrete nouns from the example
            cleaned_example = QueryGenerator._extract_photographic_terms(example[:100])
            if cleaned_example:
                parts.append(cleaned_example)

        if parts:
            return " ".join(parts)[:80]

        # 4. Fallback to first body bullet
        bullets = slide_dict.get("body_bullets", [])
        if bullets and bullets[0]:
            cleaned = QueryGenerator._extract_photographic_terms(str(bullets[0]))
            if cleaned:
                return cleaned

        # 5. Last resort: use topic
        if topic:
            return QueryGenerator._clean_query(topic)

        return title or "education learning"

    @staticmethod
    def _extract_photographic_terms(text: str) -> str:
        """Remove academic/abstract terms and keep concrete/visual words."""
        # Remove special characters but keep spaces
        clean = re.sub(r"[^\w\s-]", " ", text.lower())
        words = clean.split()

        # Filter out non-photographic terms and very short words
        visual_words = [
            w for w in words
            if len(w) > 2
            and w not in NON_PHOTOGRAPHIC_TERMS
            and not w.isdigit()
        ]

        # Limit to 6 most meaningful words
        result = " ".join(visual_words[:6])
        return result if len(result) > 3 else ""

    @staticmethod
    def _clean_query(query: str) -> str:
        """Clean and normalize a search query."""
        # Remove non-photographic qualifier words
        clean = re.sub(r"[^\w\s-]", " ", query.lower())
        words = clean.split()
        cleaned = [w for w in words if len(w) > 2 and w not in NON_PHOTOGRAPHIC_TERMS]
        return " ".join(cleaned[:8]) if cleaned else query[:50]

    @staticmethod
    def get_modifier(topic: str) -> Optional[str]:
        """Get a scene modifier for the overall topic category."""
        topic_lower = topic.lower()
        for category, modifier in TOPIC_MODIFIERS.items():
            if category in topic_lower:
                return modifier
        return None
