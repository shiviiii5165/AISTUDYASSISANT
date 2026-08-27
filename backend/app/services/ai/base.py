"""
AI Provider Abstraction Layer — Base Interfaces and Schemas
===========================================================
Defines the generic AI provider contract, response models, and capability flags.
Allows transparent swapping and routing between Gemini, Groq, OpenRouter, etc.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time


class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    latency_ms: float = 0.0
    raw_json: Optional[Dict[str, Any]] = None


class AIProvider(ABC):
    """Abstract base class for all LLM and AI service providers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> LLMResponse:
        """Generate text from chat messages."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Generate structured JSON response."""
        pass

    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """Optional embedding generation."""
        raise NotImplementedError(f"Embedding generation not implemented for {self.name}")

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
    ) -> Optional[bytes]:
        """Optional image generation."""
        raise NotImplementedError(f"Image generation not implemented for {self.name}")

    async def health_check(self) -> bool:
        """Check if provider is responsive and operational."""
        return True
