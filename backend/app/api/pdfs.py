from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException, status
from app.services.pdf_processor import extract_text_from_pdf, chunk_text
from app.services.embedding_service import get_embeddings
from app.services.vector_store import store_chunks
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import check_pdf_upload_limit
import uuid, os

router = APIRouter()

@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject: str = "General",
    current_user=Depends(check_pdf_upload_limit)
):
    pdf_id = str(uuid.uuid4())
    import tempfile
    
    try:
        # Save file temporarily in the OS temp directory (works on Vercel)
        temp_dir = os.path.join(tempfile.gettempdir(), "teachgenie_temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{pdf_id}.pdf")
        file_bytes = await file.read()
        
        # Strict validation: Check for PDF magic bytes (%PDF-)
        if not file_bytes.startswith(b'%PDF-'):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid file format. Only true PDF files are allowed."
            )
            
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        
        # Upload to Supabase Storage using bytes
        storage_res = supabase.storage.from_("pdfs").upload(
            f"{current_user.id}/{pdf_id}.pdf", 
            file_bytes,
            {"content-type": "application/pdf"}
        )
        if hasattr(storage_res, 'error') and storage_res.error:
            raise Exception(f"Storage Error: {storage_res.error}")
        
        # Save metadata to DB
        db_res = supabase.table("pdfs").insert({
            "id": pdf_id,
            "user_id": current_user.id,
            "name": file.filename,
            "subject": subject,
            "status": "processing"
        }).execute()
        
        # Process in background (chunking + embeddings)
        background_tasks.add_task(process_pdf_background, pdf_id, temp_path)
        
        return {"pdf_id": pdf_id, "status": "processing"}

    except Exception as e:
        print(f"Upload failed: {str(e)}")
        # If it failed, clean up the temp file if it was created
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


def process_pdf_background(pdf_id: str, temp_path: str):
    try:
        pages = extract_text_from_pdf(temp_path)
        chunks = chunk_text(pages)
        
        # Calculate total pages
        page_count = len(pages) if pages else 0
        
        # Batch embeddings (max 100 at a time)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            embeddings = get_embeddings([c["text"] for c in batch])
            store_chunks(pdf_id, batch, embeddings)
        
        # Update status and page count
        supabase.table("pdfs").update({
            "status": "ready",
            "page_count": page_count
        }).eq("id", pdf_id).execute()
    except Exception as e:
        # Mark as error if processing fails, and save error in subject so we can see it
        error_str = str(e)
        supabase.table("pdfs").update({
            "status": "error",
            "subject": f"ERROR: {error_str}"[:200]  # truncate just in case
        }).eq("id", pdf_id).execute()
        print(f"Error processing PDF {pdf_id}: {error_str}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/list")
async def list_pdfs(current_user=Depends(get_current_user)):
    """List all PDFs for the current user"""
    result = supabase.table("pdfs") \
        .select("*") \
        .eq("user_id", current_user.id) \
        .order("created_at", desc=True) \
        .execute()
    
    return {"pdfs": result.data}


@router.get("/{pdf_id}/status")
async def get_pdf_status(pdf_id: str, current_user=Depends(get_current_user)):
    """Get processing status for a specific PDF"""
    result = supabase.table("pdfs") \
        .select("id, status, page_count") \
        .eq("id", pdf_id) \
        .eq("user_id", current_user.id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    return result.data


@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str, current_user=Depends(get_current_user)):
    """Delete a PDF and all associated data"""
    # Verify ownership
    result = supabase.table("pdfs") \
        .select("id, user_id") \
        .eq("id", pdf_id) \
        .eq("user_id", current_user.id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    # Delete from Supabase Storage
    try:
        supabase.storage.from_("pdfs").remove([f"{current_user.id}/{pdf_id}.pdf"])
    except Exception:
        pass  # Storage file may not exist
    
    # Delete from DB
    # Note: ON DELETE CASCADE will automatically delete document_chunks
    supabase.table("pdfs").delete().eq("id", pdf_id).execute()

    
    return {"message": "PDF deleted successfully"}
