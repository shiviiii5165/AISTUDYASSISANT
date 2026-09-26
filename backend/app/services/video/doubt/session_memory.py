"""
LearnByGenie AI Video Teacher V2.2 — Server-Side Doubt Session Memory & Referential Anchors
========================================================================================
Implements:
1. Bounded server-side conversation state (Decision #1 & #8)
   - Zero requirement for frontend to repeatedly transmit entire chat logs.
   - Max 3 recent turns preserved in detail; older turns compressed into concise summaries.
2. Normalized Referential Memory (Decision #2)
   - Resolves deictic & conversational references:
     "acha 20 wala?"
     "nahi uske pehle wala"
     "upar wali step"
     "wahi arrow wala"
   - Maps to normalized anchors: scene, concept, visual_element, worked_example, equation_step,
     timeline_event, previous_tutor_explanation.
"""
import time
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple
from ..schemas import (
    VideoKnowledgePackage, SceneKnowledge, DoubtContext, DoubtAnswer,
    DoubtSessionState, DoubtTurn, ReferentialAnchor, ReferentialAnchorType,
    LearnerMasteryState, ExplanationStrategy, ConfusionType
)
from ..persistence import load_file_json, save_file_json, sync_doubt_to_supabase_background
from app.core.logging import logger


class DoubtSessionMemoryManager:
    """Manages bounded server-side doubt sessions and referential anchors."""

    # In-memory session store (keyed by doubt_session_id)
    _sessions: Dict[str, DoubtSessionState] = {}
    MAX_RECENT_TURNS: int = 3

    @classmethod
    def _init_storage(cls):
        if not cls._sessions:
            raw = load_file_json("doubt_sessions.json", default={})
            if isinstance(raw, dict):
                for sid, sdata in raw.items():
                    try:
                        cls._sessions[sid] = DoubtSessionState.model_validate(sdata)
                    except Exception as e:
                        logger.debug(f"[DoubtSessionMemory] Skipped session {sid}: {e}")

    @classmethod
    def _persist_session(cls, session: DoubtSessionState):
        try:
            cls._sessions[session.doubt_session_id] = session
            serialized = {sid: s.model_dump() for sid, s in cls._sessions.items()}
            save_file_json("doubt_sessions.json", serialized)
            sync_doubt_to_supabase_background(session.model_dump())
        except Exception as e:
            logger.warning(f"[DoubtSessionMemory] Persistence error: {e}")

    @classmethod
    def get_or_create_session(
        cls,
        doubt_session_id: Optional[str],
        lesson_id: str,
        knowledge_pack: Optional[VideoKnowledgePackage] = None
    ) -> DoubtSessionState:
        """Retrieves or creates a bounded session state."""
        cls._init_storage()
        sid = doubt_session_id or f"ds_{uuid.uuid4().hex[:12]}"
        if sid in cls._sessions:
            session = cls._sessions[sid]
            # Ensure lesson_id matches
            if session.lesson_id != lesson_id:
                session.lesson_id = lesson_id
            return session

        # Populate initial referential anchors from video knowledge package
        initial_anchors: List[ReferentialAnchor] = []
        if knowledge_pack:
            initial_anchors = cls.extract_anchors_from_knowledge_pack(knowledge_pack)

        new_session = DoubtSessionState(
            doubt_session_id=sid,
            lesson_id=lesson_id,
            current_focus_concept=knowledge_pack.topic if knowledge_pack else "",
            referential_anchors=initial_anchors,
        )
        cls._persist_session(new_session)
        return new_session

    @classmethod
    def extract_anchors_from_knowledge_pack(cls, kp: VideoKnowledgePackage) -> List[ReferentialAnchor]:
        """Extracts normalized referential anchors from storyboard and knowledge package."""
        anchors: List[ReferentialAnchor] = []
        for idx, s in enumerate(kp.scenes or []):
            # 1. Scene Anchor
            anchors.append(ReferentialAnchor(
                anchor_id=f"anchor_scene_{s.scene_id}",
                anchor_type=ReferentialAnchorType.SCENE,
                label=f"Scene {idx+1}: {s.concept_name}",
                aliases=[f"scene {idx+1}", f"part {idx+1}", f"step {idx+1}", f"scene_{idx+1:02d}", s.scene_id],
                timestamp_sec=s.timestamp_start,
                scene_id=s.scene_id,
                content_snippet=s.narration[:120],
                metadata={"order": idx + 1, "purpose": s.purpose}
            ))

            # 2. Concept Anchor
            if s.concept_name:
                anchors.append(ReferentialAnchor(
                    anchor_id=f"anchor_concept_{s.concept_id}",
                    anchor_type=ReferentialAnchorType.CONCEPT,
                    label=s.concept_name,
                    aliases=[s.concept_name.lower(), s.concept_id.lower()],
                    timestamp_sec=s.timestamp_start,
                    scene_id=s.scene_id,
                    content_snippet=s.teaching_goal or s.narration[:100],
                ))

            # 3. Worked Example / Values Anchor ("20 wala", "value 10", etc.)
            if s.worked_example:
                # Extract numeric values or identifiers inside the worked example
                numbers = re.findall(r"\b\d+\b", s.worked_example)
                aliases = [s.worked_example.lower()] + [f"{n} wala" for n in numbers] + [f"value {n}" for n in numbers] + [f"{n}" for n in numbers]
                anchors.append(ReferentialAnchor(
                    anchor_id=f"anchor_example_{s.scene_id}",
                    anchor_type=ReferentialAnchorType.WORKED_EXAMPLE,
                    label=f"Example in {s.concept_name}: {s.worked_example}",
                    aliases=aliases,
                    timestamp_sec=s.timestamp_start,
                    scene_id=s.scene_id,
                    content_snippet=s.worked_example,
                    metadata={"numbers": numbers}
                ))

            # 4. Visual Elements & Arrows ("arrow wala", "pointer", "diagram", "table", "graph")
            visual_state = s.visual_state or {}
            visual_items = visual_state.get("elements", [])
            for v_item in visual_items:
                v_str = str(v_item).lower()
                v_aliases = [v_str]
                if "arrow" in v_str:
                    v_aliases.extend(["arrow wala", "wahi arrow wala", "teer wala", "pointer"])
                if "box" in v_str or "node" in v_str:
                    v_aliases.extend(["dabba", "box wala", "node wala"])
                anchors.append(ReferentialAnchor(
                    anchor_id=f"anchor_visual_{s.scene_id}_{len(anchors)}",
                    anchor_type=ReferentialAnchorType.VISUAL_ELEMENT,
                    label=f"Visual: {v_item}",
                    aliases=v_aliases,
                    timestamp_sec=s.timestamp_start,
                    scene_id=s.scene_id,
                    content_snippet=f"Visual element on screen: {v_item}",
                ))

            # 5. Equation Steps ("upar wali step", "step 1", "formula")
            if s.visual_strategy in ["formula_breakdown", "step_by_step", "worked_derivation"] or "equation" in (s.purpose or ""):
                anchors.append(ReferentialAnchor(
                    anchor_id=f"anchor_eq_step_{s.scene_id}",
                    anchor_type=ReferentialAnchorType.EQUATION_STEP,
                    label=f"Derivation step in {s.concept_name}",
                    aliases=["upar wali step", "previous step", "pichli step", "equation step", "derivation step", "formula step"],
                    timestamp_sec=s.timestamp_start,
                    scene_id=s.scene_id,
                    content_snippet=s.narration[:100],
                ))

        return anchors

    @classmethod
    def resolve_referential_query(
        cls,
        query: str,
        session: DoubtSessionState,
        current_timestamp: float,
        knowledge_pack: Optional[VideoKnowledgePackage] = None
    ) -> Optional[ReferentialAnchor]:
        """
        Resolves conversational references (Decision #2).
        Supports:
        - "acha 20 wala?" -> worked example / node with value 20
        - "nahi uske pehle wala" -> previous tutor explanation or previous step
        - "upar wali step" -> equation step / previous derivation step
        - "wahi arrow wala" -> visual element with arrow / pointer
        """
        q_lower = query.lower().strip()

        # 1. Check for "pehle wala" / "nahi uske pehle wala" / "previous"
        if any(term in q_lower for term in ["pehle wala", "uske pehle", "previous one", "last explanation", "pehle jo bola"]):
            # Check if there was a previous tutor explanation in session
            if session.recent_turns:
                last_turn = session.recent_turns[-1]
                return ReferentialAnchor(
                    anchor_id=f"prev_explanation_{last_turn.turn_id}",
                    anchor_type=ReferentialAnchorType.PREVIOUS_TUTOR_EXPLANATION,
                    label=f"Previous explanation: '{last_turn.user_question}'",
                    aliases=["pehle wala", "uske pehle wala", "previous explanation"],
                    timestamp_sec=last_turn.timestamp_sec,
                    content_snippet=last_turn.tutor_explanation[:150],
                    metadata={"turn_id": last_turn.turn_id, "strategy": last_turn.strategy_used}
                )

        # 2. Check for "upar wali step" / "pichli step" / "previous step"
        if any(term in q_lower for term in ["upar wali step", "upar wala step", "previous step", "pichli step", "pehle wali step"]):
            for anchor in reversed(session.referential_anchors):
                if anchor.anchor_type == ReferentialAnchorType.EQUATION_STEP:
                    return anchor
            # Fallback to previous scene anchor if before current timestamp
            for anchor in reversed(session.referential_anchors):
                if anchor.anchor_type == ReferentialAnchorType.SCENE and anchor.timestamp_sec < current_timestamp:
                    return anchor

        # 3. Check for specific numbers ("20 wala", "10 wala", "25 wala", "42 wala")
        num_match = re.findall(r"\b(\d+)\b", q_lower)
        if num_match:
            target_num = num_match[0]
            for anchor in session.referential_anchors:
                if anchor.anchor_type == ReferentialAnchorType.WORKED_EXAMPLE:
                    # Check aliases or content
                    if target_num in anchor.metadata.get("numbers", []) or f"{target_num} wala" in anchor.aliases or target_num in anchor.content_snippet:
                        return anchor

        # 4. Check for visual elements ("arrow wala", "teer wala", "wahi arrow", "pointer", "box", "circle")
        if any(term in q_lower for term in ["arrow", "teer", "pointer"]):
            for anchor in session.referential_anchors:
                if anchor.anchor_type == ReferentialAnchorType.VISUAL_ELEMENT and any("arrow" in a or "pointer" in a for a in anchor.aliases):
                    return anchor

        # 5. Direct substring matching against anchor aliases
        for anchor in session.referential_anchors:
            for alias in anchor.aliases:
                if len(alias) >= 3 and alias in q_lower:
                    return anchor

        return None

    @classmethod
    def record_turn(
        cls,
        session_id: str,
        user_question: str,
        timestamp_sec: float,
        tutor_explanation: str,
        strategy_used: str,
        focus_concept: str,
        resolved: bool = True,
        confusion_type: Optional[str] = None
    ) -> DoubtSessionState:
        """
        Records a completed doubt turn, bounds history to MAX_RECENT_TURNS,
        compresses older turns, and adds explanation anchor.
        """
        session = cls._sessions.get(session_id)
        if not session:
            session = DoubtSessionState(
                doubt_session_id=session_id,
                lesson_id="default_lesson",
                current_focus_concept=focus_concept
            )
            cls._sessions[session_id] = session

        turn_id = f"turn_{len(session.recent_turns) + 1}_{int(time.time())}"
        turn = DoubtTurn(
            turn_id=turn_id,
            user_question=user_question,
            timestamp_sec=timestamp_sec,
            tutor_explanation=tutor_explanation,
            strategy_used=strategy_used,
            resolved=resolved,
            created_at=time.time()
        )

        session.recent_turns.append(turn)
        session.timestamp_history.append(timestamp_sec)
        if focus_concept and focus_concept not in session.concept_history:
            session.concept_history.append(focus_concept)
        if strategy_used and strategy_used not in session.strategies_attempted:
            session.strategies_attempted.append(strategy_used)

        session.previous_confusion = session.unresolved_confusion
        if not resolved and confusion_type:
            session.unresolved_confusion = confusion_type
        else:
            session.unresolved_confusion = None

        session.current_focus_concept = focus_concept or session.current_focus_concept

        # Register explanation anchor for conversational deictic reference ("uske pehle wala")
        session.referential_anchors.append(ReferentialAnchor(
            anchor_id=f"anchor_turn_{turn_id}",
            anchor_type=ReferentialAnchorType.PREVIOUS_TUTOR_EXPLANATION,
            label=f"Explanation for: {user_question[:30]}",
            aliases=["pehle wala", "uske pehle", "previous answer", user_question.lower()[:20]],
            timestamp_sec=timestamp_sec,
            content_snippet=tutor_explanation[:150],
            metadata={"turn_id": turn_id, "strategy": strategy_used}
        ))

        # Enforce Bounded Context (Decision #1 & #8)
        if len(session.recent_turns) > cls.MAX_RECENT_TURNS:
            overflow = session.recent_turns[:-cls.MAX_RECENT_TURNS]
            session.recent_turns = session.recent_turns[-cls.MAX_RECENT_TURNS:]
            # Compress overflow into summary
            summarized_snippets = [
                f"[Q: '{t.user_question}' -> Answered with {t.strategy_used}, resolved={t.resolved}]"
                for t in overflow
            ]
            if session.compressed_summary:
                session.compressed_summary += " " + " ".join(summarized_snippets)
            else:
                session.compressed_summary = "Prior context: " + " ".join(summarized_snippets)

        session.last_updated = time.time()
        cls._persist_session(session)
        return session

    @classmethod
    def get_bounded_llm_context(
        cls,
        session_id: str,
        context: DoubtContext,
        resolved_anchor: Optional[ReferentialAnchor] = None
    ) -> Dict[str, Any]:
        """
        Builds the strict, bounded context payload for ModelRouter / LLM (Decision #8).
        Ensures zero unbounded prompt growth.
        """
        session = cls._sessions.get(session_id)
        recent_turns_payload = []
        summary = ""
        strategies_attempted = []
        unresolved = None

        if session:
            summary = session.compressed_summary
            strategies_attempted = list(session.strategies_attempted)
            unresolved = session.unresolved_confusion
            for t in session.recent_turns[-cls.MAX_RECENT_TURNS:]:
                recent_turns_payload.append({
                    "user_question": t.user_question,
                    "tutor_explanation": t.tutor_explanation[:200],  # Bounded
                    "strategy": t.strategy_used,
                    "timestamp": t.timestamp_sec
                })

        payload = {
            "current_concept": context.current_concept,
            "timestamp": context.timestamp,
            "relevant_narration": context.relevant_narration[:250],
            "visual_state_archetype": context.visual_state.get("archetype", "unknown") if context.visual_state else "unknown",
            "unresolved_confusion": unresolved,
            "conversation_summary": summary[:400],
            "recent_turns": recent_turns_payload,
            "strategies_attempted": strategies_attempted,
        }

        if resolved_anchor:
            payload["referential_anchor"] = {
                "type": resolved_anchor.anchor_type.value,
                "label": resolved_anchor.label,
                "content_snippet": resolved_anchor.content_snippet,
                "timestamp": resolved_anchor.timestamp_sec,
            }

        return payload
