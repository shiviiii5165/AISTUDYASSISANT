import json
import logging
import re
from typing import List, Dict, Any, Optional
from .schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageActivity, 
    LearningObjective, BloomLevel, StageDifferentiation, 
    SourceReference, ClassType, RoadmapStatus
)
from .engine import (
    TimeBudgetEngine, PrerequisiteEngine, 
    StateMachineEngine, ResourceRecommenderEngine, LessonHealthValidator
)
from app.services.ai.router import router as ai_router

logger = logging.getLogger("teachgenie.lesson_planner.generator")


class RoadmapGenerator:
    """
    Intelligent curriculum design generator with prompt parsing, targeted RAG context,
    and Bloom's taxonomy objective generation.
    """

    @staticmethod
    async def parse_natural_language_prompt(prompt_text: str) -> Dict[str, Any]:
        """
        Parses freeform teacher requests into structured configuration parameters.
        """
        default_config = {
            "topic": "DBMS Normalization",
            "course": "Database Management Systems",
            "level": "B.Tech",
            "language": "english",
            "class_type": "Interactive Lecture",
            "duration_minutes": 60,
            "goal": "Explain normal forms with step-by-step decomposition examples and checkpoints.",
            "sources": ["General Knowledge"]
        }

        # Check common duration mentions via regex before LLM
        duration_match = re.search(r'(\d+)\s*(?:min|mins|minute|minutes|m\b)', prompt_text, re.IGNORECASE)
        if duration_match:
            default_config["duration_minutes"] = int(duration_match.group(1))

        parse_prompt = f"""
Extract structured lesson configuration parameters from the teacher's request.

Teacher Prompt:
"{prompt_text}"

Return JSON matching:
{{
  "topic": "Concise subject topic",
  "course": "Broader course name (e.g. Operating Systems, DBMS)",
  "level": "Audience level (e.g. B.Tech, Grade 11, High School, Introductory)",
  "language": "english | hindi | hinglish — default to 'english'; only choose 'hindi' or 'hinglish' if the teacher EXPLICITLY asks for that output language (e.g. 'explain in Hindi', 'Hinglish me'). Do NOT infer it merely from the script/language the prompt itself is written in.",
  "class_type": "Lecture | Interactive Lecture | Tutorial | Lab | Seminar | Workshop | Revision | Exam Review | Remedial",
  "duration_minutes": {default_config['duration_minutes']},
  "goal": "Core teaching outcome"
}}
Return ONLY JSON.
"""
        try:
            res = await ai_router.generate_json(
                task="planning",
                messages=[
                    {"role": "system", "content": "You are a curriculum intake parser. Extract clean JSON configuration."},
                    {"role": "user", "content": parse_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            if res and isinstance(res, dict):
                return {**default_config, **res}
        except Exception as e:
            logger.warning(f"Fallback to heuristic parsing for prompt: {e}")
            # Fallback heuristics
            text_lower = prompt_text.lower()
            if "lab" in text_lower or "coding" in text_lower:
                default_config["class_type"] = "Lab"
            elif "revision" in text_lower or "exam" in text_lower:
                default_config["class_type"] = "Revision"
            
            # Simple topic extraction
            clean_topic = prompt_text.split(" in ")[0].split(" for ")[0].replace("Mujhe ", "").replace("padhana hai", "").strip()
            if len(clean_topic) > 3:
                default_config["topic"] = clean_topic[:50]

        return default_config

    @staticmethod
    async def generate_draft_roadmap(
        topic: str,
        level: str = "B.Tech",
        language: str = "english",
        class_type: str = "Interactive Lecture",
        target_duration_minutes: int = 60,
        custom_context: Optional[str] = None,
        source_refs: Optional[List[Dict[str, Any]]] = None
    ) -> LearningRoadmap:
        """
        Uses ModelRouter with pedagogical prompt to generate a structured LearningRoadmap draft.
        """
        prompt = f"""
You are an expert university curriculum designer and master pedagogue.
Design an adaptive, stage-by-stage learning roadmap for:

Topic: {topic}
Audience Level: {level}
Language: {language} (Mix English & Hindi naturally if Hinglish)
Class Format: {class_type}
Target Duration: {target_duration_minutes} minutes

Verified Course Sources & Notes:
{custom_context or 'Rely on standard accredited university syllabus standards.'}

REQUIREMENTS:
1. Break this lesson into 3 to 6 logical pedagogical stages.
2. For each stage provide:
   - "title": Stage title
   - "description": What concepts are covered and why now
   - "duration_minutes": Allocated time in minutes
   - "objectives": List of 1-2 measurable outcomes with "description" and "bloom_level" ('remember'|'understand'|'apply'|'analyze'|'evaluate'|'create')
   - "teacher_actions": 1-2 concrete instructional actions
   - "student_actions": 1-2 active student participation activities
   - "evidence_of_learning": How understanding is demonstrated
   - "activities": Sequential micro-activities ("type": 'hook'|'explanation'|'example'|'guided_practice'|'independent_practice'|'checkpoint'|'lab_demo'|'debugging'|'summary', "title": "...", "description": "...", "duration_minutes": int)
   - "checkpoint_questions": 1-2 formative diagnostic check questions
   - "expected_misconceptions": 1-2 common pitfalls to preempt
   - "differentiation": {{"core": "...", "support": "...", "extension": "..."}}

OUTPUT JSON SCHEMA:
{{
  "title": "{topic} Master Lesson Roadmap",
  "description": "Comprehensive teaching plan",
  "stages": [
    {{
      "id": "stage_1",
      "concept_id": "concept_1",
      "title": "Stage 1 Title",
      "description": "Stage description...",
      "duration_minutes": 15,
      "objectives": [
        {{ "id": "obj_1", "description": "Students will analyze...", "bloom_level": "analyze" }}
      ],
      "teacher_actions": ["Explains core mechanism with blackboard diagram"],
      "student_actions": ["Identifies anomaly in test table"],
      "evidence_of_learning": "Correct diagnosis of functional dependency",
      "activities": [
        {{ "type": "hook", "title": "Real-world Anomaly", "description": "...", "duration_minutes": 3 }},
        {{ "type": "explanation", "title": "Core Definition", "description": "...", "duration_minutes": 12 }}
      ],
      "checkpoint_questions": ["Why does redundancy occur in unnormalized tables?"],
      "expected_misconceptions": ["Assuming primary key cannot be composite"],
      "differentiation": {{
        "core": "Standard table decomposition",
        "support": "Visual color-coded attributes",
        "extension": "Complex multi-valued dependency edge case"
      }}
    }}
  ]
}}
Return ONLY valid JSON.
"""

        messages = [
            {"role": "system", "content": "You are a JSON-generating university curriculum engine."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await ai_router.generate_json(
                task="planning",
                messages=messages,
                temperature=0.2,
                max_tokens=4000
            )

            stages_data = response.get("stages", [])
            stages: List[RoadmapStage] = []

            for i, s_data in enumerate(stages_data):
                # Objectives
                raw_objs = s_data.get("objectives", [])
                objectives = []
                for j, o in enumerate(raw_objs):
                    b_level = o.get("bloom_level", "understand")
                    try:
                        bloom = BloomLevel(b_level.lower())
                    except ValueError:
                        bloom = BloomLevel.UNDERSTAND
                    objectives.append(LearningObjective(
                        id=o.get("id", f"obj_{i+1}_{j+1}"),
                        description=o.get("description", ""),
                        bloom_level=bloom
                    ))

                # Activities
                activities = [
                    StageActivity(
                        id=f"act_{i+1}_{k+1}",
                        type=act.get("type", "explanation"),
                        title=act.get("title", f"Activity {k+1}"),
                        description=act.get("description", ""),
                        duration_minutes=act.get("duration_minutes", 5)
                    )
                    for k, act in enumerate(s_data.get("activities", []))
                ]

                # Differentiation
                diff_data = s_data.get("differentiation", {})
                differentiation = StageDifferentiation(
                    core=diff_data.get("core", ""),
                    support=diff_data.get("support", ""),
                    extension=diff_data.get("extension", "")
                )

                # Linear prerequisite chain by default
                prereqs = []
                if i > 0 and stages:
                    prereqs.append(stages[i-1].concept_id)

                stage_dur = max(5, s_data.get("duration_minutes", 10))

                stage = RoadmapStage(
                    id=s_data.get("id", f"stage_{i+1}"),
                    concept_id=s_data.get("concept_id", f"concept_{i+1}"),
                    title=s_data.get("title", f"Stage {i+1}"),
                    description=s_data.get("description", ""),
                    sequence=i,
                    duration_minutes=stage_dur,
                    status=StageStatus.AVAILABLE if i == 0 else StageStatus.LOCKED,
                    objective_ids=[o.id for o in objectives],
                    objectives=objectives,
                    prerequisite_ids=prereqs,
                    teacher_actions=s_data.get("teacher_actions", []),
                    student_actions=s_data.get("student_actions", []),
                    evidence_of_learning=s_data.get("evidence_of_learning", ""),
                    activities=activities,
                    checkpoint_questions=s_data.get("checkpoint_questions", []),
                    expected_misconceptions=s_data.get("expected_misconceptions", []),
                    differentiation=differentiation
                )

                # Attach source references if provided
                if source_refs:
                    stage.source_refs = [SourceReference(**sr) for sr in source_refs]
                else:
                    stage.source_refs = [SourceReference(source_type="general", title="Course Syllabus & Verified Curriculum")]

                # Calculate resource recommendations
                try:
                    c_type = ClassType(class_type)
                except ValueError:
                    c_type = ClassType.INTERACTIVE_LECTURE
                ResourceRecommenderEngine.evaluate_stage_resources(stage, c_type)

                stages.append(stage)

            # Map class_type
            try:
                valid_class_type = ClassType(class_type)
            except ValueError:
                valid_class_type = ClassType.INTERACTIVE_LECTURE

            clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', topic.lower()).strip('_')[:32]
            roadmap = LearningRoadmap(
                id=f"roadmap_{clean_id}",
                course_id="default_course",
                topic=topic,
                title=response.get("title", f"{topic} Roadmap"),
                description=response.get("description", f"Structured adaptive teaching roadmap for {topic}."),
                level=level,
                language=language,
                class_type=valid_class_type,
                target_duration_minutes=target_duration_minutes,
                status=RoadmapStatus.DRAFT,
                stages=stages
            )

            # Rebalance timing deterministically to exact target
            TimeBudgetEngine.auto_balance_durations(roadmap)
            PrerequisiteEngine.evaluate_readiness(roadmap)
            StateMachineEngine.determine_next_action(roadmap)
            StateMachineEngine.calculate_overall_progress(roadmap)
            LessonHealthValidator.evaluate_health(roadmap)

            return roadmap

        except Exception as e:
            logger.error(f"Failed to generate roadmap via LLM: {e}")
            # Fallback deterministic builder if LLM is offline
            return RoadmapGenerator._generate_deterministic_fallback(
                topic, level, language, class_type, target_duration_minutes
            )

    @staticmethod
    def _generate_deterministic_fallback(
        topic: str,
        level: str,
        language: str,
        class_type: str,
        duration: int
    ) -> LearningRoadmap:
        """
        Guarantees system never crashes even during external API downtime.
        """
        stages = [
            RoadmapStage(
                id="stage_1",
                concept_id="concept_foundation",
                title=f"{topic} Fundamentals & Intuition",
                description=f"Introduction to the core principles and motivation behind {topic}.",
                sequence=0,
                duration_minutes=max(10, duration // 3),
                status=StageStatus.AVAILABLE,
                objectives=[
                    LearningObjective(id="obj_1", description=f"Understand fundamental definition of {topic}", bloom_level=BloomLevel.UNDERSTAND)
                ],
                teacher_actions=["Presents motivational analogy and definition"],
                student_actions=["Answers interactive baseline poll"],
                evidence_of_learning="Student correctly identifies key motivation",
                activities=[
                    StageActivity(type="hook", title="Introduction", description="Real-world relevance", duration_minutes=5),
                    StageActivity(type="explanation", title="Core Concepts", description="Key definitions and properties", duration_minutes=duration // 3 - 5)
                ],
                checkpoint_questions=[f"What is the main objective of {topic}?"],
                expected_misconceptions=["Confusing definitions with adjacent concepts"]
            ),
            RoadmapStage(
                id="stage_2",
                concept_id="concept_deepdive",
                title=f"{topic} Deep-Dive & Worked Examples",
                description=f"Step-by-step problem walkthrough and mechanism analysis.",
                sequence=1,
                duration_minutes=max(10, duration // 3),
                status=StageStatus.LOCKED,
                prerequisite_ids=["concept_foundation"],
                objectives=[
                    LearningObjective(id="obj_2", description=f"Apply {topic} mechanisms to solve canonical problems", bloom_level=BloomLevel.APPLY)
                ],
                teacher_actions=["Solves comprehensive worked example"],
                student_actions=["Participates in guided problem step"],
                evidence_of_learning="Student successfully completes intermediate derivation",
                activities=[
                    StageActivity(type="example", title="Worked Example", description="Comprehensive derivation", duration_minutes=duration // 3)
                ],
                checkpoint_questions=[f"How do you verify correctness in this step?"],
                expected_misconceptions=["Skipping intermediate boundary conditions"]
            ),
            RoadmapStage(
                id="stage_3",
                concept_id="concept_assessment",
                title=f"{topic} Practice, Assessment & Summary",
                description=f"Independent practice problem, diagnostic quiz, and takeaway review.",
                sequence=2,
                duration_minutes=max(10, duration - 2 * (duration // 3)),
                status=StageStatus.LOCKED,
                prerequisite_ids=["concept_deepdive"],
                objectives=[
                    LearningObjective(id="obj_3", description=f"Analyze edge cases and demonstrate mastery in {topic}", bloom_level=BloomLevel.ANALYZE)
                ],
                teacher_actions=["Moderates peer discussions and clarifies edge cases"],
                student_actions=["Completes independent diagnostic test"],
                evidence_of_learning="Student achieves mastery on checkpoint assessment",
                activities=[
                    StageActivity(type="guided_practice", title="Practice", description="Independent test problem", duration_minutes=10),
                    StageActivity(type="summary", title="Review & Takeaway", description="Key summary points", duration_minutes=5)
                ],
                checkpoint_questions=[f"What are the key trade-offs in {topic}?"],
                expected_misconceptions=["Assuming one solution fits all scenarios"]
            )
        ]

        try:
            valid_class_type = ClassType(class_type)
        except ValueError:
            valid_class_type = ClassType.INTERACTIVE_LECTURE

        for s in stages:
            ResourceRecommenderEngine.evaluate_stage_resources(s, valid_class_type)

        roadmap = LearningRoadmap(
            id=f"roadmap_{re.sub(r'[^a-zA-Z0-9_]', '_', topic.lower()).strip('_')[:32]}",
            course_id="default_course",
            topic=topic,
            title=f"{topic} Roadmap",
            description=f"Structured teaching roadmap for {topic}.",
            level=level,
            language=language,
            class_type=valid_class_type,
            target_duration_minutes=duration,
            stages=stages
        )

        TimeBudgetEngine.auto_balance_durations(roadmap)
        PrerequisiteEngine.evaluate_readiness(roadmap)
        StateMachineEngine.determine_next_action(roadmap)
        StateMachineEngine.calculate_overall_progress(roadmap)
        LessonHealthValidator.evaluate_health(roadmap)

        return roadmap
