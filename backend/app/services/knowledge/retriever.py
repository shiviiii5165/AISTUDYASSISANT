"""
Knowledge Retriever
===================
Provides lightweight, token-efficient context for presentation planning and slide generation.
"""
from typing import List, Dict, Any, Optional
from .sources import KnowledgeChunk, SourceRef
from .hybrid_search import hybrid_search_document
from app.db.supabase_client import supabase


async def get_topic_overview_context(
    document_id: str,
    user_id: str,
    topic: str,
    max_chunks: int = 12,
) -> str:
    """Retrieve broad overview chunks of a document to guide the Planner Agent."""
    if not document_id:
        return ""

    chunks = await hybrid_search_document(
        document_id=document_id,
        user_id=user_id,
        query=f"{topic} overview introduction concepts summary architecture fundamentals",
        top_k=max_chunks,
    )
    if not chunks:
        # Fallback: get first few chunks in document
        try:
            res = supabase.table("document_chunks")\
                .select("chunk_text, page_number")\
                .eq("pdf_id", document_id)\
                .order("page_number")\
                .limit(max_chunks)\
                .execute()
            if res.data:
                chunks = [KnowledgeChunk(document_id=document_id, page_number=r.get("page_number", 0), text=r.get("chunk_text", "")) for r in res.data]
        except Exception:
            return ""

    formatted_lines = []
    for c in chunks:
        page_str = f"[Page {c.page_number}]" if c.page_number > 0 else "[Notes]"
        formatted_lines.append(f"{page_str} {c.text}")
    return "\n\n---\n\n".join(formatted_lines)


async def get_slide_context(
    document_id: str,
    user_id: str,
    slide_title: str,
    key_message: str = "",
    top_k: int = 4,
) -> tuple[str, List[SourceRef]]:
    """Retrieve targeted chunks for a specific slide during content expansion."""
    if not document_id:
        return "", []

    query = f"{slide_title} {key_message}".strip()
    chunks = await hybrid_search_document(
        document_id=document_id,
        user_id=user_id,
        query=query,
        top_k=top_k,
    )

    if not chunks:
        return "", []

    formatted = []
    refs = []
    seen_pages = set()

    for c in chunks:
        page_str = f"Page {c.page_number}" if c.page_number > 0 else "Notes"
        formatted.append(f"[{page_str}]: {c.text}")
        
        if c.page_number not in seen_pages:
            seen_pages.add(c.page_number)
            refs.append(SourceRef(
                source_type="pdf",
                document_id=document_id,
                page=c.page_number if c.page_number > 0 else None,
                snippet=c.text[:120] + "..." if len(c.text) > 120 else c.text,
            ))

    return "\n\n".join(formatted), refs
