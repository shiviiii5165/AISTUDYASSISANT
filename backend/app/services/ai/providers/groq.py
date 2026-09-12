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
    # Logical Allowlist matching user specification
    GROQ_PRODUCTION_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    GROQ_PREVIEW_MODELS = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"]

    _cached_available_models: List[str] = []
    _last_discovery_time: float = 0.0

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="groq")
        raw_key = (api_key or settings.GROQ_API_KEY or getattr(settings, "GROQ_API_KEYS", "") or "").strip()
        self.api_key = raw_key.split(",")[0].strip() if raw_key else ""

    async def get_discovered_models(self) -> List[str]:
        """Discovers live Groq models and intersects with internal allowlist."""
        now = time.time()
        if self._cached_available_models and (now - self._last_discovery_time < 3600):
            return self._cached_available_models

        discovered: List[str] = []
        if not self.api_key:
            return [settings.GROQ_PRIMARY_MODEL]

        try:
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    remote_ids = {m.get("id") for m in resp.json().get("data", [])}
                    # Intersect in strict order: Preferred Production -> Preview -> Remaining
                    for m in self.GROQ_PRODUCTION_MODELS:
                        if m in remote_ids and m not in discovered:
                            discovered.append(m)
                    for m in self.GROQ_PREVIEW_MODELS:
                        if m in remote_ids and m not in discovered:
                            discovered.append(m)
        except Exception as e:
            pass

        if not discovered:
            configured_fallbacks = [m.strip() for m in settings.GROQ_FALLBACK_MODELS.split(",") if m.strip()]
            discovered = [settings.GROQ_PRIMARY_MODEL] + configured_fallbacks

        GroqProvider._cached_available_models = discovered
        GroqProvider._last_discovery_time = now
        return discovered

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

        # Dynamic model cascade selection
        available = await self.get_discovered_models()
        if model and model in available:
            models_to_try = [model] + [m for m in available if m != model]
        elif model:
            models_to_try = [model] + available
        else:
            models_to_try = available

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
        # Groq requires 'json' to be explicitly mentioned in messages when using json_object format
        has_json_instruction = any("json" in m.get("content", "").lower() for m in messages)
        json_messages = list(messages)
        if not has_json_instruction:
            json_messages.insert(0, {"role": "system", "content": "You are an educational assistant. You must respond in valid JSON format."})

        response = await self.generate_text(
            messages=json_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
        return safe_parse_json(response.text)
