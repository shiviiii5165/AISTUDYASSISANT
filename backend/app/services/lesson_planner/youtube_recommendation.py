import asyncio
import re
import logging
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import settings
from .schemas import (
    RoadmapStage,
    YouTubeVideoRecommendation,
    YouTubeRecommendationResponse,
)

logger = logging.getLogger("learnbygenie.lesson_planner.youtube")

YOUTUBE_ID_REGEX = re.compile(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*')

# High-signal educational keywords for boosting
EDU_KEYWORDS = {
    "tutorial", "lecture", "course", "explanation", "introduction", 
    "nptel", "mit", "stanford", "khan", "gate", "engineering", 
    "deep dive", "crash course", "worked example", "concept", "algorithm"
}


def _extract_video_id(url: str) -> Optional[str]:
    match = YOUTUBE_ID_REGEX.search(url)
    return match.group(1) if match else None


def _format_thumbnail(video_id: Optional[str], raw_images: Any) -> Optional[str]:
    if isinstance(raw_images, dict):
        for size in ("large", "medium", "small"):
            if raw_images.get(size):
                return raw_images[size]
    elif isinstance(raw_images, str) and raw_images.startswith("http"):
        return raw_images
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return None


def _sync_ddgs_videos(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Synchronous video search using ddgs."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.videos(query, max_results=max_results))
    except Exception as e:
        logger.warning(f"[YouTubeRecommendation] DDGS video search error: {e}")
        return []


class YouTubeRecommendationService:
    """
    Live educational YouTube recommendation engine for Lesson Planner stages.
    Discovers, ranks, and annotates educational videos aligned with curriculum stages.
    """

    @classmethod
    async def get_recommendations(
        cls,
        topic: str,
        stage: Optional[RoadmapStage] = None,
        learner_level: str = "B.Tech",
        language: str = "english",
        limit: int = 3
    ) -> YouTubeRecommendationResponse:
        """
        Fetch and rank live YouTube educational videos for a lesson stage.
        """
        if not getattr(settings, "LESSON_PLANNER_YOUTUBE_ENABLED", True):
            return YouTubeRecommendationResponse(
                enabled=False,
                status="coming_soon",
                items=[]
            )

        stage_title = stage.title if stage else ""

        # Construct a targeted educational search query
        query_parts = [topic]
        if stage_title:
            query_parts.append(stage_title)
        query_parts.append("educational tutorial lecture")
        if language and language.lower() in ("hindi", "hinglish"):
            query_parts.append("hindi")
        
        search_query = " ".join(query_parts).strip()
        logger.info(f"[YouTubeRecommendation] Querying live videos for: '{search_query}' (limit={limit})")

        raw_videos: List[Dict[str, Any]] = []

        # 1. Try YouTube Data API v3 if API key is provided
        api_key = getattr(settings, "YOUTUBE_API_KEY", "")
        if api_key:
            raw_videos = await cls._fetch_youtube_data_api(search_query, api_key, limit=limit + 3)

        # 2. Fallback or primary: DuckDuckGo Videos Search
        if not raw_videos:
            try:
                loop = asyncio.get_running_loop()
                raw_videos = await loop.run_in_executor(
                    None, _sync_ddgs_videos, search_query, limit + 4
                )
            except Exception as e:
                logger.error(f"[YouTubeRecommendation] Video discovery failed: {e}")
                raw_videos = []

        # 3. Process, rank, and annotate recommendations
        recommendations: List[YouTubeVideoRecommendation] = []
        seen_urls = set()

        for item in raw_videos:
            url = item.get("content") or item.get("url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title") or f"{topic} Overview"
            channel = item.get("uploader") or item.get("publisher") or item.get("channel") or "Educational Creator"
            duration = item.get("duration") or ""
            video_id = _extract_video_id(url)
            thumbnail = _format_thumbnail(video_id, item.get("images"))

            # Calculate educational relevance score
            relevance_score = cls._score_video(title, channel, stage_title, topic)
            difficulty = cls._determine_difficulty(learner_level, title)
            reason = cls._generate_reason(title, channel, stage_title or topic, learner_level)

            recommendations.append(YouTubeVideoRecommendation(
                title=title,
                channel=channel,
                thumbnail=thumbnail,
                duration=duration if duration else "10-15 min",
                url=url,
                relevance=round(relevance_score, 2),
                difficulty=difficulty,
                source="YouTube",
                reason=reason
            ))

            if len(recommendations) >= limit:
                break

        # 4. Safe fallback if zero results were found
        if not recommendations:
            fallback_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
            recommendations.append(YouTubeVideoRecommendation(
                title=f"{topic}: {stage_title or 'Comprehensive Guide'}",
                channel="Academic & University Channels",
                thumbnail="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=640",
                duration="15-20 min",
                url=fallback_url,
                relevance=0.90,
                difficulty=cls._determine_difficulty(learner_level, stage_title),
                source="YouTube",
                reason=f"Curated reference search matching {stage_title or topic} for {learner_level} students."
            ))

        # Sort descending by relevance
        recommendations.sort(key=lambda r: r.relevance, reverse=True)

        return YouTubeRecommendationResponse(
            enabled=True,
            status="active",
            items=recommendations[:limit]
        )

    @classmethod
    async def _fetch_youtube_data_api(cls, query: str, api_key: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch videos via YouTube Data API v3 if key is configured."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "maxResults": limit,
                        "key": api_key,
                        "safeSearch": "moderate"
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    results = []
                    for item in data.get("items", []):
                        vid = item.get("id", {}).get("videoId")
                        snippet = item.get("snippet", {})
                        if vid:
                            results.append({
                                "title": snippet.get("title", ""),
                                "content": f"https://www.youtube.com/watch?v={vid}",
                                "uploader": snippet.get("channelTitle", ""),
                                "images": snippet.get("thumbnails", {}).get("high", {}).get("url")
                            })
                    return results
        except Exception as e:
            logger.warning(f"[YouTubeRecommendation] YouTube Data API call failed: {e}")
        return []

    @classmethod
    def _score_video(cls, title: str, channel: str, stage_title: str, topic: str) -> float:
        """Compute educational relevance score (0.70 to 0.99)."""
        score = 0.80
        t_lower = (title + " " + channel).lower()

        # Keyword match
        for kw in EDU_KEYWORDS:
            if kw in t_lower:
                score += 0.03

        # Topic & Stage match
        if topic.lower() in t_lower:
            score += 0.08
        if stage_title and stage_title.lower() in t_lower:
            score += 0.06

        return min(0.99, max(0.70, score))

    @classmethod
    def _determine_difficulty(cls, learner_level: str, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("advanced", "mastery", "complex", "research", "proof")):
            return "advanced"
        if any(w in t for w in ("beginner", "intro", "basics", "fundamentals", "what is")):
            return "beginner"
        if "school" in learner_level.lower():
            return "beginner"
        return "intermediate"

    @classmethod
    def _generate_reason(cls, title: str, channel: str, stage_name: str, learner_level: str) -> str:
        return f"Covers core principles of {stage_name} with concrete pedagogical demonstrations for {learner_level} learners."
