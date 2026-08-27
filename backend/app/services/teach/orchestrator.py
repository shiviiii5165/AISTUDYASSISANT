"""
Teach Me Orchestrator — Central Session & Command Coordinator (Hardened)
========================================================================
Coordinates pedagogical workflows, command dispatches, concept progression,
session ownership validation, and deterministic session summaries.
"""
from typing import Dict, Any, Optional, List
from .schemas import (
    LearningMode, LearningLevel, LearningDepth,
    LessonPlan, LearningState, ConceptStatus
)
from .teacher_agent import (
    plan_new_lesson, teach_current_concept,
    adapt_explanation_strategy, self_explain_concept
)
from .assessment_agent import evaluate_student_answer
from .telemetry import get_session_aggregate_metrics
from .tools import (
    get_learning_state, save_learning_state,
    get_lesson_plan, save_lesson_plan,
    get_next_concept, mark_concept_complete,
    verify_session_ownership
)


async def start_teaching_session(
    topic: str,
    user_id: str,
    level: str = "btech",
    language: str = "english",
    depth: str = "normal",
    mode: str = "interactive_teacher",
    source_type: str = "topic",
    source_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    1. Plans the lesson roadmap.
    2. Immediately teaches the first concept with an embedded checkpoint.
    """
    try:
        level_enum = LearningLevel(level.lower())
    except ValueError:
        level_enum = LearningLevel.BTECH

    try:
        mode_enum = LearningMode(mode.lower())
    except ValueError:
        mode_enum = LearningMode.INTERACTIVE_TEACHER

    try:
        depth_enum = LearningDepth(depth.lower())
    except ValueError:
        depth_enum = LearningDepth.NORMAL

    # 1. Plan lesson roadmap
    plan, state = await plan_new_lesson(
        topic=topic,
        user_id=user_id,
        level=level_enum,
        language=language,
        depth=depth_enum,
        mode=mode_enum,
        source_type=source_type,
        source_ids=source_ids,
    )

    # 2. Teach initial concept
    first_lesson_turn = await teach_current_concept(
        session_id=state.session_id,
        user_id=user_id,
    )

    return {
        "session_id": state.session_id,
        "plan": plan.dict(),
        "state": state.dict(),
        "initial_turn": first_lesson_turn,
    }


async def handle_user_turn(
    session_id: str,
    user_message: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handles an interactive conversational turn with ownership check."""
    if not verify_session_ownership(session_id, user_id):
        raise PermissionError("Unauthorized access to teaching session.")

    return await teach_current_concept(
        session_id=session_id,
        user_id=user_id,
        custom_instruction=user_message,
    )


async def handle_quick_command(
    session_id: str,
    command: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Dispatches quick pedagogical actions without restarting or replanning.
    Enforces session ownership verification.
    """
    if not verify_session_ownership(session_id, user_id):
        raise PermissionError("Unauthorized access to teaching session.")

    cmd = command.strip().lower()
    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise ValueError(f"Session {session_id} not found.")

    if cmd in ["continue", "next_concept"]:
        # 1. Mark current concept complete
        if state.current_concept_id:
            mark_concept_complete(session_id, state.current_concept_id)

        # 2. Advance to next pending concept
        next_c = get_next_concept(session_id)
        if next_c:
            state.current_concept_id = next_c.id
            next_c.status = ConceptStatus.LEARNING
            save_learning_state(session_id, state)
            save_lesson_plan(session_id, plan)

            turn_res = await teach_current_concept(session_id, user_id)
            return {
                "action": "advanced_concept",
                "concept": next_c.dict(),
                "turn": turn_res,
            }
        else:
            summary = generate_deterministic_summary(state, plan)
            return {
                "action": "lesson_completed",
                "message": summary,
                "plan": plan.dict(),
            }

    elif cmd in ["explain_again", "make_simpler", "dont_understand"]:
        # Rotate strategy without replanning
        turn_res = await adapt_explanation_strategy(session_id, user_id, reason=cmd)
        return {
            "action": "strategy_switched",
            "turn": turn_res,
        }

    elif cmd == "go_deeper":
        # Deepen current concept
        active_c = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
        inst = f"Deep dive into '{active_c.name if active_c else state.topic}'. Provide advanced mechanics, underlying architectural trade-offs, and an edge case."
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=inst)
        return {
            "action": "deepened",
            "turn": turn_res,
        }

    elif cmd == "give_example":
        # Concrete example only
        active_c = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
        inst = f"Provide a vivid, real-world illustrated example for '{active_c.name if active_c else state.topic}' with realistic metrics and component names."
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=inst)
        return {
            "action": "example_provided",
            "turn": turn_res,
        }

    elif cmd in ["show_visual", "visual_explanation"]:
        # Visual mental model / architectural diagram
        active_c = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
        inst = f"Provide a spatial mental model and clean text/flowchart diagram illustrating '{active_c.name if active_c else state.topic}'."
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=inst)
        return {
            "action": "visual_provided",
            "turn": turn_res,
        }

    elif cmd in ["explain_it_back", "test_me"]:
        # Self-explanation mode
        turn_res = await self_explain_concept(session_id, user_id)
        return {
            "action": "self_explanation_requested",
            "turn": turn_res,
        }

    elif cmd == "ask_question":
        # Generate new checkpoint question
        active_c = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
        inst = f"Formulate a challenging, diagnostic checkpoint question for '{active_c.name if active_c else state.topic}' testing practical application."
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=inst)
        return {
            "action": "question_asked",
            "turn": turn_res,
        }

    elif cmd == "exam_points":
        # Exam mode summary
        active_c = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
        inst = f"Summarize '{active_c.name if active_c else state.topic}' specifically for university exams: 1. Core Definition (Must Remember), 2. Full-Marks Points (Good to Know), 3. Common Student Pitfalls."
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=inst)
        return {
            "action": "exam_points",
            "turn": turn_res,
        }

    else:
        # Fallback to normal turn
        turn_res = await teach_current_concept(session_id, user_id, custom_instruction=command)
        return {
            "action": "general_turn",
            "turn": turn_res,
        }


def generate_deterministic_summary(state: LearningState, plan: LessonPlan) -> str:
    """Generates a structured completion recap directly from persistent state without LLM tokens."""
    mastered_count = len(state.covered_concepts)
    total_count = len(plan.concepts)
    avg_mastery = sum(state.mastery.values()) / max(1, len(state.mastery))
    
    lines = [
        f"🎉 **Lesson Complete: {plan.topic}**\n",
        f"- **Concepts Mastered**: {mastered_count} / {total_count}",
        f"- **Average Topic Mastery**: {int(avg_mastery * 100)}%",
    ]
    if state.misconceptions:
        lines.append(f"- **Key Clarifications Addressed**: {len(state.misconceptions)} conceptual points resolved.")
    lines.append("\nYou can now export this lesson to PowerPoint (.pptx) or test yourself with a Quiz!")
    return "\n".join(lines)
