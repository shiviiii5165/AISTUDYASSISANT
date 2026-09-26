"""
Live Quiz Engine — AI Learning Intelligence & Remedial Interventions
=====================================================================
Triggered ONLY on explicit teacher action when concept accuracy drops.
Visual intervention utilizes LearnByGenie's deterministic SVG comparison cards first
(0 token cost); explanatory paths make one scoped LLM call.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from app.services.ai.router import router as ai_router
from app.core.logging import logger
from . import repository as repo
from .schemas import LiveEventType
from app.services.video.graphics.svg_diagrams import render_flowchart_svg, render_architecture_stack_svg


async def generate_live_intervention(
    session_id: str,
    action_type: str,
    question_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a scoped remedial intervention for the live classroom.
    action_type in ["explain", "visual", "example", "followup"].
    """
    sess = repo.get_live_session(session_id)
    if not sess:
        raise repo.NotFoundError("Session not found")

    snapshot = sess.get("questions_snapshot", [])
    idx = sess.get("current_question_index", 0)
    q_order = sess.get("question_order", [])

    target_qid = question_id or (q_order[idx] if idx < len(q_order) else None)
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[0] if snapshot else {})

    concept = q_dict.get("concept_id") or sess.get("topic") or "Current Concept"
    correct_ans = str(q_dict.get("correct_answer", ""))
    question_text = q_dict.get("question_text", "")
    explanation = q_dict.get("explanation", "")

    # Identify most selected wrong distractor from class responses
    responses = repo.get_responses_for_session(session_id)
    this_q_resp = [r for r in responses if r.get("question_id") == target_qid]
    wrong_options: Dict[str, int] = {}
    for r in this_q_resp:
        opt = r.get("selected_option_id")
        if opt and not r.get("is_correct"):
            wrong_options[opt] = wrong_options.get(opt, 0) + 1

    top_wrong_distractor = max(wrong_options.items(), key=lambda x: x[1])[0] if wrong_options else None

    # ─── 1. VISUAL (Deterministic First — 0 Token Cost) ──────────────────────
    if action_type == "visual":
        nodes = [
            f"Concept: {concept[:20]}",
            "Key Principle",
            f"Correct: {correct_ans[:20]}",
        ]
        svg_markup = render_flowchart_svg(
            title=f"Core Concept Flow: {concept.title()}",
            nodes=nodes,
            style="academic",
            width=900,
            height=360,
        )

        comparison_card = {
            "title": f"Concept Contrast: {concept.title()}",
            "correct_concept": {
                "heading": "Correct Principle",
                "text": correct_ans,
                "reason": explanation or "Aligns with core educational rules.",
            },
            "common_misconception": {
                "heading": "Common Misconception",
                "text": top_wrong_distractor or "Confusing related terms or conditions",
                "pitfall": "Frequently chosen when misapplying definition boundaries.",
            },
        }

        repo.log_event(session_id, LiveEventType.INTERVENTION_TRIGGERED.value, {"type": "visual", "concept": concept})
        return {
            "type": "visual",
            "concept": concept,
            "svg": svg_markup,
            "comparison": comparison_card,
            "token_cost": 0,
        }

    # ─── 2. EXPLAIN NOW (Scoped Remedial Explanation) ────────────────────────
    elif action_type == "explain":
        prompt = (
            f"You are an expert tutor addressing a live classroom misconception.\n"
            f"Question: {question_text}\n"
            f"Correct Answer: {correct_ans}\n"
            f"Teacher's Explanation: {explanation}\n"
            f"The students frequently fell for this distractor: {top_wrong_distractor or 'an alternative option'}.\n\n"
            f"In 3 concise, friendly, engaging sentences, clarify why '{correct_ans}' is correct and "
            f"gently dispel the misconception behind '{top_wrong_distractor}'. Keep it direct and pedagogical."
        )

        llm_resp = await ai_router.generate_text(
            task="content_generation",
            messages=[
                {"role": "system", "content": "You are a warm, encouraging master teacher."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=250,
        )

        repo.log_event(session_id, LiveEventType.INTERVENTION_TRIGGERED.value, {"type": "explain", "concept": concept})
        return {
            "type": "explain",
            "concept": concept,
            "content": llm_resp.text.strip(),
            "token_cost": llm_resp.tokens_prompt + llm_resp.tokens_completion,
        }

    # ─── 3. GIVE EXAMPLE (One Vivid Counter-Example) ─────────────────────────
    elif action_type == "example":
        prompt = (
            f"Concept: {concept}\n"
            f"Question: {question_text}\n"
            f"Provide ONE memorable, crystal-clear real-world analogy or concrete example illustrating '{concept}' "
            f"and why '{correct_ans}' holds true. Keep it within 3-4 sentences."
        )

        llm_resp = await ai_router.generate_text(
            task="content_generation",
            messages=[
                {"role": "system", "content": "You are a master educator giving clear real-world analogies."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=250,
        )

        repo.log_event(session_id, LiveEventType.INTERVENTION_TRIGGERED.value, {"type": "example", "concept": concept})
        return {
            "type": "example",
            "concept": concept,
            "content": llm_resp.text.strip(),
            "token_cost": llm_resp.tokens_prompt + llm_resp.tokens_completion,
        }

    # ─── 4. ASK FOLLOW-UP (Targeted Diagnostic Check) ────────────────────────
    elif action_type == "followup":
        prompt = (
            f"Concept: {concept}\n"
            f"Context: The class struggled with question: '{question_text}'\n"
            f"Generate ONE quick, multiple-choice formative follow-up question (with 4 options and the correct answer indicated) "
            f"to verify if students now understand '{concept}'.\n"
            f"Respond in JSON format: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct\": \"A\", \"quick_tip\": \"...\"}}"
        )

        llm_resp = await ai_router.generate_text(
            task="content_generation",
            messages=[
                {"role": "system", "content": "You are a diagnostic test generator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=350,
        )

        repo.log_event(session_id, LiveEventType.INTERVENTION_TRIGGERED.value, {"type": "followup", "concept": concept})
        return {
            "type": "followup",
            "concept": concept,
            "raw_content": llm_resp.text.strip(),
            "token_cost": llm_resp.tokens_prompt + llm_resp.tokens_completion,
        }

    else:
        raise ValueError(f"Unknown intervention action: {action_type}")
