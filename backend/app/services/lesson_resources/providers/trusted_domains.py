"""
LearnByGenie Lesson Planner — Trusted Domain Registry
===================================================
Maintains authoritative domains for Official Documentation, Coding Problems,
and Academic References. Strictly ensures Wikipedia and GeeksforGeeks are NEVER
misclassified as Official Documentation.
"""

from urllib.parse import urlparse
from typing import Dict, List, Optional
from ..schemas import ResourceType

# Authoritative official documentation domains
OFFICIAL_DOCS_DOMAINS: Dict[str, str] = {
    "docs.python.org": "Python Software Foundation Documentation",
    "react.dev": "Official React Documentation",
    "reactjs.org": "Legacy React Documentation",
    "developer.mozilla.org": "MDN Web Docs (Mozilla)",
    "postgresql.org": "PostgreSQL Global Development Group",
    "dev.mysql.com": "MySQL Official Documentation",
    "docs.oracle.com": "Oracle Official Documentation",
    "mongodb.com": "MongoDB Official Manual",
    "redis.io": "Redis Official Documentation",
    "typescriptlang.org": "TypeScript Official Handbook",
    "docs.docker.com": "Docker Official Documentation",
    "kubernetes.io": "Kubernetes Official Documentation",
    "pandas.pydata.org": "Pandas Official Documentation",
    "numpy.org": "NumPy Official Documentation",
    "pytorch.org": "PyTorch Official Documentation",
    "tensorflow.org": "TensorFlow Official Documentation",
    "doc.rust-lang.org": "Rust Official Documentation",
    "go.dev": "Go Official Documentation",
    "cppreference.com": "C++ Standard Reference",
    "git-scm.com": "Git Official Documentation",
    "man7.org": "Linux Programmer's Manual",
    "sqlite.org": "SQLite Official Documentation",
    "expressjs.com": "Express.js Official Guide",
    "spring.io": "Spring Official Documentation"
}

# Practice & Coding platforms
CODING_PRACTICE_DOMAINS = {
    "leetcode.com": "LeetCode",
    "geeksforgeeks.org": "GeeksforGeeks Practice",
    "hackerrank.com": "HackerRank",
    "codewars.com": "Codewars"
}

# General tutorials & guides (NOT official documentation)
TUTORIAL_GUIDE_DOMAINS = {
    "geeksforgeeks.org": "GeeksforGeeks Tutorial",
    "tutorialspoint.com": "TutorialsPoint",
    "w3schools.com": "W3Schools",
    "javatpoint.com": "Javatpoint",
    "freecodecamp.org": "freeCodeCamp",
    "baeldung.com": "Baeldung",
    "digitalocean.com": "DigitalOcean Community",
    "medium.com": "Medium Publication"
}

# Academic & Encyclopedia sources
ACADEMIC_REFERENCE_DOMAINS = {
    "en.wikipedia.org": "Wikipedia",
    "wikipedia.org": "Wikipedia",
    "britannica.com": "Encyclopaedia Britannica",
    "plato.stanford.edu": "Stanford Encyclopedia of Philosophy",
    "mathworld.wolfram.com": "Wolfram MathWorld",
    "sciencedirect.com": "ScienceDirect",
    "nature.com": "Nature Publishing",
    "ieee.org": "IEEE Xplore",
    "acm.org": "ACM Digital Library"
}


class TrustedDomainRegistry:
    """
    Validates and classifies web resources into strict pedagogical categories.
    """

    @classmethod
    def get_domain(cls, url: str) -> str:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    @classmethod
    def is_official_doc_domain(cls, url: str) -> bool:
        domain = cls.get_domain(url)
        # Never allow Wikipedia or GeeksforGeeks as official documentation
        if "wikipedia.org" in domain or "geeksforgeeks.org" in domain:
            return False
        return any(domain == doc_d or domain.endswith("." + doc_d) for doc_d in OFFICIAL_DOCS_DOMAINS)

    @classmethod
    def is_coding_platform(cls, url: str) -> bool:
        domain = cls.get_domain(url)
        return any(domain == c_d or domain.endswith("." + c_d) for c_d in CODING_PRACTICE_DOMAINS)

    @classmethod
    def is_academic_reference(cls, url: str) -> bool:
        domain = cls.get_domain(url)
        return any(domain == a_d or domain.endswith("." + a_d) for a_d in ACADEMIC_REFERENCE_DOMAINS)

    @classmethod
    def classify_url(cls, url: str, is_programming_topic: bool = False) -> ResourceType:
        """
        Determines the strict pedagogical resource type of a given URL.
        """
        domain = cls.get_domain(url)

        # 1. Check Academic References (Wikipedia is ALWAYS reference, never official doc)
        if cls.is_academic_reference(url):
            return ResourceType.ACADEMIC_REFERENCE

        # 2. Check Coding Platforms
        if cls.is_coding_platform(url):
            # If URL contains /problems/ or /practice, classify as coding problem
            if any(path_sub in url.lower() for path_sub in ["/problems/", "/practice/", "/challenges/"]):
                return ResourceType.CODING_PROBLEM
            return ResourceType.CODING_PROBLEM if is_programming_topic else ResourceType.PRACTICE_PROBLEM

        # 3. Check Official Documentation
        if cls.is_official_doc_domain(url):
            return ResourceType.OFFICIAL_DOCUMENTATION

        # 4. Check Tutorial & Guides
        if any(domain == t_d or domain.endswith("." + t_d) for t_d in TUTORIAL_GUIDE_DOMAINS):
            return ResourceType.GUIDE

        return ResourceType.GUIDE
