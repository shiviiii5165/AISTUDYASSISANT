import re
import json
import httpx
import asyncio
from app.core.config import settings


# ══════════════════════════════════════════════════════════════════════════════
# JSON REPAIR UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def repair_json(text: str) -> str:
    """
    Attempt to repair common JSON issues from LLM output:
    - Strip markdown code fences
    - Remove trailing commas before } or ]
    - Fix unescaped newlines inside strings
    """
    text = text.strip()
    
    # Strip markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    # Try to fix unescaped control characters inside strings
    # This handles newlines that appear inside JSON string values
    text = text.replace('\r\n', '\\n').replace('\r', '\\n')
    
    return text


def safe_json_loads(text: str) -> dict:
    """Parse JSON with automatic repair on failure."""
    # First try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try with repair
    repaired = repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    # Last resort: try to find the first { ... } or [ ... ] block
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', repaired)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    raise json.JSONDecodeError(
        f"Could not parse or repair JSON. First 200 chars: {text[:200]}", text, 0
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER DEFINITIONS — Current models as of August 2026
# ══════════════════════════════════════════════════════════════════════════════

# Gemini 3.x series (current generation, ordered by capability)
GEMINI_MODELS = [
    "gemini-3.6-flash",       # Latest stable (July 2026)
    "gemini-3.5-flash",       # Stable production (May 2026)
    "gemini-3.5-flash-lite",  # Lightweight fallback (July 2026)
]

# Groq models (currently active, verified August 2026)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",      # Fast fallback
]


# ══════════════════════════════════════════════════════════════════════════════
# RAW PROVIDER CALLS (no fallback — used as building blocks)
# ══════════════════════════════════════════════════════════════════════════════

async def _call_gemini_raw(
    messages: list,
    model: str = "gemini-3.6-flash",
    temperature: float = 0.3,
    max_tokens: int = 8192,
    api_key: str = None,
) -> str:
    """Direct Gemini REST call. Raises on any error."""
    key = (api_key or settings.GEMINI_API_KEY).strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    gemini_contents = []
    system_instruction = None

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "user":
            gemini_contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            gemini_contents.append({"role": "model", "parts": [{"text": content}]})

    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise Exception(f"Gemini/{model} error {resp.status_code}: {resp.text[:250]}")
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise Exception(f"Gemini/{model}: no candidates returned")
        return candidates[0]["content"]["parts"][0]["text"]


async def _call_groq_raw(
    messages: list,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> str:
    """Direct Groq REST call (OpenAI-compatible). Raises on any error."""
    api_key = settings.GROQ_API_KEY.strip()
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Groq/{model} error {resp.status_code}: {resp.text[:250]}")
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise Exception(f"Groq/{model}: no choices returned")
        return choices[0]["message"]["content"]


# ══════════════════════════════════════════════════════════════════════════════
# SMART ORCHESTRATION — Cascading fallback through all providers
# ══════════════════════════════════════════════════════════════════════════════

async def call_gemini(
    messages: list,
    model: str = "gemini-3.6-flash",
    temperature: float = 0.3,
    max_tokens: int = 8192,
    retries: int = 1,
) -> str:
    """
    RESILIENT LLM call — cascading fallback through ALL available providers.
    
    Order:
      1. Gemini 3.6 Flash (latest stable)
      2. Gemini 3.5 Flash (production stable)
      3. Gemini 3.5 Flash-Lite (lightweight)
      4. Groq Llama 3.3 70B (best Groq model)
      5. Groq Llama 3.1 8B (fast fallback)
    
    If ANY provider succeeds, the user never sees an error.
    """
    errors = []

    # ── Phase 1: Try all Gemini models ──────────────────────────────────────
    # Put the requested model first, then the rest
    gemini_order = [model] + [m for m in GEMINI_MODELS if m != model]
    
    for gm in gemini_order:
        for attempt in range(1 + retries):
            try:
                result = await _call_gemini_raw(
                    messages=messages, model=gm,
                    temperature=temperature, max_tokens=max_tokens,
                )
                if gm != model:
                    print(f"⚡ Primary Gemini/{model} failed, succeeded with Gemini/{gm}")
                return result
            except Exception as e:
                err_str = str(e)
                errors.append(f"Gemini/{gm}[{attempt+1}]: {err_str[:120]}")
                # If it's a 404 or auth error, don't retry the same model
                if "404" in err_str or "401" in err_str or "403" in err_str:
                    break
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))

    # ── Phase 2: Cascade through Groq models ───────────────────────────────
    print(f"⚡ All Gemini models failed, falling back to Groq...")
    
    for gq in GROQ_MODELS:
        try:
            result = await _call_groq_raw(
                messages=messages, model=gq,
                temperature=temperature, max_tokens=max_tokens,
            )
            print(f"✅ Groq/{gq} fallback succeeded")
            return result
        except Exception as e:
            err_str = str(e)
            errors.append(f"Groq/{gq}: {err_str[:120]}")
            # If rate-limited on Groq, wait briefly before next model
            if "429" in err_str:
                await asyncio.sleep(2)

    # ── All providers exhausted ─────────────────────────────────────────────
    error_summary = " | ".join(errors[-4:])  # Show last 4 errors
    raise Exception(f"All {len(errors)} API calls failed. Last errors: {error_summary}")


# ══════════════════════════════════════════════════════════════════════════════
# PARALLEL RACING — Run multiple LLMs simultaneously, pick BEST output
# Used for critical quality-sensitive tasks (PPT outlines, expansions)
# ══════════════════════════════════════════════════════════════════════════════

def _score_json_quality(text: str, required_keys: list = None) -> int:
    """
    Score the quality of an LLM response for content richness.
    Higher = better quality.
    """
    score = 0
    
    # Base score: length (more detailed = better)
    score += min(len(text), 10000)  # Cap at 10k to avoid gaming
    
    # Bonus for valid JSON
    try:
        data = safe_json_loads(text)
        score += 2000  # Big bonus for valid JSON
        
        # Check for required keys
        if required_keys:
            for key in required_keys:
                if key in data:
                    score += 500
        
        # Bonus for rich sections
        sections = data.get("sections", [])
        score += len(sections) * 300
        
        for section in sections:
            # More bullets = better
            bullets = section.get("body_bullets", [])
            score += len(bullets) * 100
            
            # Has example = better
            if section.get("example") and len(str(section.get("example", ""))) > 30:
                score += 400
            
            # Has speaker notes = better
            if section.get("speaker_note") and len(str(section.get("speaker_note", ""))) > 20:
                score += 200
            
            # Has image prompt = better
            if section.get("image_prompt") and len(str(section.get("image_prompt", ""))) > 20:
                score += 150
                
    except Exception:
        pass  # Not valid JSON, no bonus
    
    return score


async def call_best_llm(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    required_json_keys: list = None,
) -> str:
    """
    🏆 PARALLEL RACING — Calls Gemini AND Groq simultaneously.
    Both run at the same time, we pick the HIGHEST QUALITY response.
    If one fails, the other's result is used automatically.
    
    This is the premium path for PPT generation where quality > speed.
    """
    # Launch both providers in parallel
    gemini_task = asyncio.create_task(
        _call_gemini_raw(
            messages=messages,
            model="gemini-3.6-flash",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )
    groq_task = asyncio.create_task(
        _call_groq_raw(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )

    # Wait for both to complete (don't fail on individual errors)
    results = await asyncio.gather(gemini_task, groq_task, return_exceptions=True)
    
    gemini_result = results[0]
    groq_result = results[1]
    
    gemini_ok = not isinstance(gemini_result, Exception)
    groq_ok = not isinstance(groq_result, Exception)
    
    # Both failed → cascade through all providers
    if not gemini_ok and not groq_ok:
        print(f"⚠️ Both parallel calls failed. Gemini: {gemini_result} | Groq: {groq_result}")
        print("🔄 Falling back to cascading fallback chain...")
        return await call_gemini(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    # Only one succeeded → use that
    if gemini_ok and not groq_ok:
        print("🏆 Race result: Only Gemini succeeded")
        return gemini_result
    
    if groq_ok and not gemini_ok:
        print("🏆 Race result: Only Groq succeeded")
        return groq_result
    
    # 🔥 BOTH SUCCEEDED — Pick the BEST quality response
    gemini_score = _score_json_quality(gemini_result, required_json_keys)
    groq_score = _score_json_quality(groq_result, required_json_keys)
    
    winner = "Gemini" if gemini_score >= groq_score else "Groq"
    print(f"🏆 Race result: {winner} wins! (Gemini={gemini_score}, Groq={groq_score})")
    
    return gemini_result if gemini_score >= groq_score else groq_result


async def call_parallel_merge(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> list[str]:
    """
    🔀 PARALLEL MERGE — Calls ALL available providers and returns ALL successful 
    results. Used when we want to MERGE/COMBINE outputs from multiple LLMs
    for maximum richness (e.g., generating slide content from multiple perspectives).
    """
    tasks = [
        asyncio.create_task(_call_gemini_raw(
            messages=messages, model="gemini-3.6-flash",
            temperature=temperature, max_tokens=max_tokens,
        )),
        asyncio.create_task(_call_groq_raw(
            messages=messages, model="llama-3.3-70b-versatile",
            temperature=temperature + 0.1,  # Slightly different temp for diversity
            max_tokens=max_tokens,
        )),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = [r for r in results if not isinstance(r, Exception)]
    
    if not successes:
        # All failed, use cascading fallback
        result = await call_gemini(messages=messages, temperature=temperature, max_tokens=max_tokens)
        return [result]
    
    return successes
