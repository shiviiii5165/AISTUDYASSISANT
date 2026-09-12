"""
Cost-Aware Model Router
=======================
Routes AI tasks (planning, content batches, technical reasoning, QA repair, images, embeddings)
to the optimal provider based on task cost, speed, and capability.
Provides graceful fallback cascade on provider failures without racing multiple models by default.
"""
import asyncio
import logging
import time
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
        # Task -> Preferred Provider & Model Mapping (Adheres strictly to user specification)
        self.task_policies = {
            "planning": [
                ("gemini", "gemini-3.8-flash"),
                ("gemini", "gemini-3.6-flash"),
                ("groq", "openai/gpt-oss-120b"),
                ("groq", "qwen/qwen3.8-27b"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "doubt_tutor": [
                ("groq", "openai/gpt-oss-120b"),
                ("gemini", "gemini-3.8-flash"),
                ("groq", "qwen/qwen3.8-27b"),
                ("gemini", "gemini-3.6-flash"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "semantic_qa": [
                ("groq", "openai/gpt-oss-120b"),
                ("gemini", "gemini-3.8-flash"),
                ("groq", "qwen/qwen3.8-27b"),
                ("gemini", "gemini-3.6-flash"),
            ],
            "content_generation": [
                ("gemini", "gemini-3.8-flash"),
                ("gemini", "gemini-3.6-flash"),
                ("groq", "openai/gpt-oss-120b"),
                ("groq", "qwen/qwen3.8-27b"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "technical_content": [
                ("gemini", "gemini-3.8-flash"),
                ("gemini", "gemini-3.6-flash"),
                ("groq", "openai/gpt-oss-120b"),
                ("groq", "qwen/qwen3.8-27b"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "repair": [
                ("gemini", "gemini-3.8-flash"),
                ("gemini", "gemini-3.6-flash"),
                ("groq", "openai/gpt-oss-120b"),
                ("groq", "qwen/qwen3.8-27b"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "qa": [
                ("gemini", "gemini-3.8-flash"),
                ("gemini", "gemini-3.6-flash"),
                ("groq", "openai/gpt-oss-120b"),
                ("groq", "qwen/qwen3.8-27b"),
                ("openrouter", "openai/gpt-4o"),
            ],
            "embedding": [
                ("gemini", "gemini-embedding-001"),
            ],
            "image": [
                ("gemini", "gemini-3.8-flash"),
            ]
        }
        self.last_routed_calls: Dict[str, Dict[str, Any]] = {}

    def get_last_routed(self, task: str) -> Optional[Dict[str, Any]]:
        return self.last_routed_calls.get(task)

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
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> LLMResponse:
        if messages is None:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        policies = self.task_policies.get(task, [("groq", "qwen/qwen3.8-27b"), ("gemini", "gemini-3.6-flash")])
        errors = []
        budget_start = time.time()

        for provider_name, model_name in policies:
            # Budget check: stop trying more providers if caller's timeout is exhausted
            elapsed = time.time() - budget_start
            remaining = timeout - elapsed
            if remaining <= 2.0:
                errors.append(f"router: budget exhausted after {elapsed:.1f}s")
                break

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
                    timeout=min(remaining, 30.0),
                )
                health_manager.record_success(provider_name)
                self.last_routed_calls[task] = {"provider": provider_name, "model": model_name, "timestamp": time.time()}
                return res
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Provider {provider_name}/{model_name} failed for task '{task}': {err_str[:120]}")
                if "402" in err_str or "Payment Required" in err_str:
                    health_manager.record_terminal_failure(provider_name, cooldown_seconds=3600)
                else:
                    health_manager.record_failure(provider_name)
                errors.append(f"{provider_name}: {err_str[:120]}")

        raise RuntimeError(f"All providers exhausted for task '{task}'. Errors: {' | '.join(errors)}")

    async def generate_json(
        self,
        task: str,
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        if messages is None:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        policies = self.task_policies.get(task, [("gemini", "gemini-3.8-flash"), ("groq", "openai/gpt-oss-120b")])
        errors = []
        budget_start = time.time()

        for provider_name, model_name in policies:
            # Budget check: stop trying more providers if caller's timeout is exhausted
            elapsed = time.time() - budget_start
            remaining = timeout - elapsed
            if remaining <= 2.0:
                errors.append(f"router: budget exhausted after {elapsed:.1f}s")
                break

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
                    timeout=min(remaining, 30.0),
                )
                health_manager.record_success(provider_name)
                self.last_routed_calls[task] = {"provider": provider_name, "model": model_name, "timestamp": time.time()}
                return res
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Provider {provider_name}/{model_name} failed JSON generation for task '{task}': {err_str[:120]}")
                if "402" in err_str or "Payment Required" in err_str:
                    health_manager.record_terminal_failure(provider_name, cooldown_seconds=3600)
                else:
                    health_manager.record_failure(provider_name)
                errors.append(f"{provider_name}: {err_str[:120]}")

        raise RuntimeError(f"All providers exhausted for JSON task '{task}'. Errors: {' | '.join(errors)}")

    async def generate_embeddings(self, texts: List[str], timeout: float = 30.0) -> List[List[float]]:
        try:
            return await asyncio.wait_for(
                self.gemini.generate_embeddings(texts, timeout=timeout),
                timeout=timeout + 5.0,
            )
        except asyncio.TimeoutError:
            logger.error(f"[Router] generate_embeddings timed out after {timeout}s")
            raise

    async def generate_image(self, prompt: str, timeout: float = 40.0) -> Optional[bytes]:
        try:
            return await asyncio.wait_for(
                self.gemini.generate_image(prompt, timeout=timeout),
                timeout=timeout + 5.0,
            )
        except asyncio.TimeoutError:
            logger.error(f"[Router] generate_image timed out after {timeout}s for prompt: {prompt[:60]}")
            return None
        except Exception as e:
            logger.error(f"[Router] generate_image failed: {e}")
            return None


# Singleton router instance
router = ModelRouter()
model_router = router

