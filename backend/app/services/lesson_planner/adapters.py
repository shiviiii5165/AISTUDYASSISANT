from typing import List, Dict, Any, Optional
from .schemas import RoadmapStage, LearningRoadmap, ResourceType, ResourceStatus

# Downstream schema imports with safe fallback
try:
    from app.services.presentation.schemas import (
        PresentationConfig, 
        DesignSystem
    )
except ImportError:
    PresentationConfig = None
    DesignSystem = None

try:
    from app.services.video.schemas import (
        VideoConfig,
        SourceType,
        VideoQuality,
        AIIntensity,
        AspectRatio,
        VideoStyle
    )
except ImportError:
    VideoConfig = None


class PPTAdapter:
    """
    Connects a specific RoadmapStage to the existing PowerPoint Presentation Engine.
    Preserves stage objectives, activities, diagrams, and source references.
    """

    @staticmethod
    def create_presentation_config(
        roadmap: LearningRoadmap,
        stage: RoadmapStage,
        theme: str = "blue_professional"
    ) -> Any:
        if PresentationConfig is None:
            raise ImportError("Presentation Engine schema not found.")

        # Build targeted context strictly from canonical stage data
        obj_text = "\n".join([f"- {o.description} ({o.bloom_level.value})" for o in stage.objectives]) or stage.description
        act_text = "\n".join([f"- {a.type.upper()}: {a.title} ({a.duration_minutes}m) - {a.description}" for a in stage.activities])
        chk_text = "\n".join([f"- {q}" for q in stage.checkpoint_questions])
        misc_text = "\n".join([f"- {m}" for m in stage.expected_misconceptions])

        custom_context = (
            f"STAGE CONTEXT FOR POWERPOINT GENERATION:\n"
            f"Topic: {roadmap.topic} -> Stage: {stage.title}\n"
            f"Duration: {stage.duration_minutes} minutes | Level: {roadmap.level}\n\n"
            f"LEARNING OBJECTIVES:\n{obj_text}\n\n"
            f"INSTRUCTIONAL FLOW & ACTIVITIES:\n{act_text}\n\n"
            f"FORMATIVE CHECKPOINTS & MISCONCEPTIONS TO CLARIFY:\n{chk_text}\n{misc_text}\n"
        )

        # PresentationConfig only accepts slide_count in [10..15]; short stages
        # previously requested 8 slides, which raised a ValidationError -> 500.
        slide_count = 10 if stage.duration_minutes <= 15 else 12

        design = DesignSystem.ACADEMIC_CLEAN if DesignSystem else "academic_clean"

        return PresentationConfig(
            topic=f"{stage.title} — {roadmap.topic}",
            slide_count=slide_count,
            audience=roadmap.level,
            language=roadmap.language,
            depth="full",
            design=design,
            theme=theme,
            source_type="general",
            custom_context=custom_context,
            enable_diagrams=True,
            enable_images=True,
            enable_speaker_notes=True,
            enable_sources=True,
            enable_examples=True,
            enable_quiz=bool(stage.checkpoint_questions)
        )


class VideoAdapter:
    """
    Connects a RoadmapStage to the existing AI Video Studio Engine.
    Adapts duration from lecture time to concise high-impact video script.
    """

    @staticmethod
    def create_video_config(
        roadmap: LearningRoadmap,
        stage: RoadmapStage
    ) -> Any:
        if VideoConfig is None:
            raise ImportError("Video Engine schema not found.")

        custom_context = (
            f"EDUCATIONAL VIDEO STORYBOARD CONTEXT:\n"
            f"Topic: {stage.title} (Part of {roadmap.topic})\n"
            f"Core Objective: {stage.description}\n"
            f"Expected Misconceptions to Address: {', '.join(stage.expected_misconceptions)}\n"
            f"Checkpoint Questions: {', '.join(stage.checkpoint_questions)}\n"
        )

        # Video duration is condensed for micro-learning
        if stage.duration_minutes <= 10:
            duration_sec = 60
        elif stage.duration_minutes <= 25:
            duration_sec = 180
        else:
            duration_sec = 300

        return VideoConfig(
            topic=stage.title,
            source_type=SourceType.TOPIC if 'SourceType' in globals() else "topic",
            custom_context=custom_context,
            duration=duration_sec,
            quality=VideoQuality.STANDARD if 'VideoQuality' in globals() else "standard",
            ai_intensity=AIIntensity.BALANCED if 'AIIntensity' in globals() else "balanced",
            aspect_ratio=AspectRatio.LANDSCAPE if 'AspectRatio' in globals() else "16:9",
            language=roadmap.language,
            style=VideoStyle.ACADEMIC if 'VideoStyle' in globals() else "academic",
            audience=roadmap.level,
            depth="normal"
        )


class TeachMeAdapter:
    """
    Formats the stage pedagogical context for the Teach Me Socratic Agent.
    """

    @staticmethod
    def create_teach_me_context(
        roadmap: LearningRoadmap,
        stage: RoadmapStage
    ) -> str:
        objs = "\n".join([f"- {o.description}" for o in stage.objectives]) or stage.description
        prereqs = ", ".join(stage.prerequisite_ids) or "None (Foundational stage)"
        misc = "\n".join([f"- {m}" for m in stage.expected_misconceptions])
        chks = "\n".join([f"- {q}" for q in stage.checkpoint_questions])
        sources = "\n".join([f"- [{s.source_type}] {s.title} (p. {s.page or 'N/A'})" for s in stage.source_refs])

        return (
            f"TEACH ME PEDAGOGICAL BRIEF:\n"
            f"Course / Subject: {roadmap.topic}\n"
            f"Current Concept: {stage.title}\n"
            f"Target Audience Level: {roadmap.level} | Language: {roadmap.language}\n\n"
            f"PREREQUISITES:\n{prereqs}\n\n"
            f"LEARNING OBJECTIVES:\n{objs}\n\n"
            f"STUDENT MISCONCEPTIONS TO ADDRESS:\n{misc}\n\n"
            f"FORMATIVE SOCRATIC CHECKPOINTS:\n{chks}\n\n"
            f"SOURCE PROVENANCE & REFERENCES:\n{sources}\n"
        )


class QuizAdapter:
    """
    Generates targeted stage assessment questions directly aligned to stage objectives and misconceptions.
    """

    @staticmethod
    def generate_stage_quiz_spec(
        roadmap: LearningRoadmap,
        stage: RoadmapStage
    ) -> Dict[str, Any]:
        questions = []
        for i, q in enumerate(stage.checkpoint_questions):
            questions.append({
                "id": f"q_{stage.id}_{i+1}",
                "question": q,
                "options": [
                    f"Option A: Correct application for {stage.title}",
                    f"Option B: Common misconception ({stage.expected_misconceptions[0] if stage.expected_misconceptions else 'Distractor'})",
                    "Option C: Irrelevant parameter",
                    "Option D: Inverted condition"
                ],
                "correct_option": "A",
                "explanation": f"Based on the core principles of {stage.title} taught in this stage.",
                "bloom_level": "apply"
            })

        return {
            "quiz_title": f"{stage.title} Concept Check",
            "topic": stage.title,
            "course": roadmap.topic,
            "stage_id": stage.id,
            "questions": questions
        }


class NotesAdapter:
    """
    Generates curated learner study notes from the canonical stage data without re-researching.
    """

    @staticmethod
    def generate_stage_notes(
        roadmap: LearningRoadmap,
        stage: RoadmapStage,
        mode: str = "Detailed"
    ) -> Dict[str, Any]:
        content_sections = [
            f"# {stage.title}",
            f"**Course:** {roadmap.topic} | **Time:** {stage.duration_minutes} mins\n",
            f"## Overview\n{stage.description}\n",
            "## Key Takeaways",
            "\n".join([f"- **Objective:** {o.description}" for o in stage.objectives]) or f"- {stage.description}",
            "\n## Common Pitfalls & Misconceptions",
            "\n".join([f"- ⚠️ *{m}*" for m in stage.expected_misconceptions]) if stage.expected_misconceptions else "- Master all edge conditions carefully.",
            "\n## Practice Checkpoints",
            "\n".join([f"{i+1}. {q}" for i, q in enumerate(stage.checkpoint_questions)]) if stage.checkpoint_questions else "- Review worked examples."
        ]

        return {
            "title": f"Study Notes: {stage.title}",
            "stage_id": stage.id,
            "mode": mode,
            "markdown_content": "\n\n".join(content_sections),
            "source_references": [s.model_dump() for s in stage.source_refs]
        }
