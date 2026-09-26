"""
Image Service — Abstract Base Adapter
======================================
All provider adapters (Pexels, Pixabay, Unsplash) inherit from this.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from ..models import CandidateImage, CredentialHealth, ProviderHealth


class BaseAdapter(ABC):
    """
    Abstract stock photo provider adapter.
    Each adapter owns its credential pool, performs health-based credential selection,
    and returns normalized CandidateImage results.
    """

    PROVIDER_NAME: str = "base"
    COOLDOWN_SECONDS: int = 300  # 5 minutes after a 429
    USER_AGENT: str = "LearnByGenieEduBot/2.0 (https://teachgenie.online; support@teachgenie.online)"

    def __init__(self, api_keys: List[str]):
        """Initialize with a list of API keys (credential pool)."""
        self._credentials: List[CredentialHealth] = []
        for key in api_keys:
            key = key.strip()
            if key:
                self._credentials.append(CredentialHealth(
                    key=key,
                    provider=self.PROVIDER_NAME,
                ))
        self._health = ProviderHealth(name=self.PROVIDER_NAME, credentials=self._credentials)

    @property
    def is_configured(self) -> bool:
        """True if at least one credential is available."""
        return len(self._credentials) > 0

    @property
    def provider_health(self) -> ProviderHealth:
        return self._health

    def pick_credential(self) -> Optional[CredentialHealth]:
        """
        Select the healthiest available credential.
        Health = success_rate, with preference to credentials with fewer total requests
        (to distribute load, but health-first).
        """
        available = [c for c in self._credentials if c.is_available]
        if not available:
            return None

        # Sort by: success_rate desc, then fewer requests (spread load)
        available.sort(key=lambda c: (c.success_rate, -c.total_requests), reverse=True)
        return available[0]

    def record_success(self, credential: CredentialHealth, latency_ms: float = 0) -> None:
        """Record a successful request for both credential and provider."""
        credential.record_success()
        self._health.total_requests += 1
        self._health.total_successes += 1
        self._health.consecutive_failures = 0
        if latency_ms > 0:
            # Exponential moving average for latency
            self._health.avg_latency_ms = 0.7 * self._health.avg_latency_ms + 0.3 * latency_ms

    def record_failure(self, credential: CredentialHealth, is_rate_limit: bool = False) -> None:
        """Record a failure. If 429, apply cooldown to the specific credential."""
        credential.record_failure()
        self._health.total_requests += 1
        self._health.consecutive_failures += 1
        if is_rate_limit:
            credential.set_cooldown(self.COOLDOWN_SECONDS)

    def health_score(self) -> float:
        """Provider-level health score for cross-provider comparison."""
        return self._health.health_score

    @abstractmethod
    async def search(self, query: str, per_page: int = 5) -> List[CandidateImage]:
        """
        Search this provider for images matching the query.
        Returns a list of CandidateImage results.
        Must handle credential selection, 429s, and health updates internally.
        """
        ...
