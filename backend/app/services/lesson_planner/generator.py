import json
import logging
from typing import List, Dict, Any, Optional
from .schemas import LearningRoadmap, RoadmapStage, StageStatus, StageActivity
from app.services.ai.router import router as ai_router

logger = logging.getLogger("teachgenie.lesson_planner.generator")

class RoadmapGenerator:
    @staticmethod
    async def generate_draft_roadmap(
        topic: str,
        level: str,
        language: str,
        class_type: str,
        target_duration_minutes: int,
        context: Optional[str] = None
    ) -> LearningRoadmap:
        """
        Uses the ModelRouter to generate a structured LearningRoadmap draft.
        """
        prompt = f"""
You are an expert curriculum designer and master teacher.
Design a highly structured learning roadmap for the following lesson:

Topic: {topic}
Audience Level: {level}
Language: {language} (If Hinglish, mix English and Hindi naturally)
Class Type: {class_type}
Target Duration: {target_duration_minutes} minutes

Context/Syllabus:
{context or 'None provided. Rely on general expert knowledge.'}

Your goal is to break this topic down into sequential STAGES.
Each stage should represent a distinct concept or activity.

CRITICAL RULES:
1. The total duration of all stages MUST EXACTLY equal {target_duration_minutes} minutes.
2. Output MUST be valid JSON matching this schema:
{{
  "stages": [
    {{
      "id": "stage_1",
      "concept_id": "concept_abc",
      "title": "Stage Title",
      "description": "What will be taught",
      "duration_minutes": 10,
      "activities": [
        {{ "type": "hook", "description": "...", "duration_minutes": 2 }},
        {{ "type": "explanation", "description": "...", "duration_minutes": 8 }}
      ],
      "checkpoint_questions": ["Question 1?"],
      "expected_misconceptions": ["Misconception A"],
      "recommended_resources": ["ppt", "quiz"]
    }}
  ]
}}

Return ONLY JSON. Do not include markdown formatting or explanations.
        """

        messages = [
            {"role": "system", "content": "You are a precise JSON-generating curriculum engine."},
            {"role": "user", "content": prompt}
        ]

        try:
            # We use the planning task policy which favors strong reasoning models (e.g. Llama-3-70b or Gemini 1.5 Pro)
            response = await ai_router.generate_json(
                task="planning",
                messages=messages,
                temperature=0.2,
                max_tokens=4000
            )
            
            stages_data = response.get("stages", [])
            stages = []
            
            for i, s_data in enumerate(stages_data):
                activities = [
                    StageActivity(**act) for act in s_data.get("activities", [])
                ]
                
                # Default previous stage as prerequisite to enforce linear progression initially
                prereqs = []
                if i > 0:
                    prereqs.append(stages[i-1].concept_id)

                stage = RoadmapStage(
                    id=s_data.get("id", f"stage_{i+1}"),
                    concept_id=s_data.get("concept_id", f"concept_{i+1}"),
                    title=s_data.get("title", f"Stage {i+1}"),
                    description=s_data.get("description", ""),
                    duration_minutes=s_data.get("duration_minutes", 10),
                    status=StageStatus.LOCKED if i > 0 else StageStatus.AVAILABLE,
                    activities=activities,
                    checkpoint_questions=s_data.get("checkpoint_questions", []),
                    expected_misconceptions=s_data.get("expected_misconceptions", []),
                    recommended_resources=s_data.get("recommended_resources", []),
                    prerequisite_ids=prereqs
                )
                stages.append(stage)

            roadmap = LearningRoadmap(
                id="draft_" + topic.replace(" ", "_").lower(),
                course_id="default_course",
                topic=topic,
                level=level,
                language=language,
                class_type=class_type,
                target_duration_minutes=target_duration_minutes,
                stages=stages
            )
            
            return roadmap

        except Exception as e:
            logger.error(f"Failed to generate roadmap: {e}")
            raise
