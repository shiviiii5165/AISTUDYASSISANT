"""
Image Service — Unsplash Adapter
==================================
Unsplash API adapter with credential pool and full compliance:
  - Hotlink photo.urls.regular directly (no re-hosting)
  - Trigger download tracking endpoint on use
  - Store photographer attribution metadata
"""
from app.core.logging import logger
import time
from typing import List

import httpx

from .base import BaseAdapter
from ..models import CandidateImage, Attribution


class UnsplashAdapter(BaseAdapter):
    """
    Unsplash stock photo provider adapter.

    Compliance requirements:
    1. Hotlink URLs from photo.urls (do NOT re-host the image)
    2. Trigger GET /photos/:id/download when image is actually used
    3. Store and display photographer name + link attribution
    """

    PROVIDER_NAME = "unsplash"
    API_URL = "https://api.unsplash.com/search/photos"

    async def search(self, query: str, per_page: int = 5) -> List[CandidateImage]:
        """
        Search Unsplash for landscape photos matching the query.
        Returns candidates with photo_id and download_url for compliance tracking.
        """
        credential = self.pick_credential()
        if not credential:
            logger.warning("[UnsplashAdapter] No available credentials")
            return []

        headers = {
            "Authorization": f"Client-ID {credential.key}",
            "User-Agent": self.USER_AGENT,
            "Accept-Version": "v1",
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

            if resp.status_code == 403 or resp.status_code == 429:
                logger.warning(f"[UnsplashAdapter] {resp.status_code} rate-limited on key ...{credential.key[-8:]}")
                self.record_failure(credential, is_rate_limit=True)
                return []

            if resp.status_code != 200:
                logger.warning(f"[UnsplashAdapter] API returned {resp.status_code}: {resp.text[:150]}")
                self.record_failure(credential)
                return []

            self.record_success(credential, latency_ms)
            data = resp.json()
            results = data.get("results", [])

            candidates = []
            for item in results:
                urls = item.get("urls", {})
                # Hotlink the 'regular' size (1080px wide) — no re-hosting per ToS
                img_url = urls.get("regular") or urls.get("small", "")
                if not img_url:
                    continue

                user = item.get("user", {})
                photo_id = item.get("id", "")

                # Build the download tracking URL (Unsplash compliance)
                links = item.get("links", {})
                download_url = links.get("download_location", "")

                candidates.append(CandidateImage(
                    url=img_url,
                    thumbnail_url=urls.get("thumb", ""),
                    width=item.get("width", 0),
                    height=item.get("height", 0),
                    description=f"{item.get('description', '') or ''} {item.get('alt_description', '') or ''}".strip(),
                    provider="unsplash",
                    photo_id=photo_id,
                    download_url=download_url,
                    attribution=Attribution(
                        photographer_name=user.get("name", ""),
                        photographer_url=f"{user.get('links', {}).get('html', '')}?utm_source=teachgenie&utm_medium=referral",
                        source_url=f"{item.get('links', {}).get('html', '')}?utm_source=teachgenie&utm_medium=referral",
                        provider="unsplash",
                        license_type="Unsplash License",
                    ),
                ))

            logger.info(f"[UnsplashAdapter] Found {len(candidates)} candidates for '{query[:40]}' ({latency_ms:.0f}ms)")
            return candidates

        except httpx.TimeoutException:
            logger.warning(f"[UnsplashAdapter] Timeout for query '{query[:40]}'")
            self.record_failure(credential)
            return []
        except Exception as e:
            logger.warning(f"[UnsplashAdapter] Error: {e}")
            self.record_failure(credential)
            return []

    async def trigger_download(self, download_url: str) -> None:
        """
        Trigger Unsplash download tracking endpoint (compliance requirement).
        Must be called when an image is actually used in a presentation.

        Per Unsplash API guidelines: GET the download_location URL to increment
        the photographer's download count.
        """
        if not download_url:
            return

        credential = self.pick_credential()
        if not credential:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    download_url,
                    headers={
                        "Authorization": f"Client-ID {credential.key}",
                        "User-Agent": self.USER_AGENT,
                    },
                )
            if resp.status_code == 200:
                logger.info(f"[UnsplashAdapter] Download tracking triggered for {download_url[:60]}")
            else:
                logger.warning(f"[UnsplashAdapter] Download tracking returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"[UnsplashAdapter] Download tracking error: {e}")
