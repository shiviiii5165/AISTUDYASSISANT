"""
Image Source Router
===================
Coordinates a prioritized stock photo provider chain:
1. Pexels API (primary)
2. Pixabay API (fallback 1)
3. Unsplash API (fallback 2)
4. Wikimedia Commons (zero-key open educational fallback)
5. AI ModelRouter Image Generation (last resort)

Performs deterministic relevance scoring of candidate metadata against image_query,
caches results in persistent Supabase storage with 30-day TTL and versioning,
and logs all operations loudly (never silent failures).
"""
from app.core.logging import logger
import asyncio
import re
import hashlib
import io
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from PIL import Image
from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.ai import router

IMAGE_CACHE_VERSION = 1
IMAGE_TTL_DAYS = 30
USER_AGENT = "LearnByGenieEduBot/1.0 (https://learnbygenie.online; support@learnbygenie.online)"


def compute_image_query_hash(query: str) -> str:
    """Compute normalized SHA256 for image query."""
    clean = re.sub(r"[^\w\s]", "", query.strip().lower())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def score_relevance(query: str, metadata_text: str) -> float:
    """
    Computes keyword overlap score between image_query and returned metadata (tags/alt-text/title).
    Returns ratio of matched meaningful query terms (0.0 to 1.0).
    """
    stopwords = {"with", "from", "that", "this", "into", "over", "under", "about", "scene", "showing", "system", "real", "photography", "professional", "image", "photo", "demonstration"}
    q_words = [re.sub(r"[^\w]", "", w.lower()) for w in query.split()]
    meaningful = [w for w in q_words if len(w) > 2 and w not in stopwords]
    if not meaningful:
        return 1.0

    meta_lower = metadata_text.lower()
    matches = sum(1 for w in meaningful if w in meta_lower)
    return matches / len(meaningful)


async def get_cached_image(query_hash: str) -> Optional[bytes]:
    """Retrieve cached image bytes from Supabase with TTL check."""
    if not supabase:
        return None
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        # Check dedicated image_cache table
        res = supabase.table("image_cache")\
            .select("image_url, metadata, expires_at")\
            .eq("query_hash", query_hash)\
            .eq("version", IMAGE_CACHE_VERSION)\
            .gte("expires_at", now_iso)\
            .execute()
        if res.data and len(res.data) > 0:
            cached_url = res.data[0].get("image_url")
            if cached_url:
                logger.info(f"[ImageRouter] Persistent image cache HIT: downloading {cached_url[:60]}...")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    img_resp = await client.get(cached_url, headers={"User-Agent": USER_AGENT})
                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                        return img_resp.content
    except Exception:
        # Fallback check on deck_cache table
        try:
            deck_res = supabase.table("deck_cache")\
                .select("deck_json")\
                .eq("topic", f"image_v{IMAGE_CACHE_VERSION}_{query_hash}")\
                .execute()
            if deck_res.data and len(deck_res.data) > 0:
                payload = deck_res.data[0]["deck_json"]
                exp_str = payload.get("expires_at")
                if exp_str and datetime.fromisoformat(exp_str) >= datetime.now(timezone.utc):
                    url = payload.get("image_url")
                    if url:
                        logger.info(f"[ImageRouter] Persistent deck_cache HIT: downloading {url[:60]}...")
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            img_resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                            if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                                return img_resp.content
        except Exception:
            pass
    return None


async def save_cached_image(query_hash: str, provider: str, image_url: str, metadata: Dict[str, Any]) -> None:
    """Save resolved image metadata to persistent Supabase cache with 30-day TTL."""
    if not supabase:
        return
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=IMAGE_TTL_DAYS)).isoformat()
    try:
        supabase.table("image_cache").upsert({
            "query_hash": query_hash,
            "version": IMAGE_CACHE_VERSION,
            "provider": provider,
            "image_url": image_url,
            "metadata": metadata,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
        }).execute()
        logger.info(f"[ImageRouter] Cached {provider} image in image_cache for query hash {query_hash[:12]}")
    except Exception:
        try:
            supabase.table("deck_cache").upsert({
                "topic": f"image_v{IMAGE_CACHE_VERSION}_{query_hash}",
                "depth": "image",
                "audience": provider,
                "deck_json": {
                    "version": IMAGE_CACHE_VERSION,
                    "provider": provider,
                    "image_url": image_url,
                    "metadata": metadata,
                    "created_at": now.isoformat(),
                    "expires_at": expires_at,
                },
            }).execute()
            logger.info(f"[ImageRouter] Cached {provider} image in deck_cache fallback for {query_hash[:12]}")
        except Exception as err:
            logger.warning(f"[ImageRouter] Could not save image cache: {err}")


async def _fetch_pexels(query: str) -> Optional[tuple[str, str]]:
    """Query Pexels API. Returns (image_url, metadata_text) or None."""
    api_key = settings.PEXELS_API_KEY.strip()
    if not api_key:
        return None
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key, "User-Agent": USER_AGENT}
    params = {"query": query, "per_page": 4, "orientation": "landscape"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                logger.warning(f"[ImageRouter] Pexels API returned status {resp.status_code}: {resp.text[:150]}")
                return None
            data = resp.json()
            photos = data.get("photos", [])
            for photo in photos:
                alt = photo.get("alt", "")
                score = score_relevance(query, alt)
                if score >= 0.25:
                    img_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                    if img_url:
                        return img_url, f"Pexels: {alt}"
            # Fallback to first if available
            if photos:
                return photos[0]["src"].get("large", ""), f"Pexels: {photos[0].get('alt', '')}"
    except Exception as e:
        logger.warning(f"[ImageRouter] Pexels API error: {e}")
    return None


async def _fetch_pixabay(query: str) -> Optional[tuple[str, str]]:
    """Query Pixabay API. Returns (image_url, metadata_text) or None."""
    api_key = settings.PIXABAY_API_KEY.strip()
    if not api_key:
        return None
    url = "https://pixabay.com/api/"
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "orientation": "horizontal",
        "per_page": 4,
        "safesearch": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                logger.warning(f"[ImageRouter] Pixabay API returned status {resp.status_code}: {resp.text[:150]}")
                return None
            data = resp.json()
            hits = data.get("hits", [])
            for hit in hits:
                tags = hit.get("tags", "")
                score = score_relevance(query, tags)
                if score >= 0.25:
                    img_url = hit.get("largeImageURL") or hit.get("webformatURL")
                    if img_url:
                        return img_url, f"Pixabay: {tags}"
            if hits:
                return hits[0].get("largeImageURL") or hits[0].get("webformatURL", ""), f"Pixabay: {hits[0].get('tags', '')}"
    except Exception as e:
        logger.warning(f"[ImageRouter] Pixabay API error: {e}")
    return None


async def _fetch_unsplash(query: str) -> Optional[tuple[str, str]]:
    """Query Unsplash API. Returns (image_url, metadata_text) or None."""
    access_key = settings.UNSPLASH_ACCESS_KEY.strip()
    if not access_key:
        return None
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {access_key}", "User-Agent": USER_AGENT}
    params = {"query": query, "per_page": 4, "orientation": "landscape"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                logger.warning(f"[ImageRouter] Unsplash API returned status {resp.status_code}: {resp.text[:150]}")
                return None
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                desc = f"{item.get('description', '')} {item.get('alt_description', '')}"
                score = score_relevance(query, desc)
                if score >= 0.25:
                    img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("small")
                    if img_url:
                        return img_url, f"Unsplash: {desc}"
            if results:
                return results[0]["urls"].get("regular", ""), f"Unsplash: {results[0].get('alt_description', '')}"
    except Exception as e:
        logger.warning(f"[ImageRouter] Unsplash API error: {e}")
    return None


async def _fetch_wikimedia(query: str) -> Optional[tuple[str, str]]:
    """
    Zero-key open educational fallback via Wikimedia Commons.
    Returns high-resolution educational photographs under Creative Commons.
    """
    url = "https://commons.wikimedia.org/w/api.php"
    # Simplify search query for media search
    clean_q = re.sub(r"[^\w\s]", "", query)
    tokens = [t for t in clean_q.split() if len(t) > 2][:4]
    search_str = " ".join(tokens) + " filetype:bitmap"
    
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": search_str,
        "gsrlimit": "4",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[ImageRouter] Wikimedia Commons returned status {resp.status_code}")
                return None
            pages = resp.json().get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                title = pdata.get("title", "")
                info_list = pdata.get("imageinfo", [])
                if info_list:
                    info = info_list[0]
                    img_url = info.get("url", "")
                    mime = info.get("mime", "")
                    # Only accept standard photographic raster formats
                    if img_url and mime in ["image/jpeg", "image/png", "image/webp"]:
                        score = score_relevance(query, title)
                        if score >= 0.2:
                            return img_url, f"Wikimedia: {title}"
            # Return first valid raster image if present
            for pid, pdata in pages.items():
                info_list = pdata.get("imageinfo", [])
                if info_list:
                    info = info_list[0]
                    img_url = info.get("url", "")
                    mime = info.get("mime", "")
                    if img_url and mime in ["image/jpeg", "image/png"]:
                        return img_url, f"Wikimedia: {pdata.get('title', '')}"
    except Exception as e:
        logger.warning(f"[ImageRouter] Wikimedia Commons search error: {e}")
    return None


async def _resolve_stock_image_inner(image_query: str) -> Optional[bytes]:
    """
    Inner implementation: resolves a concrete image_query to image bytes.
    1. Checks persistent Supabase cache.
    2. Sequentially tries Pexels -> Pixabay -> Unsplash -> Wikimedia Commons.
    3. Downloads and validates bytes.
    4. Falls back to AI image generation if stock providers yield nothing.
    """
    if not image_query or not image_query.strip():
        return None

    query = image_query.strip()
    q_hash = compute_image_query_hash(query)

    # 1. Check Persistent Supabase Cache
    cached_bytes = await get_cached_image(q_hash)
    if cached_bytes:
        return cached_bytes

    logger.info(f"[ImageRouter] Resolving stock photo for query: '{query}'")

    providers = [
        ("pexels", _fetch_pexels),
        ("pixabay", _fetch_pixabay),
        ("unsplash", _fetch_unsplash),
        ("wikimedia", _fetch_wikimedia),
    ]

    for prov_name, fetch_func in providers:
        candidate = await fetch_func(query)
        if candidate:
            img_url, meta_desc = candidate
            logger.info(f"[ImageRouter] Provider {prov_name} found match: {meta_desc[:60]} -> {img_url[:70]}...")
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    img_resp = await client.get(img_url, headers={"User-Agent": USER_AGENT})
                    if img_resp.status_code == 200 and len(img_resp.content) > 2000:
                        # Validate that Pillow can read image bytes
                        try:
                            im = Image.open(io.BytesIO(img_resp.content))
                            im.verify()
                        except Exception as img_val_err:
                            logger.warning(f"[ImageRouter] Corrupted image bytes from {prov_name}: {img_val_err}")
                            continue

                        # Cache and return
                        await save_cached_image(q_hash, prov_name, img_url, {"description": meta_desc})
                        return img_resp.content
                    else:
                        logger.warning(f"[ImageRouter] Failed to download {prov_name} image bytes (status {img_resp.status_code})")
            except Exception as dl_err:
                logger.warning(f"[ImageRouter] Download exception for {prov_name}: {dl_err}")

    # 5. Last-Resort Fallback: AI image generation via router (capped at 20s)
    logger.info(f"[ImageRouter] Stock providers exhausted for '{query}'. Attempting AI generation fallback...")
    try:
        ai_bytes = await asyncio.wait_for(router.generate_image(query, timeout=18.0), timeout=20.0)
        if ai_bytes:
            logger.info(f"[ImageRouter] AI image generation succeeded for '{query}'")
            return ai_bytes
    except asyncio.TimeoutError:
        logger.warning(f"[ImageRouter] AI image generation timed out for '{query}'")
    except Exception as ai_err:
        logger.warning(f"[ImageRouter] AI image generation fallback failed: {ai_err}")

    logger.warning(f"[ImageRouter] Zero images resolved for '{query}'. Slide will use deterministic diagram/text layout.")
    return None


async def resolve_stock_image(image_query: str) -> Optional[bytes]:
    """
    Main entry point: resolves a concrete image_query to image bytes.
    Wraps inner implementation in a hard 25-second timeout to prevent hangs.
    """
    try:
        return await asyncio.wait_for(_resolve_stock_image_inner(image_query), timeout=25.0)
    except asyncio.TimeoutError:
        logger.warning(f"[ImageRouter] resolve_stock_image hard-timeout (25s) for query: '{image_query[:60]}'")
        return None

