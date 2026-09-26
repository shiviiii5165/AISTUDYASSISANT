"""
Curriculum Resolver for Lesson Planner VNext
============================================
Maps (topic, grade, board/curriculum) into canonical curriculum objectives.

Authoritative Priority Ladder:
  1. Teacher uploaded official curriculum / syllabus
  2. Configured official curriculum (database registry)
  3. Knowledge Pack canonical objectives
  4. LLM-assisted mapping (lowest priority fallback)

Rule: LLM should not invent curriculum when an authoritative source exists.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.db.supabase_client import supabase
from ..schemas import LearningObjective, BloomLevel, KnowledgePack

logger = logging.getLogger("learnbygenie.lesson_planner.curriculum")


class CurriculumResolutionResult(BaseModel):
    curriculum_id: str
    curriculum_version: str = "1.0"
    board: str = "Standard"
    grade_level: str = "B.Tech"
    topic: str
    objectives: List[LearningObjective] = Field(default_factory=list)
    mandatory_concepts: List[str] = Field(default_factory=list)
    optional_concepts: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    assessment_expectations: List[str] = Field(default_factory=list)
    depth_requirements: str = "standard"
    resolution_source: str = "knowledge_pack"  # uploaded_syllabus, configured_official, knowledge_pack, llm_assisted


class CurriculumResolver:
    """
    Deterministically resolves canonical curriculum objectives following the authoritative ladder.
    """

    @classmethod
    async def resolve(
        cls,
        topic: str,
        grade: str = "B.Tech",
        board: str = "Standard",
        subject: str = "General",
        uploaded_context: Optional[str] = None,
        knowledge_pack: Optional[KnowledgePack] = None
    ) -> CurriculumResolutionResult:
        """
        Executes the 4-tier curriculum resolution ladder.
        """
        # --- TIER 1: Teacher Uploaded Official Curriculum / Syllabus ---
        if uploaded_context and len(uploaded_context.strip()) > 30:
            extracted_objs = cls._extract_from_text(uploaded_context, topic)
            if extracted_objs:
                logger.info(f"[CurriculumResolver] Tier 1 Match: Resolved from Teacher Uploaded Syllabus for '{topic}'")
                return CurriculumResolutionResult(
                    curriculum_id=f"custom_upload_{board}_{grade}",
                    curriculum_version="1.0-custom",
                    board=board,
                    grade_level=grade,
                    topic=topic,
                    objectives=extracted_objs,
                    mandatory_concepts=[topic],
                    optional_concepts=[],
                    prerequisites=knowledge_pack.prerequisites if knowledge_pack else [],
                    assessment_expectations=[f"Demonstrate mastery of {topic} per uploaded syllabus"],
                    depth_requirements="custom_uploaded",
                    resolution_source="uploaded_syllabus"
                )

        # --- TIER 2: Configured Official Curriculum Registry (Supabase) ---
        if supabase:
            try:
                res = supabase.table("curriculum_objectives").select("*")\
                    .eq("topic", topic)\
                    .eq("grade_level", grade)\
                    .execute()
                
                if res.data and len(res.data) > 0:
                    objs: List[LearningObjective] = []
                    mandatory = []
                    optional = []
                    prereqs = []
                    
                    for row in res.data:
                        try:
                            b_level = BloomLevel(row.get("bloom_level", "understand").lower())
                        except ValueError:
                            b_level = BloomLevel.UNDERSTAND
                        
                        code = row.get("objective_code") or f"obj_{len(objs)+1}"
                        objs.append(LearningObjective(
                            id=code,
                            description=row["objective_text"],
                            bloom_level=b_level
                        ))
                        if row.get("is_mandatory", True):
                            mandatory.append(row["objective_text"])
                        else:
                            optional.append(row["objective_text"])
                        
                        p_codes = row.get("prerequisite_codes") or []
                        if isinstance(p_codes, list):
                            prereqs.extend(p_codes)

                    logger.info(f"[CurriculumResolver] Tier 2 Match: Official DB Curriculum for '{topic}' ({len(objs)} objectives)")
                    return CurriculumResolutionResult(
                        curriculum_id=f"official_{board}_{grade}",
                        curriculum_version="1.0",
                        board=board,
                        grade_level=grade,
                        topic=topic,
                        objectives=objs,
                        mandatory_concepts=mandatory or [topic],
                        optional_concepts=optional,
                        prerequisites=list(dict.fromkeys(prereqs)),
                        assessment_expectations=[f"Accredited Board Assessment on {topic}"],
                        depth_requirements="official_board",
                        resolution_source="configured_official"
                    )
            except Exception as e:
                logger.warning(f"[CurriculumResolver] Tier 2 lookup error: {e}")

        # --- TIER 3: Knowledge Pack Canonical Objectives ---
        if knowledge_pack and knowledge_pack.learning_objectives:
            logger.info(f"[CurriculumResolver] Tier 3 Match: Knowledge Pack for '{topic}' ({len(knowledge_pack.learning_objectives)} objectives)")
            return CurriculumResolutionResult(
                curriculum_id=f"kp_{knowledge_pack.curriculum}_{knowledge_pack.grade}",
                curriculum_version=knowledge_pack.curriculum_version,
                board=knowledge_pack.curriculum,
                grade_level=knowledge_pack.grade,
                topic=topic,
                objectives=knowledge_pack.learning_objectives,
                mandatory_concepts=[c.get("title", topic) for c in knowledge_pack.concepts] if knowledge_pack.concepts else [topic],
                optional_concepts=[],
                prerequisites=knowledge_pack.prerequisites,
                assessment_expectations=knowledge_pack.assessment_targets or [f"Formative check on {topic}"],
                depth_requirements=knowledge_pack.difficulty,
                resolution_source="knowledge_pack"
            )

        # --- TIER 4: Fallback Canonical Objectives ---
        logger.info(f"[CurriculumResolver] Tier 4 Fallback: Canonical defaults for '{topic}'")
        default_objs = [
            LearningObjective(id="obj_canon_1", description=f"Understand theoretical foundations of {topic}", bloom_level=BloomLevel.UNDERSTAND),
            LearningObjective(id="obj_canon_2", description=f"Analyze and solve problems using {topic}", bloom_level=BloomLevel.ANALYZE)
        ]
        return CurriculumResolutionResult(
            curriculum_id=f"fallback_{board}_{grade}",
            curriculum_version="1.0",
            board=board,
            grade_level=grade,
            topic=topic,
            objectives=default_objs,
            mandatory_concepts=[topic],
            optional_concepts=[],
            prerequisites=[],
            assessment_expectations=[f"Standard mastery check on {topic}"],
            depth_requirements="standard",
            resolution_source="llm_assisted"
        )

    @staticmethod
    def _extract_from_text(text: str, topic: str) -> List[LearningObjective]:
        """Simple deterministic extraction of objective-like lines from text."""
        lines = [line.strip().lstrip("-*•123456789.) ") for line in text.split("\n") if line.strip()]
        objs = []
        for line in lines:
            lower = line.lower()
            if any(lower.startswith(prefix) for prefix in ["understand", "explain", "analyze", "apply", "evaluate", "implement", "identify", "derive"]):
                b_level = BloomLevel.UNDERSTAND
                if lower.startswith("apply") or lower.startswith("implement"):
                    b_level = BloomLevel.APPLY
                elif lower.startswith("analyze"):
                    b_level = BloomLevel.ANALYZE
                elif lower.startswith("evaluate"):
                    b_level = BloomLevel.EVALUATE
                objs.append(LearningObjective(
                    id=f"obj_up_{len(objs)+1}",
                    description=line,
                    bloom_level=b_level
                ))
                if len(objs) >= 5:
                    break
        return objs
