from app.db.supabase_client import supabase
from app.core.logging import logger

def store_chunks(pdf_id: str, chunks: list[dict], embeddings: list[list[float]]):
    """Store chunks and their embeddings in Supabase pgvector"""
    logger.info(f"Preparing to insert {len(chunks)} chunks into pgvector for PDF {pdf_id}...")
    # Prepare records for insertion
    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append({
            "pdf_id": pdf_id,
            "page_number": chunk["page"],
            "chunk_text": chunk["text"],
            "embedding": embedding
        })
    
    # Insert in batches of 100 to avoid request limits
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            supabase.table("document_chunks").insert(batch).execute()
            logger.info(f"Inserted batch of {len(batch)} chunks.")
        except Exception as e:
            logger.error(f"Error inserting chunks into pgvector: {e}")
            raise e
    logger.info(f"Successfully inserted all {len(records)} chunks.")

def _verify_ownership(pdf_id: str, user_id: str):
    """Explicitly verify ownership to prevent swallowing unauthorized access as empty results."""
    owner_check = supabase.table("pdfs") \
        .select("id") \
        .eq("id", pdf_id) \
        .eq("user_id", user_id) \
        .execute()
    if not owner_check.data:
        logger.warning(f"Ownership check failed: PDF {pdf_id} not owned by user {user_id}.")
        raise PermissionError(f"PDF {pdf_id} not found or access denied.")

def search_relevant_chunks(pdf_id: str, user_id: str, query_embedding: list[float], top_k=5) -> list[dict]:
    """Search for relevant chunks using Supabase RPC for cosine similarity"""
    try:
        _verify_ownership(pdf_id, user_id)
        
        response = supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter_pdf_id": pdf_id,
                "filter_user_id": user_id
            }
        ).execute()
        
        results = response.data
        logger.info(f"Similarity search returned {len(results)} chunks.")
        
        # Map the RPC response to the existing dictionary format expected by the RAG service
        return [
            {
                "text": row["chunk_text"],
                "page": row["page_number"],
                "score": row["similarity"]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error during similarity search in pgvector: {e}")
        raise e

def get_all_chunks(pdf_id: str, user_id: str) -> list[dict]:
    """Fetch all chunks for a specific PDF, bypassing similarity search."""
    try:
        _verify_ownership(pdf_id, user_id)

        response = supabase.table("document_chunks") \
            .select("chunk_text, page_number") \
            .eq("pdf_id", pdf_id) \
            .order("page_number") \
            .execute()
            
        results = response.data
        logger.info(f"Fetched {len(results)} total chunks for PDF {pdf_id}.")
        
        return [
            {
                "text": row["chunk_text"],
                "page": row["page_number"]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error fetching all chunks: {e}")
        raise e


