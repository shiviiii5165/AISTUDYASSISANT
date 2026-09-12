"""
Timestamp Context Resolver
==========================
Resolves any video timestamp T against a VideoKnowledgePackage to determine:
- Exactly which scene, concept, and visual state was on screen
- Nearby narration and transcript context
- Connected prerequisites, misconceptions, and worked examples
- Enables deictic doubt resolution ("ye wala part", "this minus sign", "20.next")
"""
from typing import Optional, Dict, Any, List
from ..schemas import VideoKnowledgePackage, SceneKnowledge, DoubtContext


class VideoContextResolver:
    """Extracts granular pedagogical context from timestamp playback."""

    @classmethod
    def resolve_context(
        cls,
        knowledge_pack: VideoKnowledgePackage,
        timestamp: float,
        student_question: str = ""
    ) -> DoubtContext:
        scenes = knowledge_pack.scenes or []
        if not scenes:
            # Fallback empty context
            return DoubtContext(
                video_id=knowledge_pack.video_id,
                timestamp=timestamp,
                current_scene_id="scene_01",
                current_concept=knowledge_pack.topic,
                learner_level=knowledge_pack.learner_level,
                language=knowledge_pack.language,
                student_question=student_question
            )

        # 1. Locate active scene by timestamp interval
        active_scene: Optional[SceneKnowledge] = None
        active_idx = 0

        for idx, s in enumerate(scenes):
            if s.timestamp_start <= timestamp <= s.timestamp_end:
                active_scene = s
                active_idx = idx
                break

        # If timestamp is slightly before or after, clamp to closest scene
        if not active_scene:
            if timestamp < scenes[0].timestamp_start:
                active_scene = scenes[0]
                active_idx = 0
            else:
                active_scene = scenes[-1]
                active_idx = len(scenes) - 1

        # 2. Extract neighbor concepts
        prev_concept = scenes[active_idx - 1].concept_name if active_idx > 0 else None
        next_concept = scenes[active_idx + 1].concept_name if active_idx < len(scenes) - 1 else None

        # 3. Aggregate nearby transcript context
        start_bound = max(0, active_idx - 1)
        end_bound = min(len(scenes), active_idx + 2)
        nearby_transcript = " ".join(s.narration for s in scenes[start_bound:end_bound])

        # 4. Construct visual state snapshot
        visual_snapshot = dict(active_scene.visual_state)
        visual_snapshot["archetype"] = active_scene.visual_strategy
        visual_snapshot["purpose"] = active_scene.purpose

        return DoubtContext(
            video_id=knowledge_pack.video_id,
            timestamp=timestamp,
            current_scene_id=active_scene.scene_id,
            current_concept=active_scene.concept_name or knowledge_pack.topic,
            previous_concept=prev_concept,
            next_concept=next_concept,
            relevant_narration=active_scene.narration,
            visual_state=visual_snapshot,
            misconception_tags=active_scene.misconception_tags,
            prerequisites=active_scene.prerequisite_refs or knowledge_pack.prerequisites,
            examples_shown=[active_scene.worked_example] if active_scene.worked_example else [],
            learner_level=knowledge_pack.learner_level,
            language=knowledge_pack.language,
            student_question=student_question
        )


ContextResolver = VideoContextResolver
