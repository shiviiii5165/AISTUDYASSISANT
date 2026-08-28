from typing import List, Dict, Any
from .schemas import RoadmapStage, LearningRoadmap

# Try to import downstream schemas
try:
    from app.services.presentation.schemas import (
        PresentationConfig, 
        PresentationSpec, 
        SlideSpec, 
        SlideType, 
        DesignSystem
    )
except ImportError:
    PresentationConfig = None
    PresentationSpec = None

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
    @staticmethod
    def create_presentation_config(roadmap: LearningRoadmap, stage: RoadmapStage, theme: str = "blue_professional") -> "PresentationConfig":
        """
        Creates a PresentationConfig tailored exactly to this stage, bypassing broad topic generation.
        """
        if PresentationConfig is None:
            raise ImportError("Presentation Engine not found.")

        # We inject the stage's specifics into the 'custom_context' so the PPT engine
        # generates slides strictly for this stage's objectives and activities.
        custom_context = (
            f"Stage Title: {stage.title}\n"
            f"Description: {stage.description}\n"
            f"Activities: {[a.type for a in stage.activities]}\n"
            f"Checkpoints: {stage.checkpoint_questions}\n"
            f"Misconceptions to address: {stage.expected_misconceptions}\n"
        )

        return PresentationConfig(
            topic=stage.title,
            slide_count=10, # Standard mini-deck for a stage
            audience=roadmap.level,
            language=roadmap.language,
            depth="full",
            design=DesignSystem.ACADEMIC_CLEAN,
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
    @staticmethod
    def create_video_config(roadmap: LearningRoadmap, stage: RoadmapStage) -> "VideoConfig":
        """
        Creates a VideoConfig tailored exactly to this stage.
        """
        if VideoConfig is None:
            raise ImportError("Video Engine not found.")

        custom_context = (
            f"Stage Title: {stage.title}\n"
            f"Description: {stage.description}\n"
            f"Activities: {[a.type for a in stage.activities]}\n"
            f"Checkpoints: {stage.checkpoint_questions}\n"
            f"Misconceptions to address: {stage.expected_misconceptions}\n"
        )

        # AI video is highly condensed compared to lecture time
        # E.g. A 10 minute lecture might be a 60s video.
        if stage.duration_minutes <= 10:
            duration_sec = 60
        elif stage.duration_minutes <= 20:
            duration_sec = 180
        else:
            duration_sec = 300

        return VideoConfig(
            topic=stage.title,
            source_type=SourceType.TOPIC,
            custom_context=custom_context,
            duration=duration_sec,
            quality=VideoQuality.STANDARD,
            ai_intensity=AIIntensity.BALANCED,
            aspect_ratio=AspectRatio.LANDSCAPE,
            language=roadmap.language,
            style=VideoStyle.ACADEMIC,
            audience=roadmap.level,
            depth="normal"
        )


class TeachMeAdapter:
    @staticmethod
    def create_teach_me_context(roadmap: LearningRoadmap, stage: RoadmapStage) -> str:
        """
        Creates a system prompt context to feed to the Teach Me engine so it teaches
        exactly this stage without re-researching.
        """
        context = (
            f"You are teaching the concept: {stage.title}.\n"
            f"Course Level: {roadmap.level}, Language: {roadmap.language}.\n"
            f"Description: {stage.description}\n"
            "Ensure you address these misconceptions:\n"
            + "\n".join([f"- {m}" for m in stage.expected_misconceptions]) +
            "\nAssess the student using these checkpoint questions:\n"
            + "\n".join([f"- {q}" for q in stage.checkpoint_questions])
        )
        return context
