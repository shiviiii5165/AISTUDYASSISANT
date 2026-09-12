import time
import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger("teachgenie.ai.circuit_breaker")

class ProviderState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OPEN = "open"          # Circuit is open (failing fast)
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    """Tracks provider health and enforces circuit breaker pattern to avoid retry storms."""
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        
        self.state = ProviderState.HEALTHY
        self.failures = 0
        self.last_failure_time = 0.0

    def record_success(self):
        """Records a successful request, resetting failures if healthy/half-open."""
        if self.state in [ProviderState.OPEN, ProviderState.HALF_OPEN]:
            logger.info("Circuit breaker closed (recovered).")
        self.failures = 0
        self.state = ProviderState.HEALTHY

    def record_failure(self):
        """Records a failure and potentially opens the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold and self.state != ProviderState.OPEN:
            self.state = ProviderState.OPEN
    def record_terminal_failure(self, cooldown_seconds: int = 3600):
        """Immediately trips circuit breaker for persistent errors like 402 Payment Required."""
        self.state = ProviderState.OPEN
        self.last_failure_time = time.time()
        self.cooldown_seconds = cooldown_seconds
        logger.warning(f"Circuit breaker TERMINALLY TRIPPED. Cooldown set to {cooldown_seconds}s.")

    def can_execute(self) -> bool:
        """Determines if a request should be allowed to proceed."""
        if self.state == ProviderState.HEALTHY:
            return True
            
        if self.state == ProviderState.OPEN:
            # Check if cooldown has passed
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = ProviderState.HALF_OPEN
                logger.info("Circuit breaker HALF-OPEN (testing recovery).")
                return True
            return False
            
        if self.state == ProviderState.HALF_OPEN:
            # Only allow a single test request through; if it fails, it will trip again quickly
            return True
            
        return True


class ProviderHealthManager:
    """Manages circuit breakers for all registered AI providers."""
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, provider_name: str) -> CircuitBreaker:
        if provider_name not in self.breakers:
            self.breakers[provider_name] = CircuitBreaker()
        return self.breakers[provider_name]

    def can_use_provider(self, provider_name: str) -> bool:
        return self.get_breaker(provider_name).can_execute()

    def record_success(self, provider_name: str):
        self.get_breaker(provider_name).record_success()

    def record_failure(self, provider_name: str):
        self.get_breaker(provider_name).record_failure()

    def record_terminal_failure(self, provider_name: str, cooldown_seconds: int = 3600):
        self.get_breaker(provider_name).record_terminal_failure(cooldown_seconds)

# Global health manager
health_manager = ProviderHealthManager()
