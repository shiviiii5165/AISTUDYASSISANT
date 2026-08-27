"""
Knowledge & Multi-Source Evidence Package
=========================================
"""
from .sources import SourceType, EvidenceItem, SourceRef, KnowledgeChunk
from .hybrid_search import hybrid_search_evidence, hybrid_search_document
from .retriever import get_topic_overview_context, get_slide_context
from .ppt_processor import process_pptx_and_store, extract_content_from_pptx
from .youtube_processor import process_youtube_video_and_store, extract_youtube_video_id

__all__ = [
    "SourceType",
    "EvidenceItem",
    "SourceRef",
    "KnowledgeChunk",
    "hybrid_search_evidence",
    "hybrid_search_document",
    "get_topic_overview_context",
    "get_slide_context",
    "process_pptx_and_store",
    "extract_content_from_pptx",
    "process_youtube_video_and_store",
    "extract_youtube_video_id",
]
