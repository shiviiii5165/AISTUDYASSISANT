"""
Image Service — Provider Manager
==================================
Holds one adapter per provider and provides health-based provider ordering.
Default preference: Pexels > Pixabay > Unsplash, overridden by real-time health.
"""
from app.core.logging import logger
from typing import List, Optional

from .adapters.base import BaseAdapter
from .adapters.pexels import PexelsAdapter
from .adapters.pixabay import PixabayAdapter
from .adapters.unsplash import UnsplashAdapter


class ProviderManager:
    """
    Manages all stock photo provider adapters.
    Provides get_ordered_providers() which returns providers sorted by health score.
    """

    # Default preference ordering (used as tiebreaker when health scores are equal)
    DEFAULT_ORDER = {"pexels": 0, "pixabay": 1, "unsplash": 2}

    def __init__(
        self,
        pexels_keys: List[str] = None,
        pixabay_keys: List[str] = None,
        unsplash_keys: List[str] = None,
    ):
        self.pexels = PexelsAdapter(pexels_keys or [])
        self.pixabay = PixabayAdapter(pixabay_keys or [])
        self.unsplash = UnsplashAdapter(unsplash_keys or [])

        self._adapters: List[BaseAdapter] = [
            self.pexels,
            self.pixabay,
            self.unsplash,
        ]

    @property
    def configured_adapters(self) -> List[BaseAdapter]:
        """Return only adapters that have at least one credential configured."""
        return [a for a in self._adapters if a.is_configured]

    def get_ordered_providers(self) -> List[BaseAdapter]:
        """
        Return providers ordered by health score (descending).
        Ties are broken by default preference order (Pexels > Pixabay > Unsplash).
        Only returns configured adapters.
        """
        configured = self.configured_adapters
        if not configured:
            logger.warning("[ProviderManager] No providers configured with API keys")
            return []

        # Sort by health_score desc, then default order asc
        configured.sort(
            key=lambda a: (
                a.health_score(),
                -self.DEFAULT_ORDER.get(a.PROVIDER_NAME, 99),
            ),
            reverse=True,
        )

        provider_names = [a.PROVIDER_NAME for a in configured]
        logger.info(f"[ProviderManager] Provider order by health: {provider_names}")
        return configured

    def get_healthiest_provider(self) -> Optional[BaseAdapter]:
        """Return the single healthiest provider, or None."""
        ordered = self.get_ordered_providers()
        return ordered[0] if ordered else None

    def get_health_report(self) -> dict:
        """Return health stats for all adapters (for debugging/logging)."""
        return {
            a.PROVIDER_NAME: {
                "configured": a.is_configured,
                "health_score": round(a.health_score(), 3),
                "total_requests": a.provider_health.total_requests,
                "total_successes": a.provider_health.total_successes,
                "consecutive_failures": a.provider_health.consecutive_failures,
                "avg_latency_ms": round(a.provider_health.avg_latency_ms, 1),
                "available_credentials": sum(1 for c in a.provider_health.credentials if c.is_available),
                "total_credentials": len(a.provider_health.credentials),
            }
            for a in self._adapters
        }
