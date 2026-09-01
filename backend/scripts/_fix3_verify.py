"""Live verification of Fix 3 — dead GEMINI_IMAGE_API_KEY removed & handled gracefully.
Runs in-process against the SAME .env the running server loaded (root .env)."""
import asyncio, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services.ai.providers.gemini import GeminiProvider
from app.services.embedding_service import _gemini_keys

DEAD = "AQ.Ab8RN6LFfON7nsNvEWDSvbWvH3NLpqPz-AOnQhy7jQ6yflbowQ"
def mask(v): return (v[:6] + "..." + v[-6:]) if v and len(v) > 12 else repr(v)

print("=" * 60); print("FIX 3 — dead image key removed / graceful handling"); print("=" * 60)

print(f"settings.GEMINI_IMAGE_API_KEY raw = {settings.GEMINI_IMAGE_API_KEY!r}")

# 1) Provider with current env: image key must fall back to the LIVE primary, not the dead key
p = GeminiProvider()
print(f"provider.api_key        = {mask(p.api_key)}")
print(f"provider.image_api_key  = {mask(p.image_api_key)}")
print(f"image_api_key is dead?  = {p.image_api_key == DEAD}")

# 2) Embedding rotation pool must no longer contain the dead key
pool = _gemini_keys()
print(f"\nembedding pool ({len(pool)} keys): {[mask(k) for k in pool]}")
print(f"dead key still in embedding pool? = {DEAD in pool}")

# 3) Graceful handling when NO key is available at all (fail-fast, returns None, no exception)
async def _run():
    empty = GeminiProvider(api_key="", image_api_key="")
    print(f"\n[absent-key provider] api_key={empty.api_key!r} image_api_key={empty.image_api_key!r}")
    res = await empty.generate_image("a simple circle")
    print(f"[absent-key] generate_image() -> {type(res).__name__} ({'None (graceful)' if res is None else str(len(res))+' bytes'})")

    # 4) Real provider: generate_image should not raise and should not use the dead key.
    real_res = await p.generate_image("a simple blue circle on white background")
    print(f"[live provider] generate_image() -> {type(real_res).__name__} "
          f"({'None (fell through cleanly)' if real_res is None else str(len(real_res))+' bytes'})")

asyncio.run(_run())

ok = (settings.GEMINI_IMAGE_API_KEY == "" and p.image_api_key != DEAD and DEAD not in pool)
print("\nRESULT:", "PASS — dead key gone from image slot + embedding pool; absent key handled gracefully"
      if ok else "FAIL")
