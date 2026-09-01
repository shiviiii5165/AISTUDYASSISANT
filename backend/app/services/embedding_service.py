import time
import httpx
from app.core.config import settings


def _gemini_keys() -> list[str]:
    """Primary key plus any comma-separated pool keys, de-duplicated, order-preserving."""
    keys = [settings.GEMINI_API_KEY.strip()]
    for k in settings.GEMINI_API_KEYS.split(","):
        k = k.strip()
        if k:
            keys.append(k)
    seen, out = set(), []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks using Gemini REST API.

    Retries with backoff and rotates across the key pool on rate limits (429) or
    transient 5xx errors, so a temporary quota blip no longer surfaces as an opaque
    500 on the chat endpoint.
    """
    if not texts:
        return []

    print(f"Generating Gemini embeddings for {len(texts)} chunks via REST...")

    requests = [
        {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
        }
        for text in texts
    ]
    payload = {"requests": requests}

    keys = _gemini_keys()
    max_attempts = max(3, len(keys))
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        key = keys[attempt % len(keys)]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-embedding-001:batchEmbedContents?key={key}"
        )
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = httpx.HTTPStatusError(
                    f"{resp.status_code} from embedding API", request=resp.request, response=resp
                )
                backoff = min(8.0, 1.5 * (attempt + 1))
                print(f"Embedding API {resp.status_code} (attempt {attempt + 1}/{max_attempts}); "
                      f"rotating key and retrying in {backoff:.1f}s")
                time.sleep(backoff)
                continue
            resp.raise_for_status()
            data = resp.json()
            embeddings = []
            if "embeddings" in data:
                for item in data["embeddings"]:
                    embeddings.append(item["values"])
            return embeddings
        except Exception as e:
            last_exc = e
            print(f"Gemini Embedding Error (attempt {attempt + 1}/{max_attempts}): {e}")
            time.sleep(min(8.0, 1.5 * (attempt + 1)))

    # Exhausted retries — raise so the caller can surface a clear, retryable error.
    raise last_exc if last_exc else RuntimeError("Embedding generation failed")
