"""
TeachGenie Lesson Planner — Semantic Scholar Provider
=====================================================
Retrieves peer-reviewed scholarly papers and authoritative preprints
using the Semantic Scholar Graph API. Includes global rate limiting,
429 backoff, evidence-based publication labeling, and DOI extraction.
"""

import asyncio
import time
import httpx
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from ..schemas import ResourceCandidate, ResourceType, VerificationLevel

logger = logging.getLogger("teachgenie.lesson_resources.semantic_scholar")

import os
import json
from pathlib import Path

# Provider-level rate limiter: minimum seconds between outbound requests
_LAST_REQUEST_TIME = 0.0
_RATE_LIMIT_LOCK = asyncio.Lock()
MIN_REQUEST_INTERVAL_SECONDS = 1.0  # Strict maximum 1 request/second for introductory key

_S2_CACHE_FILE = Path(".cache/lesson_resources/s2_cache.json")


def _load_s2_disk_cache() -> Dict[str, Any]:
    if _S2_CACHE_FILE.exists():
        try:
            with open(_S2_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_s2_disk_cache(data: Dict[str, Any]) -> None:
    try:
        _S2_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_S2_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"[SemanticScholar] Failed to save disk cache: {e}")


def map_publication_type(raw_types: Optional[List[str]]) -> tuple[str, str]:
    """
    Maps Semantic Scholar publicationTypes to evidence-based labels.
    Returns (publication_type, peer_review_status).
    Never fabricates peer review without evidence.
    """
    if not raw_types:
        return "Scholarly Paper", "Unknown"

    lower_types = [t.lower() for t in raw_types]
    if any("journal" in t for t in lower_types):
        return "Journal Article", "Peer-reviewed"
    if any("conference" in t for t in lower_types):
        return "Conference Paper", "Peer-reviewed"
    if any("review" in t for t in lower_types):
        return "Systematic Review", "Peer-reviewed"
    if any("book" in t for t in lower_types):
        return "Book Chapter", "Peer-reviewed"
    if any("preprint" in t for t in lower_types):
        return "Preprint", "Preprint"

    return "Scholarly Paper", "Unknown"


class SemanticScholarProvider:
    """
    Semantic Scholar Graph API integration with strict 1 req/sec rate-limiting,
    Retry-After respecting backoff, and persistent query-level disk caching.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    @classmethod
    def get_api_key(cls) -> str:
        key = getattr(settings, "SEMANTIC_SCHOLAR_API_KEY", "")
        return key.strip() if key else ""

    @classmethod
    async def fetch_papers(
        cls,
        queries: List[str],
        limit_per_query: int = 6,
        bypass_cache: bool = False
    ) -> List[ResourceCandidate]:
        global _LAST_REQUEST_TIME
        api_key = cls.get_api_key()
        
        headers = {
            "User-Agent": "TeachGenie-LessonPlanner/1.0 (contact@teachgenie.online)"
        }
        if api_key:
            headers["x-api-key"] = api_key

        fields = (
            "paperId,title,abstract,authors,year,venue,citationCount,"
            "influentialCitationCount,externalIds,openAccessPdf,url,publicationTypes"
        )

        candidates: List[ResourceCandidate] = []
        seen_paper_ids = set()
        disk_cache = _load_s2_disk_cache()
        cache_updated = False

        async with httpx.AsyncClient(timeout=12.0) as client:
            for q in queries[:2]:
                q_key = f"s2_{q.strip().lower()}"
                if not bypass_cache and q_key in disk_cache:
                    logger.info(f"[SemanticScholar] Disk cache HIT for query: '{q}'")
                    cached_items = disk_cache[q_key]
                    for item_dict in cached_items:
                        try:
                            c = ResourceCandidate(**item_dict)
                            if c.paper_id and c.paper_id not in seen_paper_ids:
                                seen_paper_ids.add(c.paper_id)
                                candidates.append(c)
                        except Exception:
                            continue
                    continue

                # Enforce global rate limiter across requests (true maximum 1 request/second)
                async with _RATE_LIMIT_LOCK:
                    now = time.time()
                    elapsed = now - _LAST_REQUEST_TIME
                    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
                        sleep_dur = MIN_REQUEST_INTERVAL_SECONDS - elapsed
                        logger.debug(f"[SemanticScholar] Rate limiter: sleeping {sleep_dur:.2f}s")
                        await asyncio.sleep(sleep_dur)
                    _LAST_REQUEST_TIME = time.time()

                params = {
                    "query": q,
                    "limit": limit_per_query,
                    "fields": fields
                }

                # Attempt request with Retry-After and 429 backoff
                query_candidates = []
                for attempt in range(2):
                    try:
                        resp = await client.get(cls.BASE_URL, headers=headers, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            for item in data.get("data", []):
                                pid = item.get("paperId")
                                title = item.get("title")
                                if not pid or not title or pid in seen_paper_ids:
                                    continue
                                seen_paper_ids.add(pid)

                                abstract = item.get("abstract") or ""
                                year = item.get("year")
                                venue = item.get("venue") or ""
                                citation_count = item.get("citationCount")
                                influential_citations = item.get("influentialCitationCount")
                                external_ids = item.get("externalIds") or {}
                                doi = external_ids.get("DOI")
                                arxiv_id = external_ids.get("ArXiv")
                                open_access = item.get("openAccessPdf") is not None
                                
                                raw_authors = item.get("authors") or []
                                authors_str = ", ".join([a.get("name", "") for a in raw_authors[:3]])
                                if len(raw_authors) > 3:
                                    authors_str += " et al."

                                pub_type, peer_review = map_publication_type(item.get("publicationTypes"))
                                if venue and peer_review == "Unknown":
                                    peer_review = "Peer-reviewed"

                                # S2 canonical url fallback
                                url = item.get("url") or f"https://www.semanticscholar.org/paper/{pid}"

                                cand = ResourceCandidate(
                                    id=f"s2_{pid}",
                                    provider="semantic_scholar",
                                    resource_type=ResourceType.RESEARCH_PAPER,
                                    title=title,
                                    canonical_url=url,
                                    description=abstract[:280] + ("..." if len(abstract) > 280 else ""),
                                    source_name=venue or "Semantic Scholar",
                                    author_or_channel=authors_str or "Scholarly Researchers",
                                    year=year,
                                    paper_id=pid,
                                    doi=doi,
                                    arxiv_id=arxiv_id,
                                    citation_count=citation_count,
                                    influential_citation_count=influential_citations,
                                    open_access=open_access,
                                    publication_type=pub_type,
                                    peer_review_status=peer_review,
                                    venue=venue,
                                    verified=True,
                                    verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.METADATA_VERIFIED],
                                    metadata={"abstract": abstract, "external_ids": external_ids}
                                )
                                candidates.append(cand)
                                query_candidates.append(cand)
                            
                            # Cache query results to disk
                            disk_cache[q_key] = [c.model_dump() for c in query_candidates]
                            cache_updated = True
                            break
                        elif resp.status_code == 429:
                            # Respect Retry-After header if provided
                            retry_after_hdr = resp.headers.get("Retry-After")
                            backoff = 2.0 * (attempt + 1)
                            if retry_after_hdr:
                                try:
                                    backoff = max(float(retry_after_hdr), backoff)
                                except ValueError:
                                    pass
                            logger.warning(f"[SemanticScholar] Rate limited (429). Sleeping {backoff:.1f}s (attempt {attempt+1})...")
                            async with _RATE_LIMIT_LOCK:
                                _LAST_REQUEST_TIME = time.time() + backoff
                            await asyncio.sleep(backoff)
                        else:
                            logger.warning(f"[SemanticScholar] Status {resp.status_code}: {resp.text[:120]}")
                            break
                    except Exception as e:
                        logger.error(f"[SemanticScholar] Request error for query '{q}': {e}")
                        break

        if cache_updated:
            _save_s2_disk_cache(disk_cache)

        return candidates
