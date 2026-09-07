"""
Image Service — Top-Level Entry Point
=======================================
Exposes `ImageService` with a single `get_best_image()` method.
Coordinates Cache → ProviderManager → ImageRanker → FallbackManager.

Usage:
    from app.services.image_service import get_best_image
    result = await get_best_image("machine learning neural network")
    if result:
        image_bytes = result.image_bytes
        attribution = result.attribution
"""
from app.core.logging import logger
import asyncio
from typing import Optional, List, Dict, Any

from app.core.config import settings

from .cache import ImageCache
from .fallback_manager import FallbackManager
from .models import ImageResult
from .provider_manager import ProviderManager
from .query_generator import QueryGenerator


def _parse_key_pool(pool_str: str, single_key: str = "") -> List[str]:
    """Parse comma-separated key pool, falling back to single key."""
    keys = []
    if pool_str:
        keys = [k.strip() for k in pool_str.split(",") if k.strip()]
    if not keys and single_key and single_key.strip():
        keys = [single_key.strip()]
    return keys


class ImageService:
    """
    Provider-abstracted stock photo engine.

    The PPT generator calls this through `get_best_image(query, aspect_ratio)`.
    It doesn't know or care which provider or credential served the image.
    """

    _instance: Optional["ImageService"] = None

    def __init__(self):
        # Parse credential pools from settings
        pexels_keys = _parse_key_pool(settings.PEXELS_API_KEYS, settings.PEXELS_API_KEY)
        pixabay_keys = _parse_key_pool(settings.PIXABAY_API_KEYS, settings.PIXABAY_API_KEY)
        unsplash_keys = _parse_key_pool(settings.UNSPLASH_ACCESS_KEYS, settings.UNSPLASH_ACCESS_KEY)

        logger.info(
            f"[ImageService] Initialized with credential pools: "
            f"Pexels={len(pexels_keys)}, Pixabay={len(pixabay_keys)}, Unsplash={len(unsplash_keys)}"
        )

        # Initialize Supabase client for persistent cache
        try:
            from app.db.supabase_client import supabase
            supabase_client = supabase
        except Exception:
            supabase_client = None

        self._cache = ImageCache(supabase_client=supabase_client)
        self._provider_manager = ProviderManager(
            pexels_keys=pexels_keys,
            pixabay_keys=pixabay_keys,
            unsplash_keys=unsplash_keys,
        )
        self._fallback_manager = FallbackManager(self._cache, self._provider_manager)
        self._query_generator = QueryGenerator()

    @classmethod
    def get_instance(cls) -> "ImageService":
        """Get or create the singleton ImageService instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_best_image(
        self,
        query: str,
        aspect_ratio: str = "landscape",
        timeout: float = 25.0,
    ) -> Optional[ImageResult]:
        """
        Main entry point: resolve a search query to the best available image.

        Args:
            query: Image search query (e.g. "neural network brain connections")
            aspect_ratio: "landscape" | "portrait" | "square"
            timeout: Hard timeout in seconds (default 25s)

        Returns:
            ImageResult with bytes, attribution, and provider info, or None.
        """
        if not query or not query.strip():
            return None

        try:
            result = await asyncio.wait_for(
                self._fallback_manager.resolve(query, aspect_ratio),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[ImageService] get_best_image timed out ({timeout}s) for '{query[:50]}'")
            return None
        except Exception as e:
            logger.error(f"[ImageService] get_best_image error: {e}")
            return None

    async def get_best_image_for_slide(
        self,
        slide_dict: Dict[str, Any],
        topic: str = "",
        aspect_ratio: str = "landscape",
    ) -> Optional[ImageResult]:
        """
        Convenience method: generate query from slide content, then resolve image.

        Args:
            slide_dict: Slide dictionary with title, key_message, example, etc.
            topic: Overall presentation topic
            aspect_ratio: Target aspect ratio

        Returns:
            ImageResult or None.
        """
        query = self._query_generator.generate_query(slide_dict, topic)
        if not query:
            return None

        logger.info(f"[ImageService] Generated query for slide '{slide_dict.get('title', '')[:30]}': '{query[:50]}'")
        return await self.get_best_image(query, aspect_ratio)

    def get_health_report(self) -> Dict[str, Any]:
        """Return full health report (provider health + cache stats)."""
        return {
            "providers": self._provider_manager.get_health_report(),
            "cache": self._cache.get_stats(),
        }


# ── Module-level convenience function ──────────────────────────────────

async def get_best_image(
    query: str,
    aspect_ratio: str = "landscape",
    timeout: float = 25.0,
) -> Optional[ImageResult]:
    """
    Module-level convenience function.
    Creates/reuses singleton ImageService and resolves an image.
    """
    service = ImageService.get_instance()
    return await service.get_best_image(query, aspect_ratio, timeout)
