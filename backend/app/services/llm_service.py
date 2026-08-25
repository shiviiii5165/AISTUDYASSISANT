import re
import json
import httpx
import asyncio
from app.core.config import settings


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


async def call_gemini(
    messages: list, 
    model: str = "gemini-2.5-flash", 
    temperature: float = 0.3, 
    max_tokens: int = 8192,
    retries: int = 1
) -> str:
    """
    Calls Gemini REST API with retry logic.
    Expects messages in OpenAI format: [{"role": "system"|"user"|"assistant", "content": "..."}]
    Converts to Gemini format.
    """
    api_key = settings.GEMINI_API_KEY.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    gemini_contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "system":
            system_instruction = {
                "parts": [{"text": content}]
            }
        elif role == "user":
            gemini_contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
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
    
    last_error = None
    for attempt in range(1 + retries):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(url, json=payload)
                
                if resp.status_code >= 500:
                    # Transient server error — retry
                    last_error = Exception(f"Gemini API 5xx error (attempt {attempt+1}): {resp.status_code}")
                    if attempt < retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                        continue
                    raise last_error
                
                if resp.status_code != 200:
                    print(f"Gemini API Error: {resp.text}")
                    raise Exception(f"Gemini API failed with status {resp.status_code}: {resp.text[:200]}")
                    
                response_data = resp.json()
                if "candidates" not in response_data or not response_data["candidates"]:
                    raise Exception("No content returned from Gemini.")
                
                return response_data["candidates"][0]["content"]["parts"][0]["text"]
                
        except httpx.TimeoutException:
            last_error = Exception(f"Gemini API timeout (attempt {attempt+1})")
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise last_error
    
    raise last_error or Exception("Gemini API call failed after all retries")
