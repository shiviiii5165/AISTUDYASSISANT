"""
Vector service utility for handwritten notes and exam predictor.
Uses existing Gemini embedding_service.py and Supabase pgvector.
Adapted to existing document_chunks schema: pdf_id, chunk_text, page_number, embedding, chunk_index.
"""

from app.services.embedding_service import get_embeddings
from app.db.supabase_client import supabase


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def store_chunks_from_text(pdf_id: str, text: str, page_number: int = 0) -> int:
    """
    Chunk text, generate Gemini embeddings, and insert into document_chunks.
    Uses page_number=0 as default for handwritten notes (no real pages).
    Returns the number of chunks stored.
    """
    chunks = chunk_text(text)
    if not chunks:
        return 0

    # Generate embeddings in batches of 100 (matching existing PDF pipeline)
    batch_size = 100
    total_stored = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = get_embeddings(batch)

        records = []
        for idx, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            records.append({
                "pdf_id": pdf_id,
                "chunk_text": chunk,
                "page_number": page_number,
                "embedding": embedding,
                "chunk_index": i + idx,
            })

        try:
            supabase.table("document_chunks").insert(records).execute()
            total_stored += len(records)
            print(f"Stored batch of {len(records)} chunks for document {pdf_id}.")
        except Exception as e:
            print(f"Error storing chunks: {e}")
            raise e

    print(f"Successfully stored {total_stored} total chunks for document {pdf_id}.")
    return total_stored


def query_chunks_for_rag(pdf_id: str, user_id: str, query: str, top_k: int = 5) -> list[dict]:
    """
    Generate query embedding and search for relevant chunks via existing RPC.
    Returns list of dicts with text, page, score keys.
    """
    query_embedding = get_embeddings([query])[0]

    try:
        response = supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter_pdf_id": pdf_id,
                "filter_user_id": user_id,
            }
        ).execute()

        results = response.data
        print(f"Similarity search returned {len(results)} chunks.")

        return [
            {
                "text": row["chunk_text"],
                "page": row["page_number"],
                "score": row["similarity"],
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error during similarity search: {e}")
        raise e


def get_all_chunks_text(pdf_id: str, limit: int = 30) -> list[str]:
    """
    Fetch all chunk texts for a document, ordered by chunk_index.
    Used by the exam predictor to get full context.
    """
    try:
        response = supabase.rpc("get_top_chunks", {
            "match_pdf_id": pdf_id,
            "match_count": limit,
        }).execute()

        results = response.data
        print(f"Fetched {len(results)} chunks for document {pdf_id}.")
        return [row["chunk_text"] for row in results]
    except Exception as e:
        print(f"Error fetching all chunks: {e}")
        raise e
