"""
Test Suite: Image Provider Fallback & Caching
=============================================
Verifies provider fallback chain (Pexels fail -> Pixabay fail -> Unsplash fail -> Wikimedia)
and verifies that caching prevents duplicate external API queries.
"""
import sys
import os
import io
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, AsyncMock
from PIL import Image
from app.services.presentation.image_source_router import (
    resolve_stock_image, compute_image_query_hash, get_cached_image
)


from PIL import Image, ImageDraw

def create_dummy_jpeg() -> bytes:
    """Creates a valid JPEG in memory (> 2000 bytes for size check)."""
    im = Image.new("RGB", (300, 300), color=(73, 109, 137))
    draw = ImageDraw.Draw(im)
    for i in range(100):
        draw.line([(i, i * 2), (300 - i, i * 3)], fill=(i * 2 % 255, i * 5 % 255, i * 7 % 255))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_provider_fallback_to_wikimedia():
    """When commercial keys fail or return empty, verify clean fallback to Wikimedia Commons."""
    async def _run():
        dummy_bytes = create_dummy_jpeg()

        with patch("app.services.presentation.image_source_router._fetch_pexels", new_callable=AsyncMock) as mock_pex, \
             patch("app.services.presentation.image_source_router._fetch_pixabay", new_callable=AsyncMock) as mock_pix, \
             patch("app.services.presentation.image_source_router._fetch_unsplash", new_callable=AsyncMock) as mock_uns, \
             patch("app.services.presentation.image_source_router._fetch_wikimedia", new_callable=AsyncMock) as mock_wiki, \
             patch("app.services.presentation.image_source_router.get_cached_image", new_callable=AsyncMock, return_value=None), \
             patch("httpx.AsyncClient.get") as mock_get:

            # Pexels, Pixabay, Unsplash return None (simulating unset key or network error)
            mock_pex.return_value = None
            mock_pix.return_value = None
            mock_uns.return_value = None
            mock_wiki.return_value = ("https://upload.wikimedia.org/test.jpg", "Wikimedia: Test Image")

            # Mock download response
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.content = dummy_bytes
            mock_get.return_value = mock_resp

            result_bytes = await resolve_stock_image("laboratory semiconductor cleanroom wafer")
            
            assert result_bytes is not None
            assert len(result_bytes) > 100
            assert mock_pex.called
            assert mock_pix.called
            assert mock_uns.called
            assert mock_wiki.called
    asyncio.run(_run())


def test_persistent_caching_avoids_duplicate_api_calls():
    """Verify that cached image queries return instantly without hitting fetch providers."""
    async def _run():
        dummy_bytes = create_dummy_jpeg()
        query = "quantum computing cryogenic dilution refrigerator test"
        q_hash = compute_image_query_hash(query)

        with patch("app.services.presentation.image_source_router.get_cached_image", new_callable=AsyncMock) as mock_cache, \
             patch("app.services.presentation.image_source_router._fetch_pexels", new_callable=AsyncMock) as mock_pex:

            mock_cache.return_value = dummy_bytes

            res = await resolve_stock_image(query)
            assert res == dummy_bytes
            assert mock_cache.called
            assert not mock_pex.called, "Should not hit external providers on cache HIT"
    asyncio.run(_run())
