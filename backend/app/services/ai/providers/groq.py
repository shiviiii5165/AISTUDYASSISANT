"""
Groq Provider Implementation
============================
Handles high-speed inference on Groq (Llama 4 Scout 17B MoE).
"""
import httpx
import json
import re
import time
from typing import List, Dict, Any, Optional
from ..base import AIProvider, LLMResponse
from .gemini import safe_parse_json
from app.core.config import settings


class GroqProvider(AIProvider):
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODELS = ["mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="groq")
        raw_key = (api_key or settings.GROQ_API_KEY or getattr(settings, "GROQ_API_KEYS", "") or "").strip()
        self.api_key = raw_key.split(",")[0].strip() if raw_key else ""

    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        models_to_try = [model or self.DEFAULT_MODEL] + [m for m in self.FALLBACK_MODELS if m != model]
        last_err = None
        budget_start = time.time()

        for target_model in models_to_try:
            # Budget check: stop trying more models if caller's timeout is exhausted
            elapsed = time.time() - budget_start
            remaining = timeout - elapsed
            if remaining <= 2.0:
                last_err = f"Groq budget exhausted after {elapsed:.1f}s (limit {timeout}s)"
                break

            # Per-model timeout: at most 30s or remaining budget, whichever is smaller
            per_model_timeout = min(30.0, remaining)

            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                payload["response_format"] = response_format

            start_t = time.time()
            try:
                async with httpx.AsyncClient(timeout=per_model_timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    latency = (time.time() - start_t) * 1000

                    if resp.status_code != 200:
                        last_err = f"Groq {target_model} error {resp.status_code}: {resp.text[:200]}"
                        continue

                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError(f"Groq {target_model}: no choices returned")

                    text = choices[0]["message"]["content"]
                    usage = data.get("usage", {})
                    return LLMResponse(
                        text=text,
                        provider="groq",
                        model=target_model,
                        tokens_prompt=usage.get("prompt_tokens", 0),
                        tokens_completion=usage.get("completion_tokens", 0),
                        latency_ms=latency,
                    )
            except Exception as e:
                last_err = str(e)
                continue

        raise RuntimeError(f"GroqProvider failed: {last_err}")

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        response = await self.generate_text(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
        return safe_parse_json(response.text)
