"""
Image Service — Pixabay Adapter
=================================
Pixabay API adapter with multi-credential pool and health-based key selection.
Compliance: aggressive caching (24h TTL satisfies Pixabay ToS).
"""
from app.core.logging import logger
import time
from typing import List

import httpx

from .base import BaseAdapter
from ..models import CandidateImage, Attribution


class PixabayAdapter(BaseAdapter):
    """Pixabay stock photo provider adapter."""

    PROVIDER_NAME = "pixabay"
    API_URL = "https://pixabay.com/api/"

    async def search(self, query: str, per_page: int = 5) -> List[CandidateImage]:
        """
        Search Pixabay for landscape photos matching the query.
        Uses health-based credential selection from the pool.
        """
        credential = self.pick_credential()
        if not credential:
            logger.warning("[PixabayAdapter] No available credentials")
            return []

        params = {
            "key": credential.key,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "per_page": per_page,
            "safesearch": "true",
            "min_width": 800,
        }

        start_ms = time.monotonic() * 1000
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.API_URL,
                    params=params,
                    headers={"User-Agent": self.USER_AGENT},
                )

            latency_ms = (time.monotonic() * 1000) - start_ms

            if resp.status_code == 429:
                logger.warning(f"[PixabayAdapter] 429 rate-limited on key ...{credential.key[-8:]}")
                self.record_failure(credential, is_rate_limit=True)
                return []

            if resp.status_code != 200:
                logger.warning(f"[PixabayAdapter] API returned {resp.status_code}: {resp.text[:150]}")
                self.record_failure(credential)
                return []

            self.record_success(credential, latency_ms)
            data = resp.json()
            hits = data.get("hits", [])

            candidates = []
            for hit in hits:
                img_url = hit.get("largeImageURL") or hit.get("webformatURL", "")
                if not img_url:
                    continue

                candidates.append(CandidateImage(
                    url=img_url,
                    thumbnail_url=hit.get("previewURL", ""),
                    width=hit.get("imageWidth", 0),
                    height=hit.get("imageHeight", 0),
                    description=hit.get("tags", ""),
                    provider="pixabay",
                    attribution=Attribution(
                        photographer_name=hit.get("user", ""),
                        photographer_url=f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}",
                        source_url=hit.get("pageURL", ""),
                        provider="pixabay",
                        license_type="Pixabay License",
                    ),
                ))

            logger.info(f"[PixabayAdapter] Found {len(candidates)} candidates for '{query[:40]}' ({latency_ms:.0f}ms)")
            return candidates

        except httpx.TimeoutException:
            logger.warning(f"[PixabayAdapter] Timeout for query '{query[:40]}'")
            self.record_failure(credential)
            return []
        except Exception as e:
            logger.warning(f"[PixabayAdapter] Error: {e}")
            self.record_failure(credential)
            return []
