from app.db.supabase_client import supabase

def store_chunks(pdf_id: str, chunks: list[dict], embeddings: list[list[float]]):
    """Store chunks and their embeddings in Supabase pgvector"""
    print(f"Preparing to insert {len(chunks)} chunks into pgvector for PDF {pdf_id}...")
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
            print(f"Inserted batch of {len(batch)} chunks.")
        except Exception as e:
            print(f"Error inserting chunks into pgvector: {e}")
            raise e
    print(f"Successfully inserted all {len(records)} chunks.")

def search_relevant_chunks(pdf_id: str, user_id: str, query_embedding: list[float], top_k=5) -> list[dict]:
    """Search for relevant chunks using Supabase RPC for cosine similarity"""
    try:
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
        print(f"Similarity search returned {len(results)} chunks.")
        
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
        print(f"Error during similarity search in pgvector: {e}")
        raise e

def get_all_chunks(pdf_id: str, user_id: str) -> list[dict]:
    """Fetch all chunks for a specific PDF, bypassing similarity search."""
    try:
        # Note: We must also check user_id to ensure RLS/security if using service role,
        # but since we rely on RLS, querying the table directly works.
        # We explicitly filter by both to be extremely safe.
        response = supabase.table("document_chunks") \
            .select("chunk_text, page_number") \
            .eq("pdf_id", pdf_id) \
            .order("page_number") \
            .execute()
            
        results = response.data
        print(f"Fetched {len(results)} total chunks for PDF {pdf_id}.")
        
        return [
            {
                "text": row["chunk_text"],
                "page": row["page_number"]
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error fetching all chunks: {e}")
        raise e


