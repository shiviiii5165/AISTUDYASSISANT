import asyncio
import logging
import urllib.parse
from typing import List, Optional, Dict, Any
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from .schemas import (
    RoadmapStage,
    ExtraLearningMaterialItem,
    ExtraLearningMaterialsCategories,
    ExtraLearningMaterialsResponse,
)

logger = logging.getLogger("learnbygenie.lesson_planner.materials")

# Backward compatibility aliases
AcademicReferenceItem = ExtraLearningMaterialItem
ResearchPaperItem = ExtraLearningMaterialItem
DocumentationItem = ExtraLearningMaterialItem
ExtraMaterialItem = ExtraLearningMaterialItem


def _sync_ddgs_text(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Synchronous text search using ddgs."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "description": r.get("body", "")
                })
            return results
    except Exception as e:
        logger.warning(f"[LearningMaterials] DDGS search error for '{query[:30]}...': {e}")
        return []


class ExtraLearningMaterialsService:
    """
    Live Extra Learning Materials Hub providing curated academic references,
    arXiv research papers, official documentation, and supplementary deep dives.
    """

    @classmethod
    async def get_learning_materials(
        cls,
        topic: str,
        stage: Optional[RoadmapStage] = None,
        learner_level: str = "B.Tech",
        language: str = "english"
    ) -> ExtraLearningMaterialsResponse:
        """
        Fetch grouped learning materials for a lesson stage across 4 core categories.
        """
        if not getattr(settings, "LESSON_PLANNER_MATERIALS_ENABLED", True):
            return ExtraLearningMaterialsResponse(
                enabled=False,
                status="coming_soon",
                categories=ExtraLearningMaterialsCategories(
                    academic_references=[],
                    research_papers=[],
                    documentation=[],
                    extra_learning_material=[]
                )
            )

        stage_title = stage.title if stage else ""
        concept = f"{topic} {stage_title}".strip()
        logger.info(f"[LearningMaterials] Gathering materials for: '{concept}' ({learner_level})")

        # Execute category searches concurrently
        results = await asyncio.gather(
            cls._fetch_academic_references(concept, topic, learner_level),
            cls._fetch_research_papers(concept, topic, learner_level),
            cls._fetch_documentation(concept, topic, learner_level),
            cls._fetch_extra_material(concept, topic, learner_level),
            return_exceptions=True
        )

        academic_refs = results[0] if isinstance(results[0], list) else []
        papers = results[1] if isinstance(results[1], list) else []
        docs = results[2] if isinstance(results[2], list) else []
        extra = results[3] if isinstance(results[3], list) else []

        categories = ExtraLearningMaterialsCategories(
            academic_references=academic_refs,
            research_papers=papers,
            documentation=docs,
            extra_learning_material=extra
        )

        return ExtraLearningMaterialsResponse(
            enabled=True,
            status="active",
            categories=categories
        )

    @classmethod
    async def _fetch_academic_references(cls, concept: str, topic: str, level: str) -> List[ExtraLearningMaterialItem]:
        """Fetch Wikipedia and authoritative educational references."""
        items: List[ExtraLearningMaterialItem] = []
        try:
            # 1. Wikipedia OpenSearch API
            headers = {"User-Agent": "LearnByGenieApp/1.0 (contact@teachgenie.com)"}
            encoded_query = urllib.parse.quote(concept)
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=2&namespace=0&format=json"

            async with httpx.AsyncClient(timeout=4.0, verify=False) as client:
                resp = await client.get(wiki_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    titles = data[1] if len(data) > 1 else []
                    snippets = data[2] if len(data) > 2 else []
                    links = data[3] if len(data) > 3 else []
                    for i in range(len(titles)):
                        if links[i]:
                            items.append(ExtraLearningMaterialItem(
                                title=titles[i],
                                url=links[i],
                                description=snippets[i] or f"Authoritative encyclopedia reference on {titles[i]}.",
                                source="Wikipedia",
                                type="academic_reference",
                                relevance=0.95,
                                difficulty="intermediate"
                            ))
        except Exception as e:
            logger.warning(f"[LearningMaterials] Wikipedia fetch notice: {e}")

        # If Wikipedia search yielded nothing, fallback via DDGS
        if not items:
            loop = asyncio.get_running_loop()
            ddgs_res = await loop.run_in_executor(
                None, _sync_ddgs_text, f"{concept} wikipedia textbook reference", 2
            )
            for r in ddgs_res:
                items.append(ExtraLearningMaterialItem(
                    title=r["title"],
                    url=r["url"],
                    description=r["description"],
                    source="Academic Reference",
                    type="academic_reference",
                    relevance=0.90,
                    difficulty="intermediate"
                ))

        if not items:
            items.append(ExtraLearningMaterialItem(
                title=f"{topic} Standard Curriculum Reference",
                url=f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(topic)}",
                description=f"Accredited reference and syllabus foundation for {concept}.",
                source="Wikipedia",
                type="academic_reference",
                relevance=0.88,
                difficulty="intermediate"
            ))

        return items[:3]

    @classmethod
    async def _fetch_research_papers(cls, concept: str, topic: str, level: str) -> List[ExtraLearningMaterialItem]:
        """Fetch arXiv and scholarly publications."""
        items: List[ExtraLearningMaterialItem] = []
        try:
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(
                None, _sync_ddgs_text, f"site:arxiv.org {concept}", 3
            )
            for r in raw:
                title = r["title"].replace(" - arXiv", "").replace("[PDF] ", "").strip()
                items.append(ExtraLearningMaterialItem(
                    title=title,
                    url=r["url"],
                    description=r["description"],
                    source="arXiv",
                    type="research_paper",
                    relevance=0.92,
                    difficulty="advanced"
                ))
        except Exception as e:
            logger.warning(f"[LearningMaterials] arXiv search error: {e}")

        if not items:
            items.append(ExtraLearningMaterialItem(
                title=f"Theoretical Foundations of {topic}",
                url=f"https://arxiv.org/search/?query={urllib.parse.quote(topic)}&searchtype=all",
                description=f"Foundational research and literature analyzing {concept}.",
                source="arXiv",
                type="research_paper",
                relevance=0.90,
                difficulty="advanced"
            ))

        return items[:3]

    @classmethod
    async def _fetch_documentation(cls, concept: str, topic: str, level: str) -> List[ExtraLearningMaterialItem]:
        """Fetch official documentation and developer guides."""
        items: List[ExtraLearningMaterialItem] = []
        try:
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(
                None, _sync_ddgs_text, f"{concept} official documentation manual specification", 3
            )
            for r in raw:
                items.append(ExtraLearningMaterialItem(
                    title=r["title"],
                    url=r["url"],
                    description=r["description"],
                    source="Documentation",
                    type="documentation",
                    relevance=0.89,
                    difficulty="intermediate"
                ))
        except Exception as e:
            logger.warning(f"[LearningMaterials] Documentation search error: {e}")

        if not items:
            items.append(ExtraLearningMaterialItem(
                title=f"{topic} Specifications & Manual",
                url=f"https://www.google.com/search?q={urllib.parse.quote(concept + ' documentation')}",
                description=f"Standard reference documentation and architecture specification for {concept}.",
                source="Documentation",
                type="documentation",
                relevance=0.85,
                difficulty="intermediate"
            ))

        return items[:3]

    @classmethod
    async def _fetch_extra_material(cls, concept: str, topic: str, level: str) -> List[ExtraLearningMaterialItem]:
        """Fetch deep-dive guides, cheat sheets, and practical exercises."""
        items: List[ExtraLearningMaterialItem] = []
        try:
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(
                None, _sync_ddgs_text, f"{concept} tutorial worked examples cheat sheet", 3
            )
            for r in raw:
                items.append(ExtraLearningMaterialItem(
                    title=r["title"],
                    url=r["url"],
                    description=r["description"],
                    source="Educational Guide",
                    type="extra_learning_material",
                    relevance=0.86,
                    difficulty="beginner" if "beginner" in level.lower() else "intermediate"
                ))
        except Exception as e:
            logger.warning(f"[LearningMaterials] Extra material search error: {e}")

        if not items:
            items.append(ExtraLearningMaterialItem(
                title=f"{concept}: Worked Examples & Exercises",
                url=f"https://www.google.com/search?q={urllib.parse.quote(concept + ' worked examples tutorial')}",
                description=f"Step-by-step problem walkthroughs and practice questions for {concept}.",
                source="Educational Guide",
                type="extra_learning_material",
                relevance=0.85,
                difficulty="intermediate"
            ))

        return items[:3]
