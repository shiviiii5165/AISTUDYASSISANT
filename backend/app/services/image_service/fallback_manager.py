"""
Image Service — Fallback Manager
==================================
Implements the 5-step routing logic per image request:
  1. Cache check → hit = return immediately
  2. Cache miss → ProviderManager.get_ordered_providers()
  3. Within provider → adapter.search() (health-based credential selection)
  4. On 429/failure → mark unavailable, fall through to next healthiest
  5. On success → rank candidates, download bytes, cache result + save attribution

Also handles Wikimedia Commons as a zero-key educational fallback.
"""
from app.core.logging import logger
import asyncio
import io
import re
from typing import Optional, List

import httpx
from PIL import Image

from .cache import ImageCache
from .models import ImageResult, CandidateImage, Attribution
from .provider_manager import ProviderManager
from .ranker import ImageRanker

USER_AGENT = "LearnByGenieEduBot/2.0 (https://teachgenie.online; support@teachgenie.online)"


class FallbackManager:
    """
    Orchestrates the full image resolution pipeline:
    cache → health-ordered providers → rank → download → cache result.
    """

    def __init__(self, cache: ImageCache, provider_manager: ProviderManager):
        self._cache = cache
        self._provider_manager = provider_manager
        self._ranker = ImageRanker()

    async def resolve(
        self,
        query: str,
        aspect_ratio: str = "landscape",
    ) -> Optional[ImageResult]:
        """
        Resolve an image query to bytes through the full pipeline.
        Returns ImageResult with bytes, attribution, and provider info, or None.
        """
        if not query or not query.strip():
            return None

        query = query.strip()

        # Step 1: Cache check
        cached = await self._cache.get(query)
        if cached:
            return cached

        logger.info(f"[FallbackManager] Cache MISS — resolving '{query[:50]}' from providers")

        # Step 2: Try each provider in health order
        providers = self._provider_manager.get_ordered_providers()
        for adapter in providers:
            try:
                # Step 3: Search (adapter handles credential selection internally)
                candidates = await adapter.search(query, per_page=5)
                if not candidates:
                    continue

                # Rank candidates
                best = self._ranker.rank(candidates, query, aspect_ratio)
                if not best:
                    continue

                # Download image bytes
                result = await self._download_and_validate(best, query)
                if result:
                    # Step 5: Trigger Unsplash download tracking if applicable
                    if best.provider == "unsplash" and best.download_url:
                        unsplash_adapter = self._provider_manager.unsplash
                        asyncio.create_task(unsplash_adapter.trigger_download(best.download_url))

                    # Cache the successful result
                    await self._cache.put(query, result)
                    logger.info(f"[FallbackManager] Resolved '{query[:40]}' via {result.provider}")
                    return result

            except Exception as e:
                # Step 4: On failure, fall through to next provider
                logger.warning(f"[FallbackManager] Provider {adapter.PROVIDER_NAME} failed: {e}")
                continue

        # Step 5: Wikimedia zero-key fallback
        result = await self._try_wikimedia(query)
        if result:
            await self._cache.put(query, result)
            return result

        logger.warning(f"[FallbackManager] All providers exhausted for '{query[:50]}'")
        return None

    async def _download_and_validate(
        self,
        candidate: CandidateImage,
        query: str,
    ) -> Optional[ImageResult]:
        """Download image bytes and validate with Pillow."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    candidate.url,
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                )

            if resp.status_code != 200:
                logger.warning(f"[FallbackManager] Download failed: HTTP {resp.status_code} for {candidate.url[:60]}")
                return None

            content = resp.content
            if len(content) < 2000:
                logger.warning(f"[FallbackManager] Image too small ({len(content)} bytes)")
                return None

            # Validate image with Pillow
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception as e:
                logger.warning(f"[FallbackManager] Corrupted image from {candidate.provider}: {e}")
                return None

            return ImageResult(
                image_bytes=content,
                provider=candidate.provider,
                url=candidate.url,
                query=query,
                width=candidate.width,
                height=candidate.height,
                attribution=candidate.attribution,
            )

        except httpx.TimeoutException:
            logger.warning(f"[FallbackManager] Download timeout for {candidate.url[:60]}")
            return None
        except Exception as e:
            logger.warning(f"[FallbackManager] Download error: {e}")
            return None

    async def _try_wikimedia(self, query: str) -> Optional[ImageResult]:
        """
        Zero-key educational fallback via Wikimedia Commons.
        Returns high-resolution photographs under Creative Commons.
        """
        url = "https://commons.wikimedia.org/w/api.php"
        clean_q = re.sub(r"[^\w\s]", "", query)
        tokens = [t for t in clean_q.split() if len(t) > 2][:4]
        search_str = " ".join(tokens) + " filetype:bitmap"

        params = {
            "action": "query",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": search_str,
            "gsrlimit": "4",
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})

            if resp.status_code != 200:
                return None

            pages = resp.json().get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                info_list = pdata.get("imageinfo", [])
                if not info_list:
                    continue

                info = info_list[0]
                img_url = info.get("url", "")
                mime = info.get("mime", "")

                if img_url and mime in ["image/jpeg", "image/png", "image/webp"]:
                    # Download and validate
                    candidate = CandidateImage(
                        url=img_url,
                        description=pdata.get("title", ""),
                        provider="wikimedia",
                        attribution=Attribution(
                            source_url=img_url,
                            provider="wikimedia",
                            license_type="CC-BY-SA",
                        ),
                    )
                    result = await self._download_and_validate(candidate, query)
                    if result:
                        logger.info(f"[FallbackManager] Wikimedia fallback succeeded: {pdata.get('title', '')[:50]}")
                        return result

        except Exception as e:
            logger.warning(f"[FallbackManager] Wikimedia error: {e}")

        return None
