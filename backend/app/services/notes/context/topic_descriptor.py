"""
LearnByGenie Notes Context Engine — Topic Descriptor
==================================================
Provides generic, scalable, data-driven topic identity.
Supports arbitrary educational topics without finite keyword restrictions or hard-coded Python routing.
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from .normalizer import ContextNormalizer


class TopicDescriptor(BaseModel):
    """
    Unified, topic-agnostic descriptor representing educational topic identity.
    Decouples topic representation from hard-coded catalog keys.
    """
    subject: str = "General"
    topic: str
    normalized_topic: str
    grade: Optional[int] = None
    class_level: Optional[str] = None
    board: Optional[str] = None
    course: Optional[str] = None
    curriculum: Optional[str] = None
    curriculum_version: Optional[str] = None
    source_scope: str = "general"  # "curated_catalog" | "user_upload" | "lesson_plan" | "general"
    topic_path: List[str] = Field(default_factory=list)
    parent_topic: Optional[str] = None
    requested_subtopic: Optional[str] = None
    catalog_key: Optional[str] = None
    is_catalog_curated: bool = False

    @classmethod
    def create(
        cls,
        topic: str,
        subject: Optional[str] = None,
        class_level: Optional[str] = None,
        grade: Optional[int] = None,
        board: Optional[str] = None,
        curriculum: Optional[str] = None,
        source_scope: str = "general",
        topic_path: Optional[List[str]] = None,
        catalog_key: Optional[str] = None,
        **kwargs: Any
    ) -> "TopicDescriptor":
        """
        Factory method to construct a TopicDescriptor for arbitrary topic strings.
        Normalizes typography and aliases without rejecting unknown topics.
        """
        raw_topic, norm_topic = ContextNormalizer.normalize_topic(topic or "General Topic")
        
        grade_num = grade
        class_disp = class_level
        if grade_num is None and class_level:
            grade_num, class_disp = ContextNormalizer.normalize_grade(class_level)
        elif grade_num is not None and not class_disp:
            class_disp = f"Class {grade_num}"

        norm_board = ContextNormalizer.normalize_curriculum(board or curriculum)

        return cls(
            subject=(subject or "General").strip() or "General",
            topic=raw_topic,
            normalized_topic=norm_topic or raw_topic,
            grade=grade_num,
            class_level=class_disp,
            board=norm_board,
            curriculum=norm_board,
            source_scope=source_scope,
            topic_path=list(topic_path or []),
            catalog_key=catalog_key,
            is_catalog_curated=catalog_key is not None,
            **kwargs
        )
