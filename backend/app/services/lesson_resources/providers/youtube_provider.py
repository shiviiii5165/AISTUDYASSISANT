"""
LearnByGenie Lesson Planner — YouTube Data API v3 Provider
========================================================
Retrieves verified educational YouTube videos using official Data API v3.
Features quota protection (single query first, secondary only if needed),
two-step batch metadata enrichment, and bulletproof thumbnail cascades.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from ..schemas import ResourceCandidate, ResourceType, VerificationLevel

logger = logging.getLogger("teachgenie.lesson_resources.youtube")

DURATION_REGEX = re.compile(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')

_YT_CACHE_FILE = Path(".cache/lesson_resources/yt_query_cache.json")


def _load_yt_disk_cache() -> Dict[str, Any]:
    if _YT_CACHE_FILE.exists():
        try:
            with open(_YT_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_yt_disk_cache(data: Dict[str, Any]) -> None:
    try:
        _YT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_YT_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"[YouTubeProvider] Failed to save disk cache: {e}")


def parse_iso_duration(iso_str: str) -> tuple[int, str]:
    """Parses ISO 8601 duration (PT15M33S) into (seconds, formatted_str)."""
    if not iso_str or not isinstance(iso_str, str):
        return 600, "10:00"
    match = DURATION_REGEX.match(iso_str)
    if not match:
        return 600, "10:00"
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0) + days * 24
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)
    total_seconds = hours * 3600 + minutes * 60 + seconds

    if hours > 0:
        formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        formatted = f"{minutes}:{seconds:02d}"
    return total_seconds, formatted


class YouTubeProvider:
    """
    Official YouTube Data API v3 integration with conservative quota usage.
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    @classmethod
    def get_api_key(cls) -> str:
        # Check settings.YOUTUBE_API_KEY
        key = getattr(settings, "YOUTUBE_API_KEY", "")
        if key and "," in key:
            return key.split(",")[0].strip()
        return key

    @classmethod
    def resolve_thumbnail_cascade(cls, vid: str, raw_thumbs: dict) -> tuple[str, list[str]]:
        """
        Determines primary thumbnail and fallback sequence following:
        maxres -> standard -> high -> medium -> default -> deterministic hqdefault
        """
        thumbnail_url = None
        fallbacks = []

        for quality in ("maxres", "standard", "high", "medium", "default"):
            if quality in raw_thumbs and raw_thumbs[quality].get("url"):
                if not thumbnail_url:
                    thumbnail_url = raw_thumbs[quality]["url"]
                else:
                    fallbacks.append(raw_thumbs[quality]["url"])

        # Fallback to deterministic YouTube URL
        deterministic_url = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        if not thumbnail_url:
            thumbnail_url = deterministic_url
        elif deterministic_url not in fallbacks:
            fallbacks.append(deterministic_url)

        return thumbnail_url, fallbacks

    @classmethod
    async def fetch_candidates(
        cls,
        queries: List[str],
        min_candidates: int = 4,
        target_results: int = 8,
        bypass_cache: bool = False
    ) -> List[ResourceCandidate]:
        """
        Executes query search with strict quota protection:
        1. Checks persistent query cache first.
        2. Issues primary query (queries[0]). Stops immediately if >= min_candidates found.
        3. Only broadens to secondary query if primary yields insufficient results.
        4. When quota is exhausted, falls back to Tavily domain search, extracts/validates
           real 11-character video IDs, normalizes canonical URLs, and uses deterministic
           thumbnails with unverified metadata markers.
        """
        if not queries:
            return []

        primary_query = queries[0]
        cache_key = f"yt_{primary_query.strip().lower()}"
        disk_cache = _load_yt_disk_cache()

        if not bypass_cache and cache_key in disk_cache:
            logger.info(f"[YouTubeProvider] Disk cache HIT for '{primary_query}'")
            try:
                return [ResourceCandidate(**item) for item in disk_cache[cache_key]]
            except Exception as e:
                logger.warning(f"[YouTubeProvider] Error reading cached candidates: {e}")

        api_key = cls.get_api_key()

        all_video_ids: List[str] = []
        seen_ids = set()
        tavily_meta: Dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=8.0) as client:
            # Only use YouTube Data API if key is present
            if api_key:
                for idx, q in enumerate(queries):
                    if len(all_video_ids) >= target_results:
                        break
                    # Strict quota protection: only issue secondary query if primary yielded insufficient results
                    if idx > 0 and len(all_video_ids) >= min_candidates:
                        break

                    try:
                        search_params = {
                            "part": "snippet",
                            "q": q,
                            "type": "video",
                            "videoEmbeddable": "true",
                            "maxResults": 15,
                            "relevanceLanguage": "en",
                            "key": api_key
                        }
                        resp = await client.get(f"{cls.BASE_URL}/search", params=search_params)
                        if resp.status_code == 200:
                            data = resp.json()
                            for item in data.get("items", []):
                                vid = item.get("id", {}).get("videoId")
                                if vid and re.match(r"^[0-9A-Za-z_-]{11}$", vid) and vid not in seen_ids:
                                    seen_ids.add(vid)
                                    all_video_ids.append(vid)
                        elif resp.status_code in (403, 429):
                            logger.warning(f"[YouTubeProvider] YouTube API quota exceeded or throttled ({resp.status_code}).")
                            break
                        else:
                            logger.warning(f"[YouTubeProvider] YouTube search error {resp.status_code}: {resp.text[:100]}")
                            break
                    except Exception as e:
                        logger.error(f"[YouTubeProvider] Search request failed for '{q}': {e}")
                        break

            # Fallback to Tavily domain discovery if search quota was exhausted or 0 results found
            if not all_video_ids:
                logger.info(f"[YouTubeProvider] Falling back to Tavily domain discovery for '{primary_query}'...")
                try:
                    from .tavily_provider import TavilyProvider
                    tavily_candidates = await TavilyProvider.fetch_domain_resources(
                        query=f"site:youtube.com {primary_query}",
                        include_domains=["youtube.com"],
                        category_hint=ResourceType.YOUTUBE_VIDEO,
                        max_results=target_results
                    )
                    for tc in tavily_candidates:
                        vid_match = re.search(r"(?:v=|\/embed\/|\.be\/)([0-9A-Za-z_-]{11})", tc.canonical_url)
                        if vid_match:
                            vid = vid_match.group(1)
                            if re.match(r"^[0-9A-Za-z_-]{11}$", vid) and vid not in seen_ids:
                                seen_ids.add(vid)
                                all_video_ids.append(vid)
                                clean_title = re.sub(r"\s*-\s*YouTube\s*$", "", tc.title, flags=re.IGNORECASE).strip()
                                tavily_meta[vid] = {
                                    "title": clean_title or f"{primary_query} Tutorial",
                                    "description": tc.description,
                                    "source_name": tc.source_name
                                }
                except Exception as ex:
                    logger.warning(f"[YouTubeProvider] Tavily YouTube fallback failed: {ex}")

            if not all_video_ids:
                return []

            # Step 2: Batch enrich metadata via authoritative videos.list (1 unit quota)
            enriched: List[ResourceCandidate] = []
            if api_key:
                try:
                    enriched = await cls._enrich_video_metadata(client, all_video_ids[:target_results], api_key)
                except Exception as ex:
                    logger.warning(f"[YouTubeProvider] videos.list enrichment error: {ex}")

            if enriched:
                disk_cache[cache_key] = [c.model_dump() for c in enriched]
                _save_yt_disk_cache(disk_cache)
                return enriched

            # If videos.list unavailable (quota exhausted), construct candidates from discovered IDs
            # with validated canonical URLs, deterministic thumbnails, and honest unverified metadata markers
            fallback_candidates: List[ResourceCandidate] = []
            for vid in all_video_ids[:target_results]:
                meta = tavily_meta.get(vid, {})
                v_title = meta.get("title") or f"{primary_query} Educational Video"
                v_desc = meta.get("description") or f"Curated video tutorial for {primary_query}."

                fallback_candidates.append(ResourceCandidate(
                    id=f"yt_{vid}",
                    provider="youtube",
                    resource_type=ResourceType.YOUTUBE_VIDEO,
                    title=v_title,
                    canonical_url=f"https://www.youtube.com/watch?v={vid}",
                    description=v_desc,
                    source_name="YouTube",
                    author_or_channel="Channel unverified",
                    duration_formatted="Unavailable",
                    thumbnail_url=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                    thumbnail_fallbacks=[
                        f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                        f"https://img.youtube.com/vi/{vid}/default.jpg"
                    ],
                    verification_levels=[VerificationLevel.DOMAIN_VERIFIED],
                    metadata={"source": "tavily_youtube_fallback", "metadata_verified": False}
                ))

            if fallback_candidates:
                disk_cache[cache_key] = [c.model_dump() for c in fallback_candidates]
                _save_yt_disk_cache(disk_cache)

            return fallback_candidates

    @classmethod
    async def _enrich_video_metadata(
        cls,
        client: httpx.AsyncClient,
        video_ids: List[str],
        api_key: str
    ) -> List[ResourceCandidate]:
        candidates: List[ResourceCandidate] = []
        try:
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": api_key
            }
            resp = await client.get(f"{cls.BASE_URL}/videos", params=params)
            if resp.status_code != 200:
                logger.error(f"[YouTubeProvider] videos.list failed: {resp.status_code}")
                return []

            items = resp.json().get("items", [])
            for item in items:
                vid = item["id"]
                snippet = item.get("snippet", {})
                content = item.get("contentDetails", {})
                stats = item.get("statistics", {})

                title = snippet.get("title", "")
                description = snippet.get("description", "")
                channel = snippet.get("channelTitle", "YouTube Educator")
                published_at = snippet.get("publishedAt", "")

                thumbnail_url, fallbacks = cls.resolve_thumbnail_cascade(vid, snippet.get("thumbnails", {}))


                # Duration parsing
                duration_iso = content.get("duration", "PT10M")
                dur_seconds, dur_formatted = parse_iso_duration(duration_iso)

                view_count = int(stats.get("viewCount", 0)) if stats.get("viewCount") else None
                like_count = int(stats.get("likeCount", 0)) if stats.get("likeCount") else None

                candidates.append(ResourceCandidate(
                    id=f"yt_{vid}",
                    provider="youtube",
                    resource_type=ResourceType.YOUTUBE_VIDEO,
                    title=title,
                    canonical_url=f"https://www.youtube.com/watch?v={vid}",
                    description=description,
                    source_name="YouTube",
                    author_or_channel=channel,
                    thumbnail_url=thumbnail_url,
                    thumbnail_fallbacks=fallbacks,
                    published_at=published_at,
                    year=int(published_at[:4]) if published_at and len(published_at) >= 4 and published_at[:4].isdigit() else None,
                    duration_seconds=dur_seconds,
                    duration_formatted=dur_formatted,
                    view_count=view_count,
                    like_count=like_count,
                    verified=True,
                    verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.METADATA_VERIFIED],
                    metadata={"video_id": vid, "tags": snippet.get("tags", [])}
                ))

        except Exception as e:
            logger.error(f"[YouTubeProvider] videos.list enrichment exception: {e}")

        return candidates
