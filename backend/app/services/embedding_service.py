import httpx
from app.core.config import settings

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks using Gemini REST API"""
    if not texts:
        return []
        
    print(f"Generating Gemini embeddings for {len(texts)} chunks via REST...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={settings.GEMINI_API_KEY.strip()}"
    
    requests = []
    for text in texts:
        requests.append({
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        })
        
    payload = {"requests": requests}
    
    try:
        # httpx is already installed and async/sync capable. Using sync here.
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            embeddings = []
            if "embeddings" in data:
                for item in data["embeddings"]:
                    embeddings.append(item["values"])
            return embeddings
    except Exception as e:
        print(f"Gemini Embedding Error: {e}")
        raise e
