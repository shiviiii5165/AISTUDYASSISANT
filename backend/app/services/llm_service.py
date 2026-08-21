import httpx
from app.core.config import settings

async def call_gemini(
    messages: list, 
    model: str = "gemini-2.5-flash", 
    temperature: float = 0.3, 
    max_tokens: int = 3000
) -> str:
    """
    Calls Gemini REST API.
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
        
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            print(f"Gemini API Error: {resp.text}")
            raise Exception(f"Gemini API failed with status {resp.status_code}: {resp.text[:200]}")
            
        response_data = resp.json()
        if "candidates" not in response_data or not response_data["candidates"]:
            raise Exception("No content returned from Gemini.")
        
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
