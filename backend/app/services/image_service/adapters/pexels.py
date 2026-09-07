"""
Image Service — Pexels Adapter
================================
Pexels API adapter with multi-credential pool and health-based key selection.
Compliance: standard rate-limit respect; credentials are for redundancy, not quota multiplication.
"""
from app.core.logging import logger
import time
from typing import List

import httpx

from .base import BaseAdapter
from ..models import CandidateImage, Attribution


class PexelsAdapter(BaseAdapter):
    """Pexels stock photo provider adapter."""

    PROVIDER_NAME = "pexels"
    API_URL = "https://api.pexels.com/v1/search"

    async def search(self, query: str, per_page: int = 5) -> List[CandidateImage]:
        """
        Search Pexels for landscape photos matching the query.
        Uses health-based credential selection from the pool.
        """
        credential = self.pick_credential()
        if not credential:
            logger.warning("[PexelsAdapter] No available credentials")
            return []

        headers = {
            "Authorization": credential.key,
            "User-Agent": self.USER_AGENT,
        }
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape",
        }

        start_ms = time.monotonic() * 1000
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.API_URL, headers=headers, params=params)

            latency_ms = (time.monotonic() * 1000) - start_ms

            if resp.status_code == 429:
                logger.warning(f"[PexelsAdapter] 429 rate-limited on key ...{credential.key[-8:]}")
                self.record_failure(credential, is_rate_limit=True)
                return []

            if resp.status_code != 200:
                logger.warning(f"[PexelsAdapter] API returned {resp.status_code}: {resp.text[:150]}")
                self.record_failure(credential)
                return []

            self.record_success(credential, latency_ms)
            data = resp.json()
            photos = data.get("photos", [])

            candidates = []
            for photo in photos:
                src = photo.get("src", {})
                img_url = src.get("large2x") or src.get("large") or src.get("original", "")
                if not img_url:
                    continue

                candidates.append(CandidateImage(
                    url=img_url,
                    thumbnail_url=src.get("medium", ""),
                    width=photo.get("width", 0),
                    height=photo.get("height", 0),
                    description=photo.get("alt", ""),
                    provider="pexels",
                    attribution=Attribution(
                        photographer_name=photo.get("photographer", ""),
                        photographer_url=photo.get("photographer_url", ""),
                        source_url=photo.get("url", ""),
                        provider="pexels",
                        license_type="Pexels License",
                    ),
                ))

            logger.info(f"[PexelsAdapter] Found {len(candidates)} candidates for '{query[:40]}' ({latency_ms:.0f}ms)")
            return candidates

        except httpx.TimeoutException:
            logger.warning(f"[PexelsAdapter] Timeout for query '{query[:40]}'")
            self.record_failure(credential)
            return []
        except Exception as e:
            logger.warning(f"[PexelsAdapter] Error: {e}")
            self.record_failure(credential)
            return []
