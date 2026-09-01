"""
Web Search Service — DuckDuckGo Fallback
==========================================
Provides a lightweight, zero-API-key web search capability using the
duckduckgo-search library. Used by the Librarian agent as a fallback
when a student's internal notes are insufficient to answer a query.
"""

from app.core.logging import logger
from typing import Optional


async def perform_web_search(query: str, max_results: int = 3) -> list[dict]:
    """
    Search the web using DuckDuckGo and return structured results.

    Returns a list of dicts, each containing:
      - title: str
      - snippet: str
      - url: str

    Returns an empty list if the search fails or yields no results.
    The max_results parameter caps the number of results to control latency/cost.
    """
    if not query or not query.strip():
        return []

    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query.strip(), max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
        return results

    except ImportError:
        logger.info("[WebSearch] ddgs is not installed. Skipping web fallback.")
        return []
    except Exception as e:
        logger.error(f"[WebSearch] DuckDuckGo search failed: {e}")
        return []
