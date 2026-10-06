"""
LearnByGenie Lesson Planner — Wikipedia Academic Reference Provider
==================================================================
Retrieves canonical encyclopedia articles using Wikipedia OpenSearch / REST API.
STRICT RULE: Wikipedia is ALWAYS classified as Academic Reference, NEVER Official Documentation.
"""

import httpx
import logging
import urllib.parse
from typing import List
from ..schemas import ResourceCandidate, ResourceType, VerificationLevel

logger = logging.getLogger("teachgenie.lesson_resources.wikipedia")


class WikipediaProvider:
    """
    Authoritative encyclopedia reference provider using Wikipedia API.
    """

    BASE_URL = "https://en.wikipedia.org/w/api.php"

    @classmethod
    async def fetch_references(cls, queries: List[str], max_results: int = 2) -> List[ResourceCandidate]:
        candidates: List[ResourceCandidate] = []
        seen_urls = set()

        headers = {
            "User-Agent": "LearnByGenie-LessonPlanner/1.0 (contact@learnbygenie.online)"
        }

        async with httpx.AsyncClient(timeout=6.0) as client:
            for q in queries[:2]:
                try:
                    params = {
                        "action": "opensearch",
                        "search": q,
                        "limit": max_results,
                        "namespace": 0,
                        "format": "json"
                    }
                    resp = await client.get(cls.BASE_URL, headers=headers, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        titles = data[1] if len(data) > 1 else []
                        snippets = data[2] if len(data) > 2 else []
                        links = data[3] if len(data) > 3 else []

                        for i in range(len(titles)):
                            url = links[i]
                            if not url or url in seen_urls:
                                continue
                            seen_urls.add(url)

                            title = titles[i]
                            snippet = snippets[i] or f"Authoritative encyclopedia reference on {title}."

                            candidates.append(ResourceCandidate(
                                id=f"wiki_{abs(hash(url)) % 10000000}",
                                provider="wikipedia",
                                resource_type=ResourceType.ACADEMIC_REFERENCE,  # STRICT: NEVER Official Documentation
                                title=f"{title} — Encyclopedia Reference",
                                canonical_url=url,
                                description=snippet[:260] + ("..." if len(snippet) > 260 else ""),
                                source_name="Wikipedia Encyclopedia",
                                author_or_channel="Wikimedia Foundation",
                                verified=True,
                                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.METADATA_VERIFIED],
                                metadata={"wiki_title": title}
                            ))
                except Exception as e:
                    logger.warning(f"[WikipediaProvider] Search error for '{q}': {e}")

        return candidates
