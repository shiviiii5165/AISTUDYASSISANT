"""
OpenRouter / Extensible Provider Implementation
================================================
Generic OpenAI-compatible provider for OpenRouter, Cerebras, and Cloudflare workers.
"""
import httpx
import time
from typing import List, Dict, Any, Optional
from ..base import AIProvider, LLMResponse
from .gemini import safe_parse_json


from app.core.config import settings


class OpenRouterProvider(AIProvider):
    def __init__(self, api_key: str = "", base_url: str = "https://openrouter.ai/api/v1"):
        super().__init__(name="openrouter")
        self.api_key = (api_key or getattr(settings, "OPENROUTER_API_KEY", "")).strip()
        self.base_url = base_url

    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "meta-llama/llama-3.3-70b-instruct",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        start_t = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start_t) * 1000
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=text,
                provider="openrouter",
                model=model or "meta-llama/llama-3.3-70b-instruct",
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_completion=usage.get("completion_tokens", 0),
                latency_ms=latency,
            )

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        response = await self.generate_text(messages, model, temperature, max_tokens, timeout)
        return safe_parse_json(response.text)
