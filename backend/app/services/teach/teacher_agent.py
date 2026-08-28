"""
Teacher Agent — Interactive & Adaptive Pedagogical Generator (Hardened)
========================================================================
Executes single-call Teach + Checkpoint generation, explanation strategy rotation,
grounding verification, telemetry recording, and Socratic / Exam-coach teaching.
"""
import time
import uuid
from typing import Dict, Any, List, Optional
from app.services.ai import router
from .schemas import (
    LessonPlan, ConceptSpec, LearningState, CheckpointSpec, CheckpointType,
    ExplanationStrategy, LearningMode, LearningLevel, LearningDepth, ConceptStatus
)
from .prompts import (
    LESSON_PLANNER_PROMPT, TEACHER_SYSTEM_PROMPT,
    SOCRATIC_SYSTEM_PROMPT, EXAM_COACH_SYSTEM_PROMPT
)
from .context_builder import assemble_teaching_context
from .grounding_evaluator import validate_and_score_grounding
from .telemetry import record_turn_telemetry
from .tools import (
    search_material, get_learning_state, save_learning_state,
    get_lesson_plan, save_lesson_plan
)


STRATEGY_ROTATION = [
    ExplanationStrategy.REAL_WORLD_ANALOGY,
    ExplanationStrategy.CONCRETE_CASE_EXAMPLE,
    ExplanationStrategy.STEP_BY_STEP_BREAKDOWN,
    ExplanationStrategy.VISUAL_MENTAL_MODEL,
    ExplanationStrategy.PREREQUISITE_SCAFFOLDING,
    ExplanationStrategy.FORMAL_EXPLANATION,
]


async def plan_new_lesson(
    topic: str,
    user_id: str,
    level: LearningLevel = LearningLevel.BTECH,
    language: str = "english",
    depth: LearningDepth = LearningDepth.NORMAL,
    mode: LearningMode = LearningMode.INTERACTIVE_TEACHER,
    source_type: str = "topic",
    source_ids: Optional[List[str]] = None,
) -> tuple[LessonPlan, LearningState]:
    """
    Initializes a new structured lesson plan and learning session.
    Retrieves broad overview chunks from uploaded material if connected.
    """
    session_id = str(uuid.uuid4())
    source_ids_clean = [s for s in (source_ids or []) if s]

    # 1. Retrieve initial source evidence if available
    overview_evidence = []
    if source_ids_clean:
        overview_evidence = await search_material(
            query=f"{topic} overview introduction concepts structure fundamentals",
            user_id=user_id,
            source_filters=source_ids_clean,
            limit=4,
        )

    # 2. Formulate prompt for Lesson Planner
    evidence_text = "\n\n".join([f"[{e.get_citation_badge()}]: {e.text[:250]}" for e in overview_evidence])
    planner_input = f"Topic: {topic}\nLevel: {level.value}\nLanguage: {language}\nDepth: {depth.value}\nMode: {mode.value}"
    if evidence_text:
        planner_input += f"\n\nSource Reference Overview:\n{evidence_text}"

    messages = [
        {"role": "system", "content": LESSON_PLANNER_PROMPT},
        {"role": "user", "content": planner_input},
    ]

    # 3. Generate structured lesson plan
    raw_plan = await router.generate_json(
        task="planning",
        messages=messages,
        temperature=0.3,
        max_tokens=2500,
    )

    # 4. Parse concepts and build LessonPlan model
    raw_concepts = raw_plan.get("concepts", [])
    if not raw_concepts:
        raw_concepts = [
            {"id": "concept_1", "name": f"{topic} Core Principles", "order": 1, "summary": "Foundational overview"},
            {"id": "concept_2", "name": f"{topic} Key Mechanisms", "order": 2, "summary": "Operational breakdown"},
            {"id": "concept_3", "name": f"{topic} Real-World Applications", "order": 3, "summary": "Practical implementations"},
        ]

    concept_specs: List[ConceptSpec] = []
    for idx, c in enumerate(raw_concepts):
        c_id = c.get("id") or f"concept_{idx+1}"
        concept_specs.append(ConceptSpec(
            id=c_id,
            name=c.get("name", f"Concept {idx+1}"),
            order=idx + 1,
            summary=c.get("summary", ""),
            status=ConceptStatus.LEARNING if idx == 0 else ConceptStatus.PENDING,
            mastery_score=0.0,
            confidence=0.0,
            active_strategy=ExplanationStrategy.FORMAL_EXPLANATION,
        ))

    plan = LessonPlan(
        topic=raw_plan.get("topic", topic),
        overview=raw_plan.get("overview", ""),
        concepts=concept_specs,
        target_level=level,
        language=language,
        depth=depth,
        mode=mode,
        source_type=source_type,
        source_ids=source_ids_clean,
        user_id=user_id,
    )

    # 5. Initialize LearningState
    first_concept_id = concept_specs[0].id if concept_specs else "concept_1"
    state = LearningState(
        session_id=session_id,
        user_id=user_id,
        topic=plan.topic,
        current_concept_id=first_concept_id,
        covered_concepts=[],
        mastery={c.id: 0.0 for c in concept_specs},
        confidence={c.id: 0.0 for c in concept_specs},
        misconceptions=[],
        strategies_used=[],
        language=language,
        level=level,
        mode=mode,
        depth=depth,
        source_type=source_type,
        source_ids=source_ids_clean,
    )

    # Save to store
    save_lesson_plan(session_id, plan)
    save_learning_state(session_id, state)

    return plan, state


async def teach_current_concept(
    session_id: str,
    user_id: str,
    custom_instruction: str = "",
) -> Dict[str, Any]:
    """
    Teaches the active concept with targeted evidence, embedded micro-question checkpoint,
    citation grounding verification, and telemetry logging.
    """
    t0 = time.time()
    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise ValueError(f"Session {session_id} not found.")

    # 1. Find active ConceptSpec
    active_concept = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
    if not active_concept and plan.concepts:
        active_concept = plan.concepts[0]
        state.current_concept_id = active_concept.id

    # 2. Targeted RAG retrieval for this specific concept
    evidence_items = []
    if state.source_ids:
        evidence_items = await search_material(
            query=f"{state.topic} {active_concept.name if active_concept else ''}",
            user_id=user_id,
            source_filters=state.source_ids,
            limit=4,
        )

    # 3. Select Mode System Prompt
    if state.mode == LearningMode.SOCRATIC_TEACHER:
        system_prompt = SOCRATIC_SYSTEM_PROMPT
    elif state.mode == LearningMode.EXAM_COACH:
        system_prompt = EXAM_COACH_SYSTEM_PROMPT
    else:
        system_prompt = TEACHER_SYSTEM_PROMPT

    # 4. Assemble context package
    user_msg = custom_instruction or f"Teach the concept: {active_concept.name if active_concept else state.topic}. Explain clearly and present one Quick Check question."
    history_turns = 2
    if state.depth == LearningDepth.QUICK:
        history_turns = 1
    elif state.depth == LearningDepth.DEEP:
        history_turns = 3

    messages = assemble_teaching_context(
        system_prompt=system_prompt,
        state=state,
        concept=active_concept,
        evidence_items=evidence_items,
        user_message=user_msg,
        include_history_turns=history_turns,
    )

    # 5. Generate response via ModelRouter
    teacher_res = await router.generate_json(
        task="content_generation",
        messages=messages,
        temperature=0.35,
        max_tokens=3000,
    )

    # 6. Parse output and checkpoint
    raw_explanation = teacher_res.get("response") or teacher_res.get("explanation") or str(teacher_res)
    check_data = teacher_res.get("check") or {}

    # 7. Grounding and Citation Verification
    grounding_score, validated_citations, explanation = validate_and_score_grounding(
        generated_text=raw_explanation,
        evidence_items=evidence_items,
    )

    checkpoint = None
    if check_data and check_data.get("question"):
        checkpoint = CheckpointSpec(
            enabled=check_data.get("enabled", True),
            type=check_data.get("type", "conceptual"),
            question=check_data.get("question", ""),
            expected_skill=check_data.get("expected_skill", ""),
            difficulty=check_data.get("difficulty", "medium"),
            hint=check_data.get("hint"),
            idempotency_key=str(uuid.uuid4())[:8],
        )
        state.active_checkpoint = checkpoint

    # Track strategy used
    used_strat = teacher_res.get("strategy_used") or (active_concept.active_strategy.value if active_concept else "formal_explanation")
    if used_strat not in state.strategies_used:
        state.strategies_used.append(used_strat)

    # Update history turn
    state.recent_history.append({"role": "user", "content": user_msg})
    state.recent_history.append({"role": "assistant", "content": explanation})
    if len(state.recent_history) > 6:
        state.recent_history = state.recent_history[-6:]

    # 8. Record Telemetry
    latency_ms = (time.time() - t0) * 1000
    telemetry = record_turn_telemetry(
        session_id=session_id,
        input_tokens=len(str(messages)) // 4,
        output_tokens=len(str(explanation)) // 4,
        latency_ms=latency_ms,
        retrieved_chunks=len(evidence_items),
        grounding_score=grounding_score,
    )
    state.last_telemetry = telemetry
    save_learning_state(session_id, state)

    return {
        "explanation": explanation,
        "checkpoint": checkpoint.dict() if checkpoint else None,
        "citations": validated_citations,
        "concept": active_concept.dict() if active_concept else None,
        "strategy_used": used_strat,
        "grounding_score": grounding_score,
    }


async def adapt_explanation_strategy(
    session_id: str,
    user_id: str,
    reason: str = "student_confused",
) -> Dict[str, Any]:
    """
    Switches to an untried pedagogical strategy and re-explains the current concept.
    """
    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise ValueError(f"Session {session_id} not found.")

    active_concept = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
    if not active_concept:
        return await teach_current_concept(session_id, user_id)

    # Find next untried strategy
    current_strat = active_concept.active_strategy
    next_strat = ExplanationStrategy.REAL_WORLD_ANALOGY
    for s in STRATEGY_ROTATION:
        if s.value not in state.strategies_used and s != current_strat:
            next_strat = s
            break

    active_concept.active_strategy = next_strat
    active_concept.attempts_count += 1
    save_lesson_plan(session_id, plan)

    instruction = f"The student didn't fully grasp the previous explanation. Re-explain {active_concept.name} using a DIFFERENT strategy: '{next_strat.value}'. Make it intuitive, concrete, and provide a simpler quick check."
    return await teach_current_concept(session_id, user_id, custom_instruction=instruction)


async def self_explain_concept(
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Prompts the student to explain the active concept in their own words ('Explain it back to me').
    """
    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise ValueError(f"Session {session_id} not found.")

    active_concept = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
    concept_name = active_concept.name if active_concept else state.topic

    inst = f"Ask the student to explain '{concept_name}' in their own words as if they were explaining it to a fellow student."
    return await teach_current_concept(session_id, user_id, custom_instruction=inst)
