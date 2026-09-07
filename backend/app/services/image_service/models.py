"""
Image Service — Data Models
============================
Core dataclasses for the provider-abstracted image subsystem.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Attribution:
    """Image attribution metadata (required for Unsplash compliance)."""
    photographer_name: str = ""
    photographer_url: str = ""
    source_url: str = ""          # link back to the photo page
    provider: str = ""            # "pexels" | "pixabay" | "unsplash" | "wikimedia"
    license_type: str = "free"    # "free" | "CC-BY" | "Unsplash License"


@dataclass
class ImageResult:
    """Final resolved image returned by ImageService.get_best_image()."""
    image_bytes: bytes
    provider: str                 # which provider served this image
    url: str                      # original image URL (for caching / hotlinking)
    query: str                    # the search query used
    width: int = 0
    height: int = 0
    attribution: Attribution = field(default_factory=Attribution)


@dataclass
class CandidateImage:
    """A single search result candidate before ranking."""
    url: str                      # download URL
    thumbnail_url: str = ""       # preview URL (for Unsplash hotlinking)
    width: int = 0
    height: int = 0
    description: str = ""         # alt text / tags / description
    provider: str = ""
    relevance_score: float = 0.0
    attribution: Attribution = field(default_factory=Attribution)
    # Unsplash-specific: photo ID needed for download tracking
    photo_id: str = ""
    download_url: str = ""        # Unsplash download tracking endpoint


@dataclass
class CredentialHealth:
    """Per-credential health tracking for a single API key."""
    key: str
    provider: str
    failure_count: int = 0
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None   # 429 → 5 min cooldown
    total_requests: int = 0
    total_successes: int = 0

    @property
    def is_available(self) -> bool:
        """Credential is available if not in cooldown."""
        if self.cooldown_until is None:
            return True
        return datetime.now(timezone.utc) >= self.cooldown_until

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0  # optimistic default
        return self.total_successes / self.total_requests

    def record_success(self):
        self.total_requests += 1
        self.total_successes += 1
        self.consecutive_failures = 0

    def record_failure(self, cooldown_seconds: int = 300):
        """Record a failure. If rate-limited (429), set cooldown."""
        self.total_requests += 1
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now(timezone.utc)

    def set_cooldown(self, seconds: int = 300):
        """Set a cooldown period (e.g. 5 min after a 429)."""
        from datetime import timedelta
        self.cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)


@dataclass
class ProviderHealth:
    """Aggregate health for a provider (across all its credentials)."""
    name: str                     # "pexels" | "pixabay" | "unsplash"
    credentials: list = field(default_factory=list)  # list[CredentialHealth]
    avg_latency_ms: float = 200.0
    consecutive_failures: int = 0
    total_requests: int = 0
    total_successes: int = 0

    @property
    def health_score(self) -> float:
        """
        Health score for provider ranking.
        Higher = healthier.  Score = available_creds × success_rate / avg_latency_factor.
        """
        available = sum(1 for c in self.credentials if c.is_available)
        if available == 0:
            return 0.0
        success_rate = self.total_successes / max(self.total_requests, 1)
        latency_factor = max(self.avg_latency_ms, 50.0) / 200.0  # normalize around 200ms
        return available * (0.3 + 0.7 * success_rate) / latency_factor
