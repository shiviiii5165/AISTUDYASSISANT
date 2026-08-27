"""
Multi-Source Hybrid Knowledge Search & Evidence Retriever
=========================================================
Combines vector embeddings, keyword matching, metadata filtering, and
source-aware formatting for PDF, PPT, Handwritten Notes, and YouTube sources.
"""
import re
from typing import List, Dict, Any, Optional, Union
from app.db.supabase_client import supabase
from app.services.ai import router
from .sources import SourceType, EvidenceItem


async def hybrid_search_evidence(
    user_id: str,
    query: str,
    document_ids: Optional[List[str]] = None,
    document_id: Optional[str] = None,
    top_k: int = 5,
    page_filter: Optional[int] = None,
) -> List[EvidenceItem]:
    """
    Performs hybrid vector + keyword search across multiple documents/sources.
    Returns normalized EvidenceItem objects.
    """
    doc_id_list = []
    if document_ids:
        doc_id_list.extend(document_ids)
    if document_id and document_id not in doc_id_list:
        doc_id_list.append(document_id)

    if not doc_id_list:
        return []

    # 1. Fetch document metadata (name, source_type)
    doc_meta_map = {}
    if supabase:
        try:
            res = supabase.table("pdfs")\
                .select("id, name, source_type")\
                .in_("id", doc_id_list)\
                .execute()
            for r in (res.data or []):
                doc_meta_map[r["id"]] = {
                    "name": r.get("name", "Document"),
                    "source_type": r.get("source_type", "pdf"),
                }
        except Exception as e:
            print(f"[HybridSearch] Metadata fetch error: {e}")

    # 2. Vector search via Supabase RPC or direct query
    all_raw_results = []
    try:
        embeddings = await router.generate_embeddings([query])
        query_embedding = embeddings[0] if embeddings else []

        if query_embedding and supabase:
            for d_id in doc_id_list:
                try:
                    rpc_res = supabase.rpc(
                        "match_document_chunks",
                        {
                            "query_embedding": query_embedding,
                            "match_count": top_k * 2,
                            "filter_pdf_id": d_id,
                            "filter_user_id": user_id,
                        }
                    ).execute()
                    if rpc_res.data:
                        for item in rpc_res.data:
                            item["pdf_id"] = d_id
                            all_raw_results.append(item)
                except Exception as rpc_err:
                    print(f"[HybridSearch] RPC match failed for {d_id}: {rpc_err}")
    except Exception as e:
        print(f"[HybridSearch] Vector search failed: {e}")

    # Fallback to direct table query if RPC was empty or unavailable
    if not all_raw_results and supabase:
        for d_id in doc_id_list:
            try:
                res = supabase.table("document_chunks")\
                    .select("id, chunk_text, page_number")\
                    .eq("pdf_id", d_id)\
                    .limit(top_k)\
                    .execute()
                for r in (res.data or []):
                    all_raw_results.append({
                        "pdf_id": d_id,
                        "chunk_text": r.get("chunk_text", ""),
                        "page_number": r.get("page_number", 1),
                        "similarity": 0.6,
                    })
            except Exception as direct_err:
                print(f"[HybridSearch] Direct fallback error: {direct_err}")

    # 3. Process, Keyword-Boost, and Convert to EvidenceItem
    evidence_items: List[EvidenceItem] = []
    query_terms = [t.lower() for t in re.findall(r'\w+', query) if len(t) > 3]

    for item in all_raw_results:
        d_id = item.get("pdf_id", "")
        page = item.get("page_number", 1)
        if page_filter is not None and page != page_filter:
            continue

        text = item.get("chunk_text", "").strip()
        if not text:
            continue

        score = float(item.get("similarity", 0.5))

        # Keyword boost
        text_lower = text.lower()
        keyword_hits = sum(1 for term in query_terms if term in text_lower)
        adjusted_score = score + (keyword_hits * 0.05)

        meta = doc_meta_map.get(d_id, {"name": "Document", "source_type": "pdf"})
        stype_str = meta.get("source_type", "pdf")

        # Map to appropriate SourceType
        try:
            stype = SourceType(stype_str)
        except ValueError:
            stype = SourceType.PDF

        slide_no = page if stype == SourceType.PPT else None
        page_no = page if stype in [SourceType.PDF, SourceType.HANDWRITTEN_NOTE] else None
        
        # Timestamp extraction for YouTube
        ts_start = None
        ts_end = None
        if stype == SourceType.YOUTUBE:
            # check if time range in text e.g. 04:10-05:12
            ts_match = re.search(r'(\d+):(\d+)–(\d+):(\d+)', text)
            if ts_match:
                ts_start = int(ts_match.group(1)) * 60 + int(ts_match.group(2))
                ts_end = int(ts_match.group(3)) * 60 + int(ts_match.group(4))
            else:
                ts_start = (page - 1) * 60 if page else 0
                ts_end = ts_start + 60

        evidence_items.append(EvidenceItem(
            source_type=stype,
            source_id=d_id,
            source_name=meta.get("name", "Document"),
            text=text,
            page=page_no,
            slide=slide_no,
            timestamp_start=ts_start,
            timestamp_end=ts_end,
            relevance_score=adjusted_score,
        ))

    # Sort by adjusted relevance score and truncate to top_k
    evidence_items.sort(key=lambda e: e.relevance_score, reverse=True)
    return evidence_items[:top_k]


# Backward compatibility wrapper
async def hybrid_search_document(
    document_id: str,
    user_id: str,
    query: str,
    top_k: int = 8,
    page_filter: Optional[int] = None,
) -> List[EvidenceItem]:
    return await hybrid_search_evidence(
        user_id=user_id,
        query=query,
        document_id=document_id,
        top_k=top_k,
        page_filter=page_filter,
    )
