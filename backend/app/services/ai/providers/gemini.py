"""
Gemini Provider Implementation
==============================
Handles Gemini 3.x Flash, Flash-Lite, multimodal vision OCR, embeddings, and image generation.
"""
import httpx
import json
import logging
import re
import time
from typing import List, Dict, Any, Optional
from ..base import AIProvider, LLMResponse
from app.core.config import settings


def repair_json_str(text: str) -> str:
    """Strip markdown fences, trailing commas, double braces, and unescaped newlines."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # Fix double-brace wrapping ({{ ... }}) from some LLMs
    while text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1].strip()
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def safe_parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON with multi-stage fallback repair and unescaped control character tolerance."""
    try:
        return json.loads(text, strict=False)
    except Exception:
        pass

    repaired = repair_json_str(text)
    try:
        return json.loads(repaired, strict=False)
    except Exception:
        pass

    # Escape unescaped newlines inside quotes
    try:
        fixed_newlines = re.sub(r'[\r\n]+', r'\\n', repaired)
        return json.loads(fixed_newlines, strict=False)
    except Exception:
        pass

    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', repaired)
    if match:
        try:
            return json.loads(match.group(1), strict=False)
        except Exception:
            try:
                fixed_newlines = re.sub(r'[\r\n]+', r'\\n', match.group(1))
                return json.loads(fixed_newlines, strict=False)
            except Exception:
                pass

    raise ValueError(f"Could not parse JSON response from LLM. Snippet: {text[:200]}")


_logger = logging.getLogger("teachgenie.ai.gemini")


class GeminiProvider(AIProvider):
    DEFAULT_MODEL = getattr(settings, "GEMINI_PRIMARY_MODEL", "gemini-3.8-flash")
    FALLBACK_MODELS = [getattr(settings, "GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")]
    EMBEDDING_MODEL = "gemini-embedding-001"

    def __init__(self, api_key: Optional[str] = None, image_api_key: Optional[str] = None):
        super().__init__(name="gemini")
        raw_key = (api_key or settings.GEMINI_API_KEY or settings.GEMINI_API_KEYS or "").strip()
        self.api_key = raw_key.split(",")[0].strip() if raw_key else ""
        raw_img = (image_api_key or settings.GEMINI_IMAGE_API_KEY or self.api_key).strip()
        self.image_api_key = raw_img.split(",")[0].strip() if raw_img else self.api_key

    def _build_payload(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Dict[str, Any]:
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant" or role == "model":
                gemini_contents.append({"role": "model", "parts": [{"text": content}]})

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        return payload

    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> LLMResponse:
        models_to_try = [model or self.DEFAULT_MODEL] + [m for m in self.FALLBACK_MODELS if m != model]
        last_error = None
        budget_start = time.time()

        for target_model in models_to_try:
            # Budget check: stop trying more models if caller's timeout is exhausted
            elapsed = time.time() - budget_start
            remaining = timeout - elapsed
            if remaining <= 2.0:
                last_error = f"Gemini budget exhausted after {elapsed:.1f}s (limit {timeout}s)"
                break

            # Per-model timeout: at most 30s or remaining budget, whichever is smaller
            per_model_timeout = min(30.0, remaining)

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
            payload = self._build_payload(messages, temperature, max_tokens)
            start_t = time.time()

            try:
                async with httpx.AsyncClient(timeout=per_model_timeout) as client:
                    resp = await client.post(url, json=payload)
                    latency = (time.time() - start_t) * 1000

                    if resp.status_code == 404 or resp.status_code == 429:
                        last_error = f"Status {resp.status_code}: {resp.text[:200]}"
                        if resp.status_code == 404:
                            _logger.warning(
                                f"Gemini 404 for model '{target_model}'. If ALL models return 404, "
                                "your API key may be a deprecated standard key. Google requires "
                                "authorization keys as of September 2026 — regenerate at https://aistudio.google.com/"
                            )
                        continue
                    resp.raise_for_status()

                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError(f"No candidates returned from {target_model}")

                    text = candidates[0]["content"]["parts"][0]["text"]
                    usage = data.get("usageMetadata", {})
                    
                    return LLMResponse(
                        text=text,
                        provider="gemini",
                        model=target_model,
                        tokens_prompt=usage.get("promptTokenCount", 0),
                        tokens_completion=usage.get("candidatesTokenCount", 0),
                        latency_ms=latency,
                    )
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"GeminiProvider failed across all models: {last_error}")

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
        )
        return safe_parse_json(response.text)

    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> List[List[float]]:
        if not texts:
            return []

        target_model = model or self.EMBEDDING_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:batchEmbedContents?key={self.api_key}"
        
        requests = [{
            "model": f"models/{target_model}",
            "content": {"parts": [{"text": t}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        } for t in texts]

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json={"requests": requests})
            resp.raise_for_status()
            data = resp.json()
            return [item["values"] for item in data.get("embeddings", [])]

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: float = 40.0,
    ) -> Optional[bytes]:
        key = self.image_api_key or self.api_key
        if not key:
            return None

        import base64
        models_to_try = [model or "gemini-3.6-flash", "gemini-3.5-flash"]
        enhanced_prompt = (
            f"Generate a clean, minimal, flat-design educational illustration: {prompt}. "
            "Style: soft muted color palette, no text overlays, no watermarks, "
            "suitable for a professional presentation slide. White or transparent background."
        )
        budget_start = time.time()

        for m in models_to_try:
            # Budget check
            elapsed = time.time() - budget_start
            remaining = timeout - elapsed
            if remaining <= 2.0:
                _logger.warning(f"[GeminiImage] Budget exhausted after {elapsed:.1f}s")
                break

            per_model_timeout = min(20.0, remaining)

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": enhanced_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
            }
            try:
                async with httpx.AsyncClient(timeout=per_model_timeout) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        _logger.warning(
                            f"[GeminiImage] Model '{m}' returned status {resp.status_code}: {resp.text[:200]}"
                        )
                        continue
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            inline_data = part.get("inlineData", {})
                            if "data" in inline_data:
                                return base64.b64decode(inline_data["data"])
            except Exception as e:
                _logger.warning(f"[GeminiImage] Exception for model '{m}': {e}")
                continue
        return None

