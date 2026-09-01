"""
Teach Me Engine — Deterministic Tools Registry (Hardened & Secure)
==================================================================
Strict function calling registry for multi-source knowledge search,
state persistence, mastery profile updates, misconception tracking, and session ownership security.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..knowledge.sources import SourceType, EvidenceItem
from ..knowledge.hybrid_search import hybrid_search_evidence
from .schemas import LearningState, LessonPlan, ConceptSpec, ConceptStatus, MisconceptionItem, ConceptMasteryProfile
from app.db.supabase_client import supabase


# In-memory session state storage fallback with Supabase sync
SESSION_STORE: Dict[str, Dict[str, Any]] = {}
PLAN_STORE: Dict[str, Dict[str, Any]] = {}


def verify_session_ownership(session_id: str, user_id: str) -> bool:
    """Ensures the authenticated user owns the requested teaching session."""
    if not user_id:
        return False
    state = get_learning_state(session_id)
    if state and state.user_id:
        return state.user_id == user_id
    plan = get_lesson_plan(session_id)
    if plan and plan.user_id:
        return plan.user_id == user_id
    # Fail closed: a session with no recorded owner (or that does not exist) is
    # not owned by anyone. start_teaching_session always sets user_id on the
    # state/plan at creation, so a legitimate session never reaches here.
    return False


async def search_material(
    query: str,
    user_id: str,
    source_filters: Optional[List[str]] = None,
    limit: int = 5,
) -> List[EvidenceItem]:
    """Search grounded materials (PDFs, PPTs, Handwritten notes, YouTube transcripts)."""
    return await hybrid_search_evidence(
        user_id=user_id,
        query=query,
        document_ids=source_filters,
        top_k=limit,
    )


async def get_source_page(doc_id: str, page: int, user_id: str) -> Optional[EvidenceItem]:
    """Retrieve full text of a specific PDF or handwritten note page."""
    items = await hybrid_search_evidence(
        user_id=user_id,
        query="*",
        document_id=doc_id,
        page_filter=page,
        top_k=1,
    )
    return items[0] if items else None


async def get_source_slide(doc_id: str, slide: int, user_id: str) -> Optional[EvidenceItem]:
    """Retrieve full text and notes of a specific presentation slide."""
    items = await hybrid_search_evidence(
        user_id=user_id,
        query="*",
        document_id=doc_id,
        page_filter=slide,
        top_k=1,
    )
    return items[0] if items else None


def get_learning_state(session_id: str) -> Optional[LearningState]:
    """Retrieve active learning state from memory or DB."""
    data = SESSION_STORE.get(session_id)
    if data:
        return LearningState(**data) if isinstance(data, dict) else data
    if supabase:
        try:
            res = supabase.table('teach_sessions').select('state_json').eq('id', session_id).execute()
            if res.data and res.data[0].get('state_json'):
                state_data = res.data[0]['state_json']
                SESSION_STORE[session_id] = state_data
                return LearningState(**state_data)
        except Exception as e:
            print(f'Error fetching state: {e}')
    return None


def save_learning_state(session_id: str, state: LearningState) -> None:
    """Persist learning state in memory and Supabase."""
    state_dict = state.dict()
    SESSION_STORE[session_id] = state_dict

    if supabase:
        try:
            # Upsert into teach_sessions
            payload = {
                "id": session_id,
                "user_id": state.user_id,
                "topic": state.topic,
                "level": state.level.value if hasattr(state.level, 'value') else state.level,
                "mode": state.mode.value if hasattr(state.mode, 'value') else state.mode,
                "depth": state.depth.value if hasattr(state.depth, 'value') else state.depth,
                "state_json": state_dict
            }
            supabase.table('teach_sessions').upsert(payload, on_conflict='id').execute()
        except Exception as e:
            print(f'Error saving state: {e}')


def get_lesson_plan(session_id: str) -> Optional[LessonPlan]:
    """Retrieve full lesson plan for a session."""
    data = PLAN_STORE.get(session_id)
    if data:
        return LessonPlan(**data) if isinstance(data, dict) else data
    if supabase:
        try:
            res = supabase.table('teach_sessions').select('plan_json').eq('id', session_id).execute()
            if res.data and res.data[0].get('plan_json'):
                plan_data = res.data[0]['plan_json']
                PLAN_STORE[session_id] = plan_data
                return LessonPlan(**plan_data)
        except Exception as e:
            print(f'Error fetching plan: {e}')
    return None


def save_lesson_plan(session_id: str, plan: LessonPlan) -> None:
    """Persist lesson plan for a session."""
    PLAN_STORE[session_id] = plan.dict()

    if supabase:
        try:
            # Upsert into teach_sessions
            payload = {
                "id": session_id,
                "user_id": plan.user_id,
                "topic": plan.topic,
                "level": plan.target_level.value if hasattr(plan.target_level, 'value') else plan.target_level,
                "mode": plan.mode.value if hasattr(plan.mode, 'value') else plan.mode,
                "depth": plan.depth.value if hasattr(plan.depth, 'value') else plan.depth,
                "plan_json": plan.dict()
            }
            supabase.table('teach_sessions').upsert(payload, on_conflict='id').execute()
        except Exception as e:
            print(f'Error saving plan: {e}')


def update_mastery_profile(
    session_id: str,
    concept_id: str,
    score: float,
    delta: float,
    confidence: float = 0.5,
    difficulty: str = "medium",
) -> None:
    """Updates the comprehensive concept mastery profile."""
    state = get_learning_state(session_id)
    if state:
        state.mastery[concept_id] = score
        state.confidence[concept_id] = confidence
        
        prof = state.get_current_profile()
        prof.mastery_score = score
        prof.confidence = confidence
        prof.evidence_count += 1
        prof.recent_scores.append(score)
        if len(prof.recent_scores) > 5:
            prof.recent_scores = prof.recent_scores[-5:]
        prof.difficulty_level = difficulty
        prof.last_assessed_at = datetime.utcnow().isoformat()
        
        save_learning_state(session_id, state)

    plan = get_lesson_plan(session_id)
    if plan:
        for c in plan.concepts:
            if c.id == concept_id:
                c.mastery_score = score
                c.confidence = confidence
                if score >= 0.85 and confidence >= 0.50:
                    c.status = ConceptStatus.MASTERED
                elif score >= 0.40:
                    c.status = ConceptStatus.LEARNING
                break
        save_lesson_plan(session_id, plan)


def record_misconception_item(
    session_id: str,
    concept_id: str,
    misconception_text: str,
    severity: str = "medium",
) -> None:
    """Record a structured conceptual misunderstanding blocking mastery."""
    state = get_learning_state(session_id)
    if state and misconception_text:
        now_str = datetime.utcnow().isoformat()
        
        # Check if already present
        found = next((m for m in state.misconceptions if m.concept_id == concept_id and m.misconception.lower() == misconception_text.lower()), None)
        if found:
            found.last_detected = now_str
            found.resolved = False
        else:
            state.misconceptions.append(MisconceptionItem(
                id=str(uuid.uuid4())[:8],
                concept_id=concept_id,
                misconception=misconception_text,
                severity=severity,
                first_detected=now_str,
                last_detected=now_str,
                resolved=False,
            ))
        
        prof = state.get_current_profile()
        if misconception_text not in prof.active_misconceptions:
            prof.active_misconceptions.append(misconception_text)

        save_learning_state(session_id, state)


def resolve_misconception(session_id: str, concept_id: str, misconception_text: Optional[str] = None) -> None:
    """Marks misconceptions as resolved when student demonstrates mastery."""
    state = get_learning_state(session_id)
    if state:
        for m in state.misconceptions:
            if m.concept_id == concept_id:
                if not misconception_text or m.misconception.lower() == misconception_text.lower():
                    m.resolved = True

        prof = state.get_current_profile()
        prof.active_misconceptions = [m.misconception for m in state.misconceptions if m.concept_id == concept_id and not m.resolved]
        save_learning_state(session_id, state)


def mark_concept_complete(session_id: str, concept_id: str) -> None:
    """Marks concept as mastered and moves to covered list."""
    resolve_misconception(session_id, concept_id)
    state = get_learning_state(session_id)
    if state:
        if concept_id not in state.covered_concepts:
            state.covered_concepts.append(concept_id)
        state.mastery[concept_id] = 1.0
        state.confidence[concept_id] = 0.95
        prof = state.get_current_profile()
        prof.mastery_score = 1.0
        prof.confidence = 0.95
        prof.active_misconceptions = []
        save_learning_state(session_id, state)

    plan = get_lesson_plan(session_id)
    if plan:
        for c in plan.concepts:
            if c.id == concept_id:
                c.status = ConceptStatus.MASTERED
                c.mastery_score = 1.0
                c.confidence = 0.95
                break
        save_lesson_plan(session_id, plan)


def get_next_concept(session_id: str) -> Optional[ConceptSpec]:
    """Retrieve the next pending concept from the lesson plan."""
    plan = get_lesson_plan(session_id)
    if not plan:
        return None

    state = get_learning_state(session_id)
    covered = set(state.covered_concepts) if state else set()

    for c in plan.concepts:
        if c.id not in covered and c.status != ConceptStatus.MASTERED:
            return c
    return None


# Backward-compatibility alias
update_mastery = update_mastery_profile
record_misconception = record_misconception_item
