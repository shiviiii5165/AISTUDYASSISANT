"""
Resource Source Registry & Need Detector for Lesson Planner VNext
=================================================================
Central registry of trusted sources and dynamic visibility policy.
Enforces Sections 12, 14, 17, 18 & 33:
- Not every stage needs every resource.
- Show YouTube when visual explanation/demo is helpful; hide if text is sufficient.
- Show Courses (NPTEL / MIT OCW) for university derivations and structured lectures.
- Show Coding when domain is CS/Software and intent is implement/practice/interview.
- Show Research Papers when learner level >= UG Advanced or intent == research.
- NEVER show Q1 journals or IEEE standards to primary/secondary school learners.
- Show Standards when topic involves protocol/engineering specification.
"""

from typing import List, Dict, Any, Set
from pydantic import BaseModel
from ...schemas import (
    CanonicalDomain, TeachingIntent, ProductMode, StageArchetype, RoadmapStage
)
from ..pedagogy import ConceptType


class ResourceSourceEntry(BaseModel):
    source_id: str
    domain: str
    resource_type: str
    authority_level: int  # 0 to 100
    ranking_method: str = "composite"
    freshness_requirement: str = "standard"  # standard, high, strict
    requires_subscription: bool = False
    enabled: bool = True


# In-memory central source registry
BUILTIN_SOURCE_REGISTRY: Dict[str, ResourceSourceEntry] = {
    "youtube_edu": ResourceSourceEntry(
        source_id="youtube_edu",
        domain="all",
        resource_type="video_segment",
        authority_level=85,
        ranking_method="segment_scoring",
        freshness_requirement="standard",
        enabled=True
    ),
    "nptel_course": ResourceSourceEntry(
        source_id="nptel_course",
        domain="engineering,science,mathematics",
        resource_type="course_lecture",
        authority_level=96,
        ranking_method="curriculum_aligned",
        freshness_requirement="standard",
        enabled=True
    ),
    "mit_ocw": ResourceSourceEntry(
        source_id="mit_ocw",
        domain="engineering,science,mathematics,humanities",
        resource_type="course_lecture",
        authority_level=98,
        ranking_method="curriculum_aligned",
        freshness_requirement="standard",
        enabled=True
    ),
    "arxiv_org": ResourceSourceEntry(
        source_id="arxiv_org",
        domain="computer_science,physics,mathematics",
        resource_type="research_paper",
        authority_level=92,
        ranking_method="citation_age_normalized",
        freshness_requirement="high",
        enabled=True
    ),
    "crossref_academic": ResourceSourceEntry(
        source_id="crossref_academic",
        domain="all",
        resource_type="journal_article",
        authority_level=95,
        ranking_method="quartile_indexed",
        freshness_requirement="standard",
        enabled=True
    ),
    "geeksforgeeks": ResourceSourceEntry(
        source_id="geeksforgeeks",
        domain="computer_science,software_engineering",
        resource_type="coding_reference",
        authority_level=88,
        ranking_method="concept_coverage",
        freshness_requirement="standard",
        enabled=True
    ),
    "leetcode": ResourceSourceEntry(
        source_id="leetcode",
        domain="computer_science,software_engineering",
        resource_type="coding_practice",
        authority_level=90,
        ranking_method="difficulty_progression",
        freshness_requirement="standard",
        enabled=True
    ),
    "official_docs": ResourceSourceEntry(
        source_id="official_docs",
        domain="software_engineering,ece",
        resource_type="official_docs",
        authority_level=98,
        ranking_method="version_freshness",
        freshness_requirement="strict",
        enabled=True
    ),
    "open_oer": ResourceSourceEntry(
        source_id="open_oer",
        domain="all",
        resource_type="textbook_reference",
        authority_level=85,
        ranking_method="pedagogical_alignment",
        freshness_requirement="standard",
        enabled=True
    )
}


class ResourceNeedDetector:
    """
    Evaluates which resource types are pedagogically justified for a stage.
    """

    @classmethod
    def evaluate_stage_needs(
        cls,
        stage: RoadmapStage,
        domain: CanonicalDomain,
        intent: TeachingIntent,
        learner_level: str,
        mode: ProductMode
    ) -> Set[str]:
        """
        Returns a set of needed resource keys:
        {'youtube', 'course', 'coding', 'research', 'docs', 'textbook'}
        """
        needs: Set[str] = set()
        level_lower = learner_level.lower()
        is_advanced_higher_ed = any(k in level_lower for k in ["b.tech", "m.tech", "ug", "pg", "phd", "graduate", "university", "college"])
        is_school = any(k in level_lower for k in ["grade", "class", "school", "primary", "secondary"])

        # 1. YouTube Visibility Policy (Sections 4, 12 & 33)
        if is_school or stage.archetype in [
            StageArchetype.HOOK,
            StageArchetype.MENTAL_MODEL,
            StageArchetype.CONCEPT_INTRO,
            StageArchetype.EXPLANATION,
            StageArchetype.DEMONSTRATION,
            StageArchetype.SIMULATION,
            StageArchetype.WORKED_EXAMPLE,
            StageArchetype.REMEDIATION
        ] or len(stage.visual_requirements) > 0:
            needs.add("youtube")

        # 2. Course Intelligence Policy (Sections 9-13)
        # NPTEL / MIT OCW active for higher-ed foundations, derivations, and lectures
        if is_advanced_higher_ed and not is_school:
            if stage.archetype in [
                StageArchetype.MENTAL_MODEL,
                StageArchetype.CONCEPT_INTRO,
                StageArchetype.EXPLANATION,
                StageArchetype.WORKED_EXAMPLE,
                StageArchetype.EXTENSION
            ]:
                needs.add("course")
        elif is_school and stage.archetype in [StageArchetype.CONCEPT_INTRO, StageArchetype.EXPLANATION, StageArchetype.WORKED_EXAMPLE]:
            # School foundational courses (Swayam Prabha / NCERT)
            needs.add("course")

        # 3. Coding Resources Visibility Policy (Sections 14 & 33)
        if domain in [CanonicalDomain.COMPUTER_SCIENCE, CanonicalDomain.SOFTWARE_ENGINEERING]:
            if stage.archetype in [StageArchetype.CODING, StageArchetype.GUIDED_PRACTICE, StageArchetype.INDEPENDENT_PRACTICE] or \
               intent in [TeachingIntent.IMPLEMENT, TeachingIntent.PRACTICE, TeachingIntent.INTERVIEW_PREP, TeachingIntent.PROJECT]:
                needs.add("coding")

        # 4. Official Documentation Visibility Policy (Section 14)
        if domain in [CanonicalDomain.SOFTWARE_ENGINEERING, CanonicalDomain.ECE]:
            needs.add("docs")

        # 5. Research Papers Visibility Policy (Sections 15 & 33)
        # Strictly NEVER show papers to primary or secondary school students
        if not is_school:
            if mode == ProductMode.RESEARCH_ADVANCED or intent == TeachingIntent.RESEARCH:
                needs.add("research")
            elif is_advanced_higher_ed and stage.archetype in [StageArchetype.RESEARCH_REVIEW, StageArchetype.CASE_STUDY, StageArchetype.EXTENSION]:
                needs.add("research")

        # 6. Core Textbook / OER References are universally useful
        needs.add("textbook")

        return needs
