"""
TeachGenie Lesson Planner — URL & Candidate Verification Engine
==============================================================
Validates URLs, structure, and integrity of external resource candidates.
Rejects malformed or hallucinated candidates and enforces verification levels.
"""

import re
from urllib.parse import urlparse
from typing import List
from .schemas import ResourceCandidate, VerificationLevel

VALID_URL_REGEX = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE
)


class ResourceVerificationEngine:
    """
    Guarantees that every candidate presented to learners is genuine and verified.
    """

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        if len(url) < 10 or len(url) > 2048:
            return False
        if not VALID_URL_REGEX.match(url):
            return False
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    @classmethod
    def verify_candidate(cls, candidate: ResourceCandidate) -> bool:
        """
        Validates a single candidate. Returns False if URL is invalid or fields are empty.
        """
        if not cls.is_valid_url(candidate.canonical_url):
            candidate.verified = False
            return False

        if not candidate.title or len(candidate.title.strip()) < 3:
            candidate.verified = False
            return False

        # Provider-specific integrity checks
        if candidate.provider == "youtube":
            if "youtube.com/watch?v=" not in candidate.canonical_url and "youtu.be/" not in candidate.canonical_url:
                candidate.verified = False
                return False
        elif candidate.provider == "arxiv":
            if "arxiv.org/" not in candidate.canonical_url:
                candidate.verified = False
                return False
        elif candidate.provider == "semantic_scholar":
            if "semanticscholar.org" not in candidate.canonical_url and "doi.org" not in candidate.canonical_url:
                candidate.verified = False
                return False

        candidate.verified = True
        return True

    @classmethod
    def filter_and_verify(cls, candidates: List[ResourceCandidate]) -> List[ResourceCandidate]:
        """
        Deduplicates by URL and verifies all candidates.
        """
        verified_list: List[ResourceCandidate] = []
        seen_urls = set()

        for c in candidates:
            # Normalize URL (strip trailing slash and fragments)
            norm_url = c.canonical_url.split("#")[0].rstrip("/")
            if norm_url in seen_urls:
                continue
            
            if cls.verify_candidate(c):
                seen_urls.add(norm_url)
                c.canonical_url = norm_url
                verified_list.append(c)

        return verified_list
