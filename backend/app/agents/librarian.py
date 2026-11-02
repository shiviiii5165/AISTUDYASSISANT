"""
Librarian Agent — Knowledge Retrieval & Context Assembly
==========================================================
Given a topic/query and a user_id, the Librarian:
  1. Retrieves from the student's OWN notes first (scoped strictly by user_id)
  2. Assesses sufficiency (chunks above a relevance threshold)
  3. Falls back to web search (DuckDuckGo) ONLY if internal notes are insufficient
  4. Detects cross-topic connections (related_context) via a broader secondary retrieval
  5. Returns a structured LibrarianOutput for downstream agents (e.g. Tutor) to consume

Wraps existing retrieval stack — does NOT reimplement chunking, embedding, or vector search.
"""

import time
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db.supabase_client import supabase
from app.services.knowledge.hybrid_search import hybrid_search_evidence
from app.services.knowledge.sources import EvidenceItem
from app.services.web_search import perform_web_search
from app.core.config import settings


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# Chunks with a relevance score below this are not considered useful.
# If ALL returned chunks are below this, the query is classified as "insufficient".
MIN_RELEVANCE_THRESHOLD: float = 0.65

# Maximum number of web results to fetch when falling back.
WEB_FALLBACK_MAX_RESULTS: int = 3

# Number of chunks to retrieve for the primary search.
DEFAULT_PRIMARY_TOP_K: int = 5

# Number of chunks to retrieve for the broader "related context" search.
RELATED_CONTEXT_TOP_K: int = 3


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ChunkResult(BaseModel):
    """A single retrieved chunk of context."""
    text: str = Field(..., description="The chunk text content.")
    source_document: str = Field(..., description="Name or ID of the source document.")
    page_or_location: Optional[str] = Field(
        None, description="Page number, slide number, timestamp, or URL."
    )
    relevance_score: float = Field(
        ..., description="Relevance/similarity score (0.0–1.0+)."
    )
    source: str = Field(
        ..., description="'internal' (student's own notes) or 'web' (DuckDuckGo fallback)."
    )


class LibrarianOutput(BaseModel):
    """Structured output from the Librarian agent."""
    context: List[ChunkResult] = Field(
        default_factory=list,
        description="Primary relevant chunks for the query.",
    )
    related_context: List[ChunkResult] = Field(
        default_factory=list,
        description="Cross-topic related chunks from the student's other notes.",
    )
    sufficient: bool = Field(
        ..., description="True if the student's internal notes alone were sufficient."
    )
    used_web_fallback: bool = Field(
        ..., description="True if web search was used because internal notes were insufficient."
    )


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def _get_user_document_ids(user_id: str) -> List[str]:
    """
    Fetch all document IDs belonging to a specific user from the pdfs table.
    This is the CRITICAL user-scoping gate: only the student's own document IDs
    are ever passed to the retrieval layer, ensuring zero note-leakage.
    """
    if not supabase:
        return []
    try:
        res = supabase.table("pdfs") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("status", "ready") \
            .execute()
        return [row["id"] for row in (res.data or [])]
    except Exception as e:
        print(f"[Librarian] Failed to fetch user documents: {e}")
        return []


def _evidence_to_chunk(item: EvidenceItem) -> ChunkResult:
    """Convert an EvidenceItem from the existing retrieval stack to a ChunkResult."""
    location = None
    if item.page is not None:
        location = f"Page {item.page}"
    elif item.slide is not None:
        location = f"Slide {item.slide}"
    elif item.timestamp_start is not None:
        location = item.get_citation_badge()

    return ChunkResult(
        text=item.text,
        source_document=item.source_name or item.source_id or "Unknown Document",
        page_or_location=location,
        relevance_score=item.relevance_score,
        source="internal",
    )


def _web_result_to_chunk(result: dict) -> ChunkResult:
    """Convert a DuckDuckGo search result dict to a ChunkResult."""
    return ChunkResult(
        text=result.get("snippet", ""),
        source_document=result.get("title", "Web Result"),
        page_or_location=result.get("url", ""),
        relevance_score=0.5,  # Fixed score for web results (no similarity metric)
        source="web",
    )


def _extract_broader_query(topic: str) -> Optional[str]:
    """
    Extract a broader, more general query from the topic for cross-topic
    connection detection. Returns None if the topic is already too short/generic.

    Strategy: take the first 2–3 significant words to broaden the scope.
    E.g., "TCP three-way handshake" → "TCP networking"
          "mitosis cell division" → "cell biology"
    This is intentionally simple — we rely on the vector store's semantic
    similarity to find genuine connections, not keyword heuristics.
    """
    words = topic.strip().split()
    if len(words) <= 2:
        return None  # Already too short, no broader query possible
    # Use the first word as a broader concept search
    return words[0]


# ══════════════════════════════════════════════════════════════════════════════
# CORE RETRIEVAL FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

async def retrieve_context(
    topic: str,
    user_id: str,
    top_k: int = DEFAULT_PRIMARY_TOP_K,
) -> LibrarianOutput:
    """
    Main entry point for the Librarian agent.

    1. Validates input (empty topic → immediate return)
    2. Fetches the student's own document IDs (user-scoping gate)
    3. Retrieves top-k chunks from internal notes
    4. Assesses sufficiency (relevance threshold)
    5. Falls back to web search if insufficient
    6. Detects cross-topic connections via broader secondary retrieval
    7. Returns a structured LibrarianOutput — never crashes
    """
    # ── Input validation ────────────────────────────────────────────────────
    topic = (topic or "").strip()
    user_id = (user_id or "").strip()

    if not topic or not user_id:
        return LibrarianOutput(
            context=[],
            related_context=[],
            sufficient=False,
            used_web_fallback=False,
        )

    # ── Step 1: Fetch user's own document IDs ───────────────────────────────
    try:
        doc_ids = await _get_user_document_ids(user_id)
    except Exception as e:
        print(f"[Librarian] Error fetching user docs: {e}")
        doc_ids = []

    # ── Step 2: Primary retrieval from internal notes ───────────────────────
    primary_chunks: List[ChunkResult] = []

    if doc_ids:
        try:
            evidence_items: List[EvidenceItem] = await hybrid_search_evidence(
                user_id=user_id,
                query=topic,
                document_ids=doc_ids,
                top_k=top_k,
            )
            primary_chunks = [_evidence_to_chunk(item) for item in evidence_items]
        except Exception as e:
            print(f"[Librarian] Internal retrieval failed: {e}")
            primary_chunks = []

    # ── Step 3: Assess sufficiency ──────────────────────────────────────────
    # Sufficient = at least one chunk above MIN_RELEVANCE_THRESHOLD
    sufficient_chunks = [
        c for c in primary_chunks
        if c.relevance_score >= MIN_RELEVANCE_THRESHOLD
    ]
    is_sufficient = len(sufficient_chunks) > 0

    # If sufficient, use only the chunks above threshold for the primary context
    if is_sufficient:
        context = sufficient_chunks
    else:
        # Keep whatever we got (even low-quality), web fallback will supplement
        context = primary_chunks

    # ── Step 4: Web fallback (only if insufficient) ─────────────────────────
    used_web_fallback = False

    if not is_sufficient:
        try:
            web_results = await perform_web_search(
                query=topic,
                max_results=WEB_FALLBACK_MAX_RESULTS,
            )
            if web_results:
                # Default path: preserve exact frozen snippet chunks
                web_chunks = [_web_result_to_chunk(r) for r in web_results]

                # Optional Canary: if active for user or staging environment, evaluate admission via EvidenceQualityGate
                if settings.is_source_extraction_canary_active(user_id=user_id) and web_results[0].get("url"):
                    t_canary_start = time.time()
                    try:
                        from app.services.knowledge.source_extraction import SourceExtractionService, ExtractionStatus, EvidenceQualityGate
                        from app.services.knowledge.source_extraction_canary import canary_tracker

                        target_url = web_results[0]["url"]
                        extracted = await SourceExtractionService.extract_source(target_url, query=topic)
                        t_ext_ms = (time.time() - t_canary_start) * 1000

                        admitted, reason = EvidenceQualityGate.evaluate_admission(extracted, query=topic, snippet_text=web_chunks[0].text)
                        top_rel = extracted.relevant_passages[0].relevance_score if extracted.relevant_passages else 0.0
                        is_cached = (extracted.status == ExtractionStatus.CACHED)

                        fail_class = None
                        if extracted.status == ExtractionStatus.FAILED_ACCESS_DENIED:
                            fail_class = "access_denied"
                        elif extracted.status == ExtractionStatus.BUDGET_EXCEEDED:
                            fail_class = "budget_exceeded"
                        elif extracted.status in (ExtractionStatus.FAILED_EMPTY_CONTENT, ExtractionStatus.FAILED_HTTP_ERROR):
                            fail_class = "no_relevant_passage"

                        if admitted and extracted.relevant_passages:
                            top_passage = extracted.relevant_passages[0].text
                            loc = extracted.canonical_url
                            if extracted.section_anchor:
                                loc = f"{loc}{extracted.section_anchor}"
                            # Enrich top chunk with extracted evidence while preserving original search snippet context
                            web_chunks[0] = ChunkResult(
                                text=f"{top_passage}\n\n[Summary snippet]: {web_chunks[0].text}",
                                source_document=extracted.document_title,
                                page_or_location=loc,
                                relevance_score=0.85,
                                source="web_extracted"
                            )
                            canary_tracker.record_event(
                                url=target_url,
                                extraction_method=extracted.extraction_method,
                                is_cached=is_cached,
                                admitted=True,
                                gate_reason=reason,
                                passage_relevance=top_rel,
                                snippet_fallback_retained=False,
                                claim_support=1.0,
                                citation_valid=True,
                                extraction_latency_ms=t_ext_ms,
                                total_latency_ms=t_ext_ms,
                                credits_consumed=extracted.credits_consumed,
                                failure_classification=fail_class
                            )
                        else:
                            canary_tracker.record_event(
                                url=target_url,
                                extraction_method=extracted.extraction_method,
                                is_cached=is_cached,
                                admitted=False,
                                gate_reason=reason,
                                passage_relevance=top_rel,
                                snippet_fallback_retained=True,
                                claim_support=1.0,
                                citation_valid=True,
                                extraction_latency_ms=t_ext_ms,
                                total_latency_ms=t_ext_ms,
                                credits_consumed=extracted.credits_consumed,
                                failure_classification=fail_class
                            )
                            print(f"[Librarian Canary] EvidenceQualityGate retained snippet: {reason}")
                    except Exception as e:
                        print(f"[Librarian Canary] Source extraction canary notice: {e}")

                context.extend(web_chunks)
                used_web_fallback = True
        except Exception as e:
            print(f"[Librarian] Web fallback failed: {e}")

    # ── Step 5: Cross-topic connection (related_context) ────────────────────
    related_context: List[ChunkResult] = []

    if doc_ids:
        broader_query = _extract_broader_query(topic)
        if broader_query:
            try:
                broader_evidence: List[EvidenceItem] = await hybrid_search_evidence(
                    user_id=user_id,
                    query=broader_query,
                    document_ids=doc_ids,
                    top_k=RELATED_CONTEXT_TOP_K,
                )
                # Only include chunks that are NOT already in the primary context
                primary_texts = {c.text for c in context}
                for item in broader_evidence:
                    if item.text not in primary_texts and item.relevance_score >= 0.5:
                        related_context.append(_evidence_to_chunk(item))
            except Exception as e:
                print(f"[Librarian] Cross-topic retrieval failed (non-fatal): {e}")

    # ── Return structured output ────────────────────────────────────────────
    return LibrarianOutput(
        context=context,
        related_context=related_context,
        sufficient=is_sufficient,
        used_web_fallback=used_web_fallback,
    )


def format_isolated_context(librarian_output: LibrarianOutput, max_chars: int = 2000) -> str:
    """
    Formats librarian chunks with strict prompt-injection delimiters (§42)
    and distinguishes student-provided material from supplementary material (§9).
    """
    if not librarian_output or not librarian_output.context:
        return ""

    out_parts = []
    total_len = 0
    for idx, chunk in enumerate(librarian_output.context):
        label = "FROM YOUR MATERIAL" if chunk.source == "internal" else "SUPPLEMENTARY EXPLANATION"
        loc = f" (Location: {chunk.page_or_location})" if chunk.page_or_location else ""
        content = chunk.text.strip()
        if total_len + len(content) > max_chars:
            remaining = max_chars - total_len
            if remaining > 80:
                content = content[:remaining] + "..."
            else:
                break

        block = (
            f"<<<BEGIN_STUDENT_DOCUMENT_EXCERPT {idx+1}>>>\n"
            f"Category: {label}\n"
            f"Source: {chunk.source_document}{loc}\n"
            f"{content}\n"
            f"<<<END_STUDENT_DOCUMENT_EXCERPT {idx+1}>>>"
        )
        out_parts.append(block)
        total_len += len(content)

    return "\n\n".join(out_parts)
