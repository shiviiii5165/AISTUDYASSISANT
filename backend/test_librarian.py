"""
Librarian Agent — Test Suite
===============================
10 test cases covering:
  - Sufficient internal notes → source: "internal", sufficient: True
  - Zero internal chunks → triggers web fallback
  - Internal chunks below relevance threshold → triggers web fallback
  - Web fallback also returns nothing → sufficient: False, no crash
  - Empty/whitespace topic → immediate return, retrieval NOT called
  - Vector store raises exception → caught, sufficient: False, no crash
  - related_context populated with cross-topic chunks
  - user_id scoping verified (correct user_id passed to retrieval)
  - hybrid_search_evidence fallback safety: empty doc_ids → no chunks returned
  - Web results correctly tagged source: "web"

All tests mock the underlying services so they run offline.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.librarian import (
    retrieve_context,
    LibrarianOutput,
    ChunkResult,
    MIN_RELEVANCE_THRESHOLD,
    _get_user_document_ids,
)
from app.services.knowledge.sources import EvidenceItem, SourceType


def run(coro):
    """Run an async coroutine synchronously for pytest."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_evidence(text: str, score: float, source_name: str = "TestDoc.pdf", page: int = 1) -> EvidenceItem:
    """Helper to create a mock EvidenceItem."""
    return EvidenceItem(
        source_type=SourceType.PDF,
        source_id="doc-abc-123",
        source_name=source_name,
        text=text,
        page=page,
        relevance_score=score,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: Sufficient internal notes → source: "internal", sufficient: True
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_sufficient_internal_notes(mock_get_docs, mock_search):
    """When internal notes return high-relevance chunks, sufficient=True and no web fallback."""
    mock_get_docs.return_value = ["doc-1", "doc-2"]
    mock_search.return_value = [
        _make_evidence("TCP uses a three-way handshake for connection setup.", 0.92),
        _make_evidence("The SYN, SYN-ACK, ACK sequence establishes a reliable connection.", 0.88),
    ]

    result = run(retrieve_context("TCP three-way handshake", "user-123"))

    assert isinstance(result, LibrarianOutput)
    assert result.sufficient is True
    assert result.used_web_fallback is False
    assert len(result.context) >= 1
    assert all(c.source == "internal" for c in result.context)
    assert all(c.relevance_score >= MIN_RELEVANCE_THRESHOLD for c in result.context)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: Zero internal chunks → triggers web fallback
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_zero_chunks_triggers_web_fallback(mock_get_docs, mock_search, mock_web):
    """When no internal chunks are found, the web fallback should be triggered."""
    mock_get_docs.return_value = ["doc-1"]
    mock_search.return_value = []  # No internal results
    mock_web.return_value = [
        {"title": "TCP Handshake Explained", "snippet": "The three-way handshake...", "url": "https://example.com/tcp"},
    ]

    result = run(retrieve_context("TCP three-way handshake", "user-123"))

    assert result.sufficient is False
    assert result.used_web_fallback is True
    assert len(result.context) >= 1
    assert any(c.source == "web" for c in result.context)
    mock_web.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: Internal chunks below relevance threshold → triggers web fallback
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_low_relevance_triggers_web_fallback(mock_get_docs, mock_search, mock_web):
    """When all internal chunks have relevance below the threshold, web fallback is triggered."""
    mock_get_docs.return_value = ["doc-1"]
    mock_search.return_value = [
        _make_evidence("Some unrelated chemistry content about atoms.", 0.30),
        _make_evidence("Water molecule H2O bonding.", 0.25),
    ]
    mock_web.return_value = [
        {"title": "Recursion in Python", "snippet": "Recursion is when a function calls itself...", "url": "https://example.com/recursion"},
    ]

    result = run(retrieve_context("recursion in Python", "user-123"))

    assert result.sufficient is False
    assert result.used_web_fallback is True
    mock_web.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: Web fallback also returns nothing → sufficient: False, no crash
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_web_fallback_empty_no_crash(mock_get_docs, mock_search, mock_web):
    """When both internal and web search return nothing, the result is valid with empty context."""
    mock_get_docs.return_value = ["doc-1"]
    mock_search.return_value = []
    mock_web.return_value = []  # Web search also yields nothing

    result = run(retrieve_context("obscure topic nobody writes about", "user-123"))

    assert isinstance(result, LibrarianOutput)
    assert result.sufficient is False
    assert result.used_web_fallback is False  # Web was called but returned nothing, so flag stays False
    assert len(result.context) == 0


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: Empty/whitespace topic → returns immediately, retrieval NOT called
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_empty_topic_returns_immediately(mock_get_docs, mock_search):
    """An empty or whitespace-only topic should return immediately without calling retrieval."""
    result = run(retrieve_context("   ", "user-123"))

    assert result.sufficient is False
    assert len(result.context) == 0
    mock_get_docs.assert_not_called()
    mock_search.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: Vector store raises exception → caught, sufficient: False, no crash
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_vector_store_exception_caught(mock_get_docs, mock_search):
    """If hybrid_search_evidence raises an exception, the Librarian catches it
    and returns a valid LibrarianOutput with sufficient=False, not a crash."""
    mock_get_docs.return_value = ["doc-1"]
    mock_search.side_effect = Exception("pgvector connection refused: FATAL: too many connections")

    result = run(retrieve_context("database normalization", "user-123"))

    assert isinstance(result, LibrarianOutput)
    assert result.sufficient is False
    assert len(result.context) == 0


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: related_context populated with cross-topic chunks
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_related_context_populated(mock_get_docs, mock_search):
    """When a broader secondary retrieval finds conceptually related chunks
    from a different topic, they should appear in related_context."""
    mock_get_docs.return_value = ["doc-1", "doc-2"]

    # Primary call returns mitosis chunks (sufficient)
    primary_results = [
        _make_evidence("Mitosis is the process of cell division.", 0.90, "Biology.pdf"),
    ]
    # Secondary (broader) call returns a related but different chunk
    broader_results = [
        _make_evidence("Cell membrane structure and permeability.", 0.70, "Chemistry.pdf"),
    ]

    # First call = primary retrieval, second call = broader retrieval
    mock_search.side_effect = [primary_results, broader_results]

    result = run(retrieve_context("mitosis cell division", "user-123"))

    assert result.sufficient is True
    assert len(result.related_context) >= 1
    assert result.related_context[0].source_document == "Chemistry.pdf"
    assert result.related_context[0].source == "internal"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: user_id scoping — retrieval called with correct user_id
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_user_id_scoping(mock_get_docs, mock_search):
    """The retrieval call MUST be made with the correct user_id parameter,
    ensuring a student can never see another student's notes."""
    target_user_id = "user-specific-abc-789"
    mock_get_docs.return_value = ["doc-owned-by-abc"]
    mock_search.return_value = [
        _make_evidence("User's private notes on algorithms.", 0.85),
    ]

    result = run(retrieve_context("sorting algorithms", target_user_id))

    # Verify _get_user_document_ids was called with the exact user_id
    mock_get_docs.assert_called_once_with(target_user_id)

    # Verify hybrid_search_evidence was called with the exact user_id
    call_kwargs = mock_search.call_args
    assert call_kwargs.kwargs.get("user_id") == target_user_id
    assert call_kwargs.kwargs.get("document_ids") == ["doc-owned-by-abc"]


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: hybrid_search_evidence fallback safety — empty doc_ids returns []
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_empty_doc_ids_skips_retrieval(mock_get_docs, mock_search, mock_web):
    """If a user has no documents (empty doc_ids), hybrid_search_evidence should
    NOT be called at all — preventing any possibility of the fallback table query
    running without document_id filters. This is the safety gate."""
    mock_get_docs.return_value = []  # User has no uploaded documents
    mock_web.return_value = []  # Mock web search to prevent real calls

    result = run(retrieve_context("quantum physics", "user-no-docs"))

    # hybrid_search_evidence should NEVER be called when doc_ids is empty
    mock_search.assert_not_called()
    assert result.sufficient is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: Web results correctly tagged source: "web" with URLs
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
@patch("app.agents.librarian.hybrid_search_evidence", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
def test_web_results_tagged_correctly(mock_get_docs, mock_search, mock_web):
    """Web fallback results must be tagged source='web' and include URL in page_or_location."""
    mock_get_docs.return_value = ["doc-1"]
    mock_search.return_value = []
    mock_web.return_value = [
        {"title": "Learn Recursion", "snippet": "A function that calls itself.", "url": "https://example.com/recursion"},
        {"title": "Recursive Algorithms", "snippet": "Common patterns in recursion.", "url": "https://example.com/algorithms"},
    ]

    result = run(retrieve_context("recursion", "user-123"))

    web_chunks = [c for c in result.context if c.source == "web"]
    assert len(web_chunks) == 2
    for chunk in web_chunks:
        assert chunk.source == "web"
        assert chunk.page_or_location.startswith("https://")
        assert chunk.source_document != ""
        assert chunk.text != ""


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: hybrid_search_evidence fallback with mismatched user_id → returns nothing
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.services.knowledge.hybrid_search.router.generate_embeddings", new_callable=AsyncMock)
@patch("app.services.knowledge.hybrid_search.supabase")
def test_fallback_query_filters_by_user_id(mock_supabase, mock_embeddings):
    """
    Directly tests hybrid_search_evidence's fallback table query path.
    Scenario: The RPC vector search returns nothing (forcing the fallback path),
    and we verify that the fallback query includes .eq("user_id", user_id).

    This proves the hardening fix works: even if a document_id belonging to
    another user is somehow passed, the fallback query now filters by user_id,
    preventing cross-user data leakage.
    """
    from app.services.knowledge.hybrid_search import hybrid_search_evidence

    # Mock embeddings to return a valid embedding (so vector search is attempted)
    mock_embeddings.return_value = [[0.1] * 768]

    # Mock the RPC call to return empty (forces the fallback path)
    mock_rpc_response = MagicMock()
    mock_rpc_response.data = []
    mock_rpc_execute = MagicMock(return_value=mock_rpc_response)
    mock_rpc_result = MagicMock()
    mock_rpc_result.execute = mock_rpc_execute
    mock_supabase.rpc.return_value = mock_rpc_result

    # Mock the pdfs metadata query
    mock_meta_response = MagicMock()
    mock_meta_response.data = [{"id": "doc-other-user", "name": "OtherDoc.pdf", "source_type": "pdf"}]
    mock_meta_execute = MagicMock(return_value=mock_meta_response)
    mock_meta_result = MagicMock()
    mock_meta_result.execute = mock_meta_execute
    mock_meta_in = MagicMock(return_value=mock_meta_result)
    mock_meta_select = MagicMock()
    mock_meta_select.in_ = mock_meta_in

    # Mock the fallback table query chain
    mock_fallback_response = MagicMock()
    mock_fallback_response.data = []  # Simulates: no chunks match this user_id
    mock_fallback_execute = MagicMock(return_value=mock_fallback_response)
    mock_fallback_limit = MagicMock()
    mock_fallback_limit.execute = mock_fallback_execute
    mock_fallback_eq_user = MagicMock()
    mock_fallback_eq_user.limit = MagicMock(return_value=mock_fallback_limit)
    mock_fallback_eq_pdf = MagicMock()
    mock_fallback_eq_pdf.eq = MagicMock(return_value=mock_fallback_eq_user)
    mock_fallback_select = MagicMock()
    mock_fallback_select.eq = MagicMock(return_value=mock_fallback_eq_pdf)

    # Wire up supabase.table() to return the right mock depending on table name
    def table_router(table_name):
        if table_name == "pdfs":
            return MagicMock(select=MagicMock(return_value=mock_meta_select))
        elif table_name == "document_chunks":
            return MagicMock(select=MagicMock(return_value=mock_fallback_select))
        return MagicMock()

    mock_supabase.table = table_router

    # Call with user_id="victim-user" but document_id belonging to another user
    result = run(hybrid_search_evidence(
        user_id="victim-user",
        query="some topic",
        document_ids=["doc-other-user"],
        top_k=5,
    ))

    # The fallback query should have been called with .eq("user_id", "victim-user")
    # Since we mocked the response as empty, we should get no results
    assert len(result) == 0

    # Verify the fallback select chain was called (meaning the fallback path executed)
    mock_fallback_select.eq.assert_called_once_with("pdf_id", "doc-other-user")
    # Verify the SECOND .eq call was for user_id
    mock_fallback_eq_pdf.eq.assert_called_once_with("user_id", "victim-user")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
