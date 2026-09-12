"""
TeachGenie Lesson Planner — arXiv Preprint Provider
===================================================
Fetches and validates real preprints directly from the official arXiv API.
Parses Atom XML feeds without fabricating authors, titles, or identifiers.
"""

import re
import httpx
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from ..schemas import ResourceCandidate, ResourceType, VerificationLevel

logger = logging.getLogger("teachgenie.lesson_resources.arxiv")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivProvider:
    """
    Official arXiv API integration for physics, math, and computer science preprints.
    """

    BASE_URL = "https://export.arxiv.org/api/query"

    @classmethod
    async def fetch_preprints(
        cls,
        queries: List[str],
        max_results: int = 4
    ) -> List[ResourceCandidate]:
        candidates: List[ResourceCandidate] = []
        seen_ids = set()

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for q in queries[:1]:  # 1 targeted query to preserve latency
                clean_q = re.sub(r"[^\w\s]", " ", q).strip()
                params = {
                    "search_query": f"all:{clean_q}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending"
                }

                try:
                    resp = await client.get(cls.BASE_URL, params=params)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        for entry in root.findall("atom:entry", ATOM_NS):
                            id_elem = entry.find("atom:id", ATOM_NS)
                            raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                            # extract clean arxiv_id e.g. 2104.12345
                            arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
                            
                            if not arxiv_id or arxiv_id in seen_ids:
                                continue
                            seen_ids.add(arxiv_id)

                            title_elem = entry.find("atom:title", ATOM_NS)
                            title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else ""
                            
                            summary_elem = entry.find("atom:summary", ATOM_NS)
                            summary = " ".join(summary_elem.text.split()) if summary_elem is not None and summary_elem.text else ""
                            
                            published_elem = entry.find("atom:published", ATOM_NS)
                            published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                            year = int(published[:4]) if published and len(published) >= 4 and published[:4].isdigit() else None

                            authors = []
                            for a in entry.findall("atom:author", ATOM_NS):
                                name_elem = a.find("atom:name", ATOM_NS)
                                if name_elem is not None and name_elem.text:
                                    authors.append(name_elem.text.strip())
                            authors_str = ", ".join(authors[:3])
                            if len(authors) > 3:
                                authors_str += " et al."

                            canonical_url = f"https://arxiv.org/abs/{arxiv_id}"

                            candidates.append(ResourceCandidate(
                                id=f"arxiv_{arxiv_id.replace('.', '_')}",
                                provider="arxiv",
                                resource_type=ResourceType.RESEARCH_PAPER,
                                title=title,
                                canonical_url=canonical_url,
                                description=summary[:280] + ("..." if len(summary) > 280 else ""),
                                source_name="arXiv Preprint",
                                author_or_channel=authors_str or "arXiv Authors",
                                published_at=published,
                                year=year,
                                arxiv_id=arxiv_id,
                                open_access=True,
                                publication_type="Preprint",
                                peer_review_status="Preprint",
                                venue="arXiv.org",
                                verified=True,
                                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.METADATA_VERIFIED],
                                metadata={"arxiv_raw_id": raw_id, "summary": summary}
                            ))
                    else:
                        logger.warning(f"[ArxivProvider] Response {resp.status_code}")
                except Exception as e:
                    logger.error(f"[ArxivProvider] Search error for '{q}': {e}")

        return candidates
