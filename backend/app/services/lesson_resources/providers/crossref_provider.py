"""
TeachGenie Lesson Planner — Crossref DOI Verification Provider
=============================================================
Validates DOIs and enriches paper metadata using Crossref REST API.
Adheres to polite User-Agent conventions with CROSSREF_MAILTO.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("teachgenie.lesson_resources.crossref")

# In-memory DOI cache to prevent redundant lookups
_DOI_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


class CrossrefProvider:
    """
    Validates DOIs and retrieves verified journal publication metadata.
    """

    BASE_URL = "https://api.crossref.org/works"

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        mailto = getattr(settings, "CROSSREF_MAILTO", "contact@teachgenie.online")
        return {
            "User-Agent": f"TeachGenie-LessonPlanner/1.0 (mailto:{mailto})"
        }

    @classmethod
    async def verify_doi(cls, doi: str) -> Optional[Dict[str, Any]]:
        """
        Validates DOI against Crossref and returns canonical publication metadata.
        """
        if not doi:
            return None
            
        clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
        if clean_doi in _DOI_METADATA_CACHE:
            return _DOI_METADATA_CACHE[clean_doi]

        url = f"{cls.BASE_URL}/{clean_doi}"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers=cls.get_headers())
                if resp.status_code == 200:
                    message = resp.json().get("message", {})
                    
                    # Extract year
                    issued = message.get("issued", {}).get("date-parts", [[]])[0]
                    year = issued[0] if issued and len(issued) > 0 else None
                    
                    # Extract venue
                    container_titles = message.get("container-title", [])
                    venue = container_titles[0] if container_titles else message.get("publisher", "")
                    
                    # Extract authors
                    raw_authors = message.get("author", [])
                    author_names = []
                    for a in raw_authors[:3]:
                        family = a.get("family", "")
                        given = a.get("given", "")
                        author_names.append(f"{given} {family}".strip() or family)
                    author_str = ", ".join(author_names)
                    if len(raw_authors) > 3:
                        author_str += " et al."

                    result = {
                        "doi": clean_doi,
                        "canonical_url": message.get("URL") or f"https://doi.org/{clean_doi}",
                        "title": message.get("title", [""])[0] if message.get("title") else "",
                        "venue": venue,
                        "year": year,
                        "authors": author_str,
                        "is_peer_reviewed": True,
                        "type": message.get("type", "journal-article")
                    }
                    _DOI_METADATA_CACHE[clean_doi] = result
                    return result
                elif resp.status_code == 404:
                    logger.info(f"[Crossref] DOI not found: {clean_doi}")
                    return None
        except Exception as e:
            logger.warning(f"[Crossref] DOI verification error for '{clean_doi}': {e}")

        return None
