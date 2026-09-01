"""
PowerPoint (.pptx / .ppt) Ingestion & Chunking Service
======================================================
Parses presentation files using python-pptx, extracting slide numbers, titles,
bullet points, tables, and speaker notes with preserved provenance.
"""
from app.core.logging import logger
import io
import os
import uuid
from typing import List, Dict, Any, Optional
from pptx import Presentation
from app.services.embedding_service import get_embeddings
from app.services.vector_store import store_chunks
from app.db.supabase_client import supabase


def extract_content_from_pptx(file_source: Any) -> List[Dict[str, Any]]:
    """
    Extracts structured content per slide from a PPTX file path or bytes.
    Returns list of dicts: {"slide_number": int, "title": str, "text": str, "notes": str}
    """
    if isinstance(file_source, bytes):
        prs = Presentation(io.BytesIO(file_source))
    elif isinstance(file_source, str) and os.path.exists(file_source):
        prs = Presentation(file_source)
    elif hasattr(file_source, "read"):
        prs = Presentation(file_source)
    else:
        raise ValueError("Invalid file_source provided for PPTX extraction.")

    slides_data = []

    for idx, slide in enumerate(prs.slides):
        slide_no = idx + 1
        slide_title = ""
        body_parts = []

        # 1. Inspect Shapes
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                
                # Check if it's the title shape
                if shape == slide.shapes.title or (not slide_title and len(text) < 100 and "\n" not in text):
                    slide_title = text
                else:
                    body_parts.append(text)

            elif shape.has_table:
                table = shape.table
                table_rows = []
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        table_rows.append(" | ".join(row_cells))
                if table_rows:
                    body_parts.append("Table Data:\n" + "\n".join(table_rows))

        # 2. Inspect Speaker Notes
        notes_text = ""
        try:
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()
        except Exception:
            pass

        full_slide_text = f"Title: {slide_title}\n" if slide_title else ""
        if body_parts:
            full_slide_text += "\n".join(body_parts)
        if notes_text:
            full_slide_text += f"\n[Presenter Notes]: {notes_text}"

        slides_data.append({
            "slide_number": slide_no,
            "title": slide_title,
            "text": full_slide_text.strip(),
            "notes": notes_text,
        })

    return slides_data


def chunk_pptx_slides(slides_data: List[Dict[str, Any]], chunk_size: int = 500) -> List[Dict[str, Any]]:
    """
    Chunks slide content while strictly retaining slide_number provenance.
    """
    chunks = []
    chunk_index = 0

    for s in slides_data:
        slide_no = s["slide_number"]
        text = s["text"]
        if not text:
            continue

        words = text.split()
        if len(words) <= chunk_size:
            chunks.append({
                "text": text,
                "page": slide_no,  # map slide to page for unified document_chunks table
                "chunk_index": chunk_index,
                "metadata": {"title": s["title"], "source_type": "ppt", "slide_number": slide_no}
            })
            chunk_index += 1
        else:
            # Sub-chunk longer slides
            step = chunk_size - 50
            for i in range(0, len(words), step):
                sub_text = " ".join(words[i:i + chunk_size])
                chunks.append({
                    "text": sub_text,
                    "page": slide_no,
                    "chunk_index": chunk_index,
                    "metadata": {"title": s["title"], "source_type": "ppt", "slide_number": slide_no}
                })
                chunk_index += 1

    return chunks


def process_pptx_and_store(
    document_id: str,
    file_bytes: bytes,
    user_id: str,
    filename: str,
    subject: str = "General",
) -> Dict[str, Any]:
    """
    Processes PPTX, creates pdfs record (with source_type='ppt'), stores chunks and embeddings.
    """
    slides = extract_content_from_pptx(file_bytes)
    chunks = chunk_pptx_slides(slides)

    # 1. Upsert document record in pdfs table
    if supabase:
        try:
            supabase.table("pdfs").upsert({
                "id": document_id,
                "user_id": user_id,
                "name": filename,
                "subject": subject,
                "status": "ready",
                "page_count": len(slides),
                "source_type": "ppt",
            }).execute()
        except Exception as e:
            logger.info(f"[PPTProcessor] DB insert notice: {e}")

    # 2. Generate embeddings and store chunks
    if chunks:
        texts = [c["text"] for c in chunks]
        embeddings = get_embeddings(texts)
        if supabase:
            store_chunks(document_id, chunks, embeddings)

    return {
        "document_id": document_id,
        "total_slides": len(slides),
        "total_chunks": len(chunks),
        "slides": slides,
    }
