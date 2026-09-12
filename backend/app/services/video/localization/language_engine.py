"""
Language Teaching & Multilingual Localization Engine
===================================================
Preserves technical terms, code identifiers, formulas, and variable names
across English, Hindi, and Hinglish educational narration.
Ensures mixed-language phonetics are clean for neural speech synthesis.
"""
import re
from typing import Dict, Set, List
from ..schemas import DomainCategory


# Subject-specific protected terms that must NEVER be translated
TECHNICAL_GLOSSARIES: Dict[str, Set[str]] = {
    "computer_science": {
        "pointer", "pointers", "node", "nodes", "head", "tail", "next", "prev",
        "stack", "queue", "push", "pop", "enqueue", "dequeue", "tree", "binary tree",
        "graph", "hash table", "hash map", "array", "arrays", "linked list", "linked lists",
        "heap", "traversal", "recursion", "normalization", "1nf", "2nf", "3nf", "bcnf",
        "primary key", "foreign key", "join", "joins", "transaction", "deadlock",
        "cpu scheduling", "gantt chart", "process", "thread", "virtual memory",
        "malloc", "free", "null", "nullptr", "struct", "class", "object", "interface",
        "time complexity", "space complexity", "big o", "o(1)", "o(n)", "o(log n)"
    },
    "mathematics": {
        "derivative", "derivatives", "integration", "integral", "integrals", "limit",
        "limits", "dx", "dy", "du", "dv", "matrix", "matrices", "determinant",
        "eigenvalue", "eigenvector", "vector", "scalar", "probability", "bayes",
        "liate", "substitution", "chain rule", "product rule", "quotient rule",
        "sine", "cosine", "tangent", "polynomial", "quadratic", "slope"
    },
    "physics": {
        "force", "mass", "acceleration", "f = ma", "momentum", "velocity", "friction",
        "kinetic energy", "potential energy", "gravity", "normal force", "vector",
        "entropy", "thermodynamics", "wavelength", "frequency", "torque", "inertia"
    },
    "biology": {
        "photosynthesis", "chlorophyll", "chloroplast", "thylakoid", "stroma", "atp",
        "nadph", "rubisco", "calvin cycle", "mitochondria", "dna", "rna", "ribosome",
        "mitosis", "meiosis", "enzyme", "glucose", "synapse", "neuron", "axon"
    },
    "business": {
        "funnel", "tofu", "mofu", "bofu", "cac", "ltv", "churn", "roi", "swot",
        "balance sheet", "cash flow", "income statement", "revenue", "ebitda"
    },
    "general": {
        "step", "steps", "case", "example", "result", "output", "input", "diagram",
        "formula", "equation", "analysis", "trade-off", "invariant", "index"
    }
}


class LanguageTeachingEngine:
    """Manages technical term preservation and mixed-language Hinglish speech cleanup."""

    @classmethod
    def get_combined_glossary(cls, domain: DomainCategory) -> Set[str]:
        terms = set(TECHNICAL_GLOSSARIES.get("general", set()))
        domain_key = domain.value.lower()
        if domain_key in TECHNICAL_GLOSSARIES:
            terms.update(TECHNICAL_GLOSSARIES[domain_key])
        return terms

    @classmethod
    def normalize_narration(cls, text: str, language: str = "hinglish", domain: DomainCategory = DomainCategory.GENERAL_KNOWLEDGE) -> str:
        """
        Normalizes narration text for human readability and clear neural TTS pronunciation.
        Guarantees technical terms remain intact in English script.
        """
        if not text:
            return ""

        clean = text.strip()

        # 1. Clean code expressions for audio readability
        # E.g., '20.next' -> '20 dot next', 'curr.next' -> 'current dot next'
        clean = re.sub(r'(\w+)\.next\b', r'\1 dot next', clean)
        clean = re.sub(r'(\w+)\.prev\b', r'\1 dot prev', clean)
        clean = re.sub(r'->', ' points to ', clean)
        clean = re.sub(r'!=', ' is not equal to ', clean)
        clean = re.sub(r'==', ' is equal to ', clean)

        # 2. Math symbols for speech
        clean = re.sub(r'\bint\((.*?)\)', r'integral of \1', clean)
        clean = re.sub(r'\bF\s*=\s*ma\b', 'F equals m times a', clean)

        # 3. Clean Hinglish punctuation so sentence pacing is natural
        if language.lower() in ("hinglish", "hindi"):
            # Ensure commas and full stops have spaces after them
            clean = re.sub(r'([,\.!?])([^\s])', r'\1 \2', clean)

        # 4. Remove markdown bold/italics
        clean = re.sub(r'[*_#`]', '', clean)

        return clean.strip()

    @classmethod
    def is_technical_term(cls, word: str, domain: DomainCategory) -> bool:
        clean = word.lower().strip(" ,.!?;:\"'")
        glossary = cls.get_combined_glossary(domain)
        return clean in glossary
