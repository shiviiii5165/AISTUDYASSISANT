"""
Handwritten notes image upload endpoint.
Uses Gemini REST API (gemini-flash-latest) for OCR.
Uses Gemini embeddings via vector_service for chunk storage.
"""

import uuid
import base64
import httpx
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro
from app.db.supabase_client import supabase
from app.services.vector_service import store_chunks_from_text

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg": ("jpg", "image/jpeg"),
    "image/png": ("png", "image/png"),
    "image/webp": ("webp", "image/webp"),
}

OCR_SYSTEM_PROMPT = """You are reading a student's handwritten notes. Extract ALL text you can see, preserving the structure as much as possible. Include headings, bullet points, formulas, diagrams described in text, and any labels. Format the output as clean readable text. If you see a diagram, describe it in text form. Do not skip anything even if handwriting is unclear — make your best guess and include it."""

@router.post("/image")
async def upload_handwritten_note(
    file: UploadFile = File(...),
    subject: str = Form("General"),
    current_user=Depends(require_pro),
):
    """Upload a handwritten note image, OCR via Gemini REST API, store as chunks."""

    # 1. Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WEBP.",
        )

    note_id = str(uuid.uuid4())
    file_bytes = await file.read()
    ext, media_type = ALLOWED_TYPES[file.content_type]

    try:
        # 2. Upload original image to Supabase Storage
        storage_path = f"{current_user.id}/{note_id}.{ext}"
        supabase.storage.from_("handwritten-notes").upload(storage_path, file_bytes)
        print(f"Uploaded image to handwritten-notes/{storage_path}")

        # 3. Call Gemini REST API for OCR
        b64_img = base64.b64encode(file_bytes).decode("utf-8")
        
        api_key = settings.GEMINI_API_KEY
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": media_type,
                                "data": b64_img
                            }
                        },
                        {
                            "text": OCR_SYSTEM_PROMPT
                        }
                    ]
                }
            ]
        }
        
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                print(f"Gemini API Error: {resp.text}")
                raise Exception(f"OCR failed with status {resp.status_code}")
                
            response_data = resp.json()
            if "candidates" not in response_data or not response_data["candidates"]:
                raise Exception("No content returned from Gemini Vision.")
            
            extracted_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

        print(f"Gemini extracted {len(extracted_text)} characters from handwritten note.")

        if not extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract any text from the image. Please try a clearer photo.",
            )

        # 4. Save record to pdfs table with source_type = 'handwritten'
        # MUST DO THIS FIRST because document_chunks has a foreign key to pdfs.id
        supabase.table("pdfs").insert({
            "id": note_id,
            "user_id": current_user.id,
            "name": file.filename or f"Handwritten Note ({subject})",
            "subject": subject,
            "status": "processing",
            "page_count": 1,
            "source_type": "handwritten",
        }).execute()

        # 5. Store chunks with embeddings (page_number=0 for handwritten notes)
        total_chunks = store_chunks_from_text(note_id, extracted_text, page_number=0)

        # 6. Update status to ready
        supabase.table("pdfs").update({
            "status": "ready"
        }).eq("id", note_id).execute()

        return {
            "noteId": note_id,
            "extractedText": extracted_text[:500],
            "totalChunks": total_chunks,
            "subject": subject,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"FULL ERROR: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process handwritten note: {str(e)}",
        )
