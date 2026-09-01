"""
YouTube Video Transcript & Concept Segmentation Service
========================================================
Extracts transcripts from public YouTube URLs, segments them into timestamped
evidence chunks (e.g. 00:04:10–00:05:12), and stores them with embeddings.
"""
import re
import uuid
from typing import List, Dict, Any, Optional
from app.services.embedding_service import get_embeddings
from app.services.vector_store import store_chunks
from app.db.supabase_client import supabase


YOUTUBE_URL_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
)


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract 11-character video ID from any standard YouTube URL."""
    match = YOUTUBE_URL_REGEX.search(url.strip())
    return match.group(1) if match else None


def fetch_youtube_transcript(video_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves timed transcript items: [{"text": str, "start": float, "duration": float}].
    Falls back gracefully if transcript is disabled or package is not installed.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Try fetching English or auto-generated transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'en-US', 'hi', 'auto'])
        return transcript.fetch()
    except Exception as e:
        print(f"[YouTubeProcessor] Notice: Standard transcript fetch failed ({e}). Attempting direct get_transcript...")
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            return YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e2:
            print(f"[YouTubeProcessor] Transcript unavailable: {e2}")
            return []


def segment_transcript_chunks(transcript_items: List[Dict[str, Any]], target_duration_sec: int = 60) -> List[Dict[str, Any]]:
    """
    Groups granular transcript lines into meaningful 60-90 second semantic chunks with timestamp ranges.
    """
    if not transcript_items:
        return []

    chunks = []
    current_texts = []
    chunk_start = transcript_items[0].get("start", 0)
    current_end = chunk_start
    chunk_idx = 0

    for item in transcript_items:
        text = item.get("text", "").strip()
        start = item.get("start", 0)
        duration = item.get("duration", 0)
        end = start + duration

        if not text:
            continue

        if not current_texts:
            chunk_start = start

        current_texts.append(text)
        current_end = end

        # If accumulated duration exceeds target, finalize chunk
        if (current_end - chunk_start) >= target_duration_sec:
            full_text = " ".join(current_texts)
            chunks.append({
                "text": full_text,
                "page": int(chunk_start // 60) + 1,  # minute as page approximation
                "chunk_index": chunk_idx,
                "metadata": {
                    "source_type": "youtube",
                    "timestamp_start": int(chunk_start),
                    "timestamp_end": int(current_end),
                    "time_label": f"{int(chunk_start//60):02d}:{int(chunk_start%60):02d}–{int(current_end//60):02d}:{int(current_end%60):02d}"
                }
            })
            chunk_idx += 1
            current_texts = []

    if current_texts:
        full_text = " ".join(current_texts)
        chunks.append({
            "text": full_text,
            "page": int(chunk_start // 60) + 1,
            "chunk_index": chunk_idx,
            "metadata": {
                "source_type": "youtube",
                "timestamp_start": int(chunk_start),
                "timestamp_end": int(current_end),
                "time_label": f"{int(chunk_start//60):02d}:{int(chunk_start%60):02d}–{int(current_end//60):02d}:{int(current_end%60):02d}"
            }
        })

    return chunks


def process_youtube_video_and_store(
    url: str,
    user_id: str,
    title: Optional[str] = None,
    subject: str = "General",
) -> Dict[str, Any]:
    """
    Validates URL, fetches transcript, chunks with timestamps, and indexes into pgvector.
    """
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")

    doc_id = str(uuid.uuid4())
    doc_name = title or f"YouTube Video ({video_id})"

    transcript_items = fetch_youtube_transcript(video_id)
    if not transcript_items:
        # Create lightweight placeholder metadata so the user still has reference
        placeholder_text = f"YouTube Video Reference: {url} (ID: {video_id}). Use general concept reasoning grounded in topic context."
        chunks = [{
            "text": placeholder_text,
            "page": 1,
            "chunk_index": 0,
            "metadata": {
                "source_type": "youtube",
                "timestamp_start": 0,
                "timestamp_end": 60,
                "video_id": video_id,
            }
        }]
    else:
        chunks = segment_transcript_chunks(transcript_items)

    # 1. Upsert to pdfs table
    if supabase:
        try:
            supabase.table("pdfs").upsert({
                "id": doc_id,
                "user_id": user_id,
                "name": doc_name,
                "subject": subject,
                "status": "ready",
                "page_count": len(chunks),
                "source_type": "youtube",
            }).execute()
        except Exception as e:
            print(f"[YouTubeProcessor] DB insert notice: {e}")

    # 2. Embed and store chunks
    if chunks:
        texts = [c["text"] for c in chunks]
        embeddings = get_embeddings(texts)
        if supabase:
            store_chunks(doc_id, chunks, embeddings)

    return {
        "document_id": doc_id,
        "video_id": video_id,
        "total_chunks": len(chunks),
        "has_transcript": len(transcript_items) > 0,
    }
