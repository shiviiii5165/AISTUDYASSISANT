"""
Cost-Aware Model Router
=======================
Routes AI tasks (planning, content batches, technical reasoning, QA repair, images, embeddings)
to the optimal provider based on task cost, speed, and capability.
Provides graceful fallback cascade on provider failures without racing multiple models by default.
"""
import logging
from typing import List, Dict, Any, Optional
from .base import AIProvider, LLMResponse
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.openrouter import OpenRouterProvider
from .circuit_breaker import health_manager

logger = logging.getLogger("teachgenie.ai.router")


class ModelRouter:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()
        self.openrouter = OpenRouterProvider()

        # Task -> Preferred Provider & Model Mapping
        self.task_policies = {
            "planning": [
                ("gemini", "gemini-3.6-flash"),
                ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
            ],
            "content_generation": [
                ("gemini", "gemini-3.6-flash"),
                ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
            ],
            "technical_content": [
                ("gemini", "gemini-3.6-flash"),
                ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
            ],
            "repair": [
                ("gemini", "gemini-3.5-flash-lite"),
                ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
            ],
            "qa": [
                ("gemini", "gemini-3.5-flash-lite"),
                ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
            ],
            "embedding": [
                ("gemini", "gemini-embedding-001"),
            ],
            "image": [
                ("gemini", "gemini-2.0-flash"),
            ]
        }

    def _get_provider(self, name: str) -> AIProvider:
        if name == "gemini":
            return self.gemini
        elif name == "groq":
            return self.groq
        elif name == "openrouter":
            return self.openrouter
        raise ValueError(f"Unknown provider name: {name}")

    async def generate_text(
        self,
        task: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> LLMResponse:
        policies = self.task_policies.get(task, [("gemini", "gemini-3.6-flash"), ("groq", "meta-llama/llama-4-scout-17b-16e-instruct")])
        errors = []

        for provider_name, model_name in policies:
            if not health_manager.can_use_provider(provider_name):
                logger.debug(f"Skipping {provider_name} due to open circuit.")
                continue

            try:
                provider = self._get_provider(provider_name)
                res = await provider.generate_text(
                    messages=messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                health_manager.record_success(provider_name)
                return res
            except Exception as e:
                logger.warning(f"Provider {provider_name}/{model_name} failed for task '{task}': {e}")
                health_manager.record_failure(provider_name)
                errors.append(f"{provider_name}: {str(e)[:120]}")

        raise RuntimeError(f"All providers exhausted for task '{task}'. Errors: {' | '.join(errors)}")

    async def generate_json(
        self,
        task: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        policies = self.task_policies.get(task, [("gemini", "gemini-3.6-flash"), ("groq", "meta-llama/llama-4-scout-17b-16e-instruct")])
        errors = []

        for provider_name, model_name in policies:
            if not health_manager.can_use_provider(provider_name):
                logger.debug(f"Skipping {provider_name} due to open circuit.")
                continue

            try:
                provider = self._get_provider(provider_name)
                res = await provider.generate_json(
                    messages=messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                health_manager.record_success(provider_name)
                return res
            except Exception as e:
                logger.warning(f"Provider {provider_name}/{model_name} failed JSON generation for task '{task}': {e}")
                health_manager.record_failure(provider_name)
                errors.append(f"{provider_name}: {str(e)[:120]}")

        raise RuntimeError(f"All providers exhausted for JSON task '{task}'. Errors: {' | '.join(errors)}")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return await self.gemini.generate_embeddings(texts)

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        return await self.gemini.generate_image(prompt)


# Singleton router instance
router = ModelRouter()
