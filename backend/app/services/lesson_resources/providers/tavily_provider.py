"""
TeachGenie Lesson Planner — Tavily Domain-Constrained Provider
=============================================================
Uses Tavily Search with aggressive domain restrictions for:
- Programming practice (LeetCode, GeeksforGeeks, HackerRank)
- Authoritative Official Documentation
- High-quality Tutorials & Guides
Preserves credits using search_depth='basic' and tight domain whitelisting.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from ..schemas import ResourceCandidate, ResourceType, VerificationLevel
from .trusted_domains import (
    TrustedDomainRegistry,
    OFFICIAL_DOCS_DOMAINS,
    CODING_PRACTICE_DOMAINS,
    TUTORIAL_GUIDE_DOMAINS
)

logger = logging.getLogger("teachgenie.lesson_resources.tavily")


class TavilyProvider:
    """
    Tavily search provider operating under strict domain whitelists.
    """

    BASE_URL = "https://api.tavily.com/search"

    @classmethod
    def get_api_key(cls) -> str:
        key = getattr(settings, "TAVILY_API_KEY", "")
        if key and "," in key:
            # Multi-key pool: use first valid key
            return key.split(",")[0].strip()
        return key.strip() if key else ""

    @classmethod
    async def fetch_domain_resources(
        cls,
        query: str,
        include_domains: List[str],
        category_hint: ResourceType,
        max_results: int = 4
    ) -> List[ResourceCandidate]:
        api_key = cls.get_api_key()
        if not api_key:
            logger.warning("[TavilyProvider] No TAVILY_API_KEY configured. Skipping.")
            return []

        if not include_domains:
            return []

        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_domains": include_domains[:10],
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False
        }

        candidates: List[ResourceCandidate] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(cls.BASE_URL, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    for r in results:
                        url = r.get("url", "")
                        title = r.get("title", "").strip()
                        snippet = r.get("content", "").strip()

                        if not url or not title:
                            continue

                        # Verify and classify URL through trusted domain rules
                        actual_type = TrustedDomainRegistry.classify_url(url, is_programming_topic=True)
                        if category_hint == ResourceType.CODING_PROBLEM and actual_type != ResourceType.CODING_PROBLEM:
                            # Verify if it has problem/practice in path
                            if "problems" in url or "practice" in url:
                                actual_type = ResourceType.CODING_PROBLEM

                        domain = TrustedDomainRegistry.get_domain(url)
                        source_name = OFFICIAL_DOCS_DOMAINS.get(domain) or CODING_PRACTICE_DOMAINS.get(domain) or domain.capitalize()

                        candidates.append(ResourceCandidate(
                            id=f"tavily_{abs(hash(url)) % 10000000}",
                            provider="tavily",
                            resource_type=actual_type,
                            title=title,
                            canonical_url=url,
                            description=snippet[:260] + ("..." if len(snippet) > 260 else ""),
                            source_name=source_name,
                            author_or_channel=domain,
                            verified=True,
                            verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                            metadata={"score": r.get("score")}
                        ))
                else:
                    logger.warning(f"[TavilyProvider] Search returned status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.error(f"[TavilyProvider] Request failed for query '{query}': {e}")

        return candidates
