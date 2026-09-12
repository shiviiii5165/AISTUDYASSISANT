"""
Official Documentation Engine for Lesson Planner VNext
======================================================
Implements Section 36:
For fast-changing technologies (React, Python, Supabase, PyTorch, LangChain, ESP-IDF),
official documentation takes the highest priority over generic blogs.

Priority Ranking:
1. Official Current Docs
2. Official Examples & Tutorials
3. Maintainer Release Notes
4. High-Quality Academic/OER References
"""

import urllib.parse
from typing import List, Dict, Any, Optional
from ...schemas import (
    RoadmapStage, UniversalResourceCard, ResourceScoreBreakdown
)

KNOWN_OFFICIAL_DOCS_DOMAINS = {
    "react": ("https://react.dev/reference/react", "React Official Documentation"),
    "python": ("https://docs.python.org/3/", "Python Official Documentation"),
    "supabase": ("https://supabase.com/docs", "Supabase Official Documentation"),
    "fastapi": ("https://fastapi.tiangolo.com/", "FastAPI Official Documentation"),
    "pytorch": ("https://pytorch.org/docs/stable/", "PyTorch Official Documentation"),
    "tensorflow": ("https://www.tensorflow.org/api_docs", "TensorFlow Documentation"),
    "postgresql": ("https://www.postgresql.org/docs/current/", "PostgreSQL Official Documentation"),
    "docker": ("https://docs.docker.com/", "Docker Documentation"),
    "kubernetes": ("https://kubernetes.io/docs/", "Kubernetes Official Documentation"),
    "esp-idf": ("https://docs.espressif.com/projects/esp-idf/en/latest/", "Espressif ESP-IDF Documentation")
}


class OfficialDocsEngine:
    """
    Ranks and structures official documentation links for fast-moving technologies.
    """

    @classmethod
    def get_official_docs(
        cls,
        topic: str,
        stage: RoadmapStage,
        learner_level: str = "B.Tech"
    ) -> List[UniversalResourceCard]:
        cards: List[UniversalResourceCard] = []
        topic_lower = topic.lower()

        matched_doc = None
        for key, (url, title) in KNOWN_OFFICIAL_DOCS_DOMAINS.items():
            if key in topic_lower:
                matched_doc = (url, title)
                break

        if matched_doc:
            doc_url, doc_title = matched_doc
            cards.append(UniversalResourceCard(
                id=f"doc_{abs(hash(topic)) % 100000}",
                title=f"{doc_title}: {topic} Reference API",
                type="official_docs",
                why_recommended="Primary authoritative standard documentation with latest API specs and official examples.",
                what_it_covers=f"Canonical API reference, syntax specifications, and best practices for {topic}.",
                learner_level=learner_level,
                use_during="demonstration",
                exact_section="API Reference & Core Architecture",
                source_authority=doc_title,
                quality_score=98,
                score_breakdown=ResourceScoreBreakdown(concept_match=98, level_fit=95, authority=99, freshness=98, evidence_quality=98, accessibility=100),
                url=doc_url,
                access_type="open",
                confidence=0.98
            ))

        return cards
