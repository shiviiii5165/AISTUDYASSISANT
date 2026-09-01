"""
Quiz Generation Pipeline (§54 Phase 3)
=======================================
Source → Retrieval → Content Agent → Deterministic Validator → Repair → Persist

Retrieval: hybrid_search_evidence (match_document_chunks RPC, user_id-scoped,
confirmed safe post-audit migration 007/008 fix). Never calls get_all_chunks or
any bare document_chunks query without user_id scope.

Content agent: ModelRouter.generate_text() — same provider/model tier as the
presentation pipeline's content_agent.py (content_generation task → Gemini Flash
with Groq/OpenRouter fallback). No new LLM-calling mechanism introduced.

Validator: pure-Python (zero token cost, §46). Already implemented in validator.py.

Single-question regeneration: per §58 — one bad question must not fail the whole
batch. Each failing question gets one regen attempt; if it still fails, the
original is dropped (never shipped as known-bad).
"""
from __future__ import annotations
from app.core.logging import logger

import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple

from app.services.ai import router as ai_router
from app.services.knowledge.hybrid_search import hybrid_search_evidence
from app.db.supabase_client import supabase

from .schemas import (
    Quiz, QuizQuestion, QuizConfig, QuizMode, QuizStatus,
    QuestionType, Difficulty, SourceRef,
)
from .validator import validate_questions, ValidationReport
from . import repository as repo


# ─── Prompts ──────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are an expert educational quiz generator. Given source material, generate
high-quality quiz questions strictly grounded in that material.

Rules (non-negotiable):
• Each MCQ must have EXACTLY 4 options — no more, no fewer.
• Exactly ONE option must be correct; correct_answer must match option text verbatim.
• No "All of the above", "None of the above", or length/format tells.
• No duplicate or near-identical options within a question.
• question_text, options, and explanation must all be non-empty.
• If source material is provided, every question must be answerable from it —
  no hallucinated facts.
• For source-grounded questions, set source_ref.snippet to a short direct quote.
• Respond with ONLY a valid JSON object — no markdown fences, no extra text.

Output schema:
{
  "questions": [
    {
      "question_text": "...",
      "type": "mcq",
      "options": ["A text", "B text", "C text", "D text"],
      "correct_answer": "A text",
      "explanation": "...",
      "difficulty": "easy|medium|hard",
      "source_ref": {
        "source_type": "pdf|ppt|topic|stage",
        "source_id": "...",
        "page": null,
        "slide": null,
        "snippet": "..."
      }
    }
  ]
}"""

_REGEN_SUFFIX = "\n\nIMPORTANT: You are replacing a SINGLE question that failed validation. Generate exactly 1 question."


# ─── Retrieval helpers ────────────────────────────────────────────────────────

async def _retrieve_pdf_context(
    source_ids: List[str],
    user_id: str,
    topic: Optional[str],
    count: int,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieve relevant chunks from owned PDF/PPT sources via hybrid_search_evidence.
    Scoped by user_id at the RPC level — confirmed safe post-audit.
    Returns (formatted_context, source_refs_metadata).
    """
    query = topic or "key concepts definitions examples important principles"
    top_k_per_doc = min(10, max(4, (count * 2) // max(1, len(source_ids))))

    all_evidence = []
    for doc_id in source_ids:
        items = await hybrid_search_evidence(
            user_id=user_id,
            query=query,
            document_id=doc_id,
            top_k=top_k_per_doc,
        )
        all_evidence.extend(items)

    # Sort by relevance, de-duplicate by (source_id, page/slide)
    all_evidence.sort(key=lambda e: e.relevance_score, reverse=True)
    seen: set = set()
    context_parts: List[str] = []
    refs: List[Dict[str, Any]] = []

    for ev in all_evidence:
        key = (ev.source_id, ev.page, ev.slide)
        if key in seen:
            continue
        seen.add(key)

        loc = (
            f"Page {ev.page}" if ev.page
            else (f"Slide {ev.slide}" if ev.slide else "")
        )
        context_parts.append(f"[{ev.source_name} {loc}]: {ev.text}")
        refs.append({
            "source_type": ev.source_type.value,
            "source_id": ev.source_id,
            "page": ev.page,
            "slide": ev.slide,
            "snippet": ev.text[:120],
        })

    return "\n\n---\n\n".join(context_parts), refs


async def _retrieve_stage_context(stage_id: str, user_id: str) -> str:
    """
    Fetch stage content from roadmap_stages, ownership-checked via the parent
    learning_roadmaps.user_id.
    """
    if not supabase or not stage_id:
        return ""
    try:
        res = (
            supabase.table("roadmap_stages")
            .select("*, learning_roadmaps!inner(user_id, topic)")
            .eq("id", stage_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return ""

        row = rows[0]
        roadmap = row.get("learning_roadmaps") or {}
        if roadmap.get("user_id") != user_id:
            return ""  # not owner — ownership already verified at API level, this is defence-in-depth

        parts: List[str] = []
        roadmap_topic = roadmap.get("topic", "")
        stage_title = row.get("title", "")
        if roadmap_topic:
            parts.append(f"Course Topic: {roadmap_topic}")
        if stage_title:
            parts.append(f"Stage: {stage_title}")

        raw = row.get("stage_json") or row.get("stage_data") or row.get("config") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}

        objs = raw.get("objectives", [])
        if objs:
            parts.append("Learning Objectives:")
            for o in objs:
                desc = o.get("description", "") if isinstance(o, dict) else str(o)
                if desc:
                    parts.append(f"  - {desc}")

        checkpoints = raw.get("checkpoint_questions", [])
        if checkpoints:
            parts.append("Formative Checkpoint Questions:")
            for q in checkpoints:
                parts.append(f"  - {q}")

        activities = raw.get("activities", [])
        if activities:
            parts.append("Stage Activities:")
            for a in activities:
                if isinstance(a, dict):
                    t = a.get("title", "")
                    d = a.get("description", "")
                    if t or d:
                        parts.append(f"  - {t}: {d}" if t else f"  - {d}")

        misconceptions = raw.get("expected_misconceptions", [])
        if misconceptions:
            parts.append("Common Misconceptions to Address:")
            for m in misconceptions:
                parts.append(f"  - {m}")

        return "\n".join(parts)
    except Exception as e:
        logger.error(f"[QuizGenerator] Stage context error: {e}")
        return ""


# ─── Content agent ────────────────────────────────────────────────────────────

async def _call_content_agent(
    context: str,
    topic: Optional[str],
    config: QuizConfig,
    source_ids: List[str],
    source_type: str,
    count: int,
    is_regen: bool = False,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    LLM call via ModelRouter (content_generation task).
    Returns (raw_question_dicts, prompt_tokens, completion_tokens).
    Uses generate_text so we get actual token counts from the LLMResponse.
    """
    diff_val = config.difficulty.value if hasattr(config.difficulty, "value") else config.difficulty
    types_str = ", ".join(
        t.value if hasattr(t, "value") else t for t in config.types
    )
    primary_source_id = source_ids[0] if source_ids else None

    user_content = (
        f"Topic: {topic or 'General'}\n"
        f"Difficulty: {diff_val}\n"
        f"Question types requested: {types_str}\n"
        f"Number of questions to generate: {count}\n"
        f"Language: {config.language}\n"
        f"Source type: {source_type}\n"
    )
    if primary_source_id:
        user_content += f"Source ID (use in source_ref.source_id): {primary_source_id}\n"

    if context:
        user_content += f"\nSource Material (base ALL questions on this — no hallucination):\n{context}"
    else:
        user_content += "\nNo source material provided. Generate topic-knowledge questions."

    system = _SYSTEM + (_REGEN_SUFFIX if is_regen else "")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    try:
        llm_resp = await ai_router.generate_text(
            task="content_generation",
            messages=messages,
            temperature=0.4,
            max_tokens=4096,
        )
        raw_text = llm_resp.text
        prompt_tok = llm_resp.tokens_prompt
        completion_tok = llm_resp.tokens_completion
    except Exception as e:
        raise RuntimeError(f"Content agent LLM call failed: {e}") from e

    # Parse JSON from the text response
    raw_questions = _parse_llm_json(raw_text)
    return raw_questions, prompt_tok, completion_tok


def _parse_llm_json(text: str) -> List[Dict[str, Any]]:
    """Extract question list from LLM text response with repair fallbacks."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try direct parse
    try:
        data = json.loads(text, strict=False)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("questions", [])
    except Exception:
        pass

    # Remove trailing commas
    text_fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        data = json.loads(text_fixed, strict=False)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("questions", [])
    except Exception:
        pass

    # Extract JSON object
    m = re.search(r'\{[\s\S]*\}', text_fixed)
    if m:
        try:
            data = json.loads(m.group(0), strict=False)
            return data.get("questions", []) if isinstance(data, dict) else []
        except Exception:
            pass

    logger.info(f"[QuizGenerator] Could not parse LLM JSON. Snippet: {text[:300]}")
    return []


# ─── Question object parser ───────────────────────────────────────────────────

def _coerce_question(raw: Dict[str, Any], idx: int) -> Optional[QuizQuestion]:
    """Coerce a raw LLM dict into a QuizQuestion with safe defaults."""
    try:
        try:
            q_type = QuestionType(raw.get("type", "mcq"))
        except ValueError:
            q_type = QuestionType.MCQ

        try:
            difficulty = Difficulty(raw.get("difficulty", "medium"))
        except ValueError:
            difficulty = Difficulty.MEDIUM

        options = [str(o) for o in raw.get("options", []) if o]
        correct_answer = str(raw.get("correct_answer", "")).strip()

        source_ref = None
        raw_ref = raw.get("source_ref")
        if raw_ref and isinstance(raw_ref, dict):
            source_ref = SourceRef(
                source_type=raw_ref.get("source_type", "general"),
                source_id=raw_ref.get("source_id"),
                page=raw_ref.get("page"),
                slide=raw_ref.get("slide"),
                snippet=raw_ref.get("snippet"),
            )

        return QuizQuestion(
            question_text=str(raw.get("question_text", "")).strip(),
            type=q_type,
            options=options,
            correct_answer=correct_answer,
            explanation=str(raw.get("explanation", "")).strip(),
            difficulty=difficulty,
            source_ref=source_ref,
            order_index=idx,
        )
    except Exception as e:
        logger.error(f"[QuizGenerator] Coerce failed for question #{idx}: {e}")
        return None


# ─── Main pipeline entry point ────────────────────────────────────────────────

async def run_quiz_generation(payload, user_id: str) -> Dict[str, Any]:
    """
    Full pipeline: Retrieve → Generate → Validate → Repair → Persist.
    Returns dict with quiz, questions, validation summary, and token usage.
    """
    config = QuizConfig(
        question_count=payload.config.question_count,
        difficulty=Difficulty(payload.config.difficulty),
        types=[QuestionType(t) for t in payload.config.types],
        language=payload.config.language,
        shuffle_questions=payload.config.shuffle_questions,
        shuffle_options=payload.config.shuffle_options,
        timer_seconds=payload.config.timer_seconds,
        adaptive=payload.config.adaptive,
    )
    count = config.question_count

    # ── Step 1: Retrieve source context ──────────────────────────────────────
    context = ""
    if payload.source_type in ("pdf", "ppt") and payload.source_ids:
        context, _ = await _retrieve_pdf_context(
            source_ids=list(payload.source_ids),
            user_id=user_id,
            topic=payload.topic,
            count=count,
        )
    elif payload.source_type == "stage" and payload.stage_id:
        context = await _retrieve_stage_context(payload.stage_id, user_id)

    # ── Step 2: LLM generation batch ─────────────────────────────────────────
    raw_list, prompt_tok, completion_tok = await _call_content_agent(
        context=context,
        topic=payload.topic,
        config=config,
        source_ids=list(payload.source_ids),
        source_type=payload.source_type,
        count=count,
    )

    # ── Step 3: Parse into QuizQuestion objects ───────────────────────────────
    parsed: List[QuizQuestion] = []
    for i, raw in enumerate(raw_list):
        q = _coerce_question(raw, i)
        if q:
            parsed.append(q)

    # ── Step 4: Deterministic validator ──────────────────────────────────────
    report = validate_questions(parsed)

    # Indices of questions that failed validation
    failed_indices: set = set(iss.index for iss in report.issues if iss.index >= 0)
    failed_indices.update(j for _, j in report.duplicate_pairs)

    # ── Step 5: Single-question regeneration (§58) ────────────────────────────
    regen_log: List[Dict[str, Any]] = []
    repaired: List[QuizQuestion] = list(parsed)
    regen_prompt_tok = 0
    regen_completion_tok = 0

    for idx in sorted(failed_indices):
        if idx >= len(repaired):
            continue
        issues_for_q = [iss.code for iss in report.issues if iss.index == idx]
        is_dup = any(j == idx for _, j in report.duplicate_pairs)
        reason_codes = issues_for_q + (["duplicate_question"] if is_dup else [])

        try:
            regen_raw, rt, rc = await _call_content_agent(
                context=context,
                topic=payload.topic,
                config=QuizConfig(
                    question_count=1,
                    difficulty=config.difficulty,
                    types=config.types,
                    language=config.language,
                ),
                source_ids=list(payload.source_ids),
                source_type=payload.source_type,
                count=1,
                is_regen=True,
            )
            regen_prompt_tok += rt
            regen_completion_tok += rc

            if regen_raw:
                new_q = _coerce_question(regen_raw[0], idx)
                if new_q:
                    check = validate_questions([new_q])
                    if check.ok:
                        repaired[idx] = new_q
                        regen_log.append({"index": idx, "codes": reason_codes, "result": "repaired"})
                    else:
                        regen_log.append({"index": idx, "codes": reason_codes, "result": "still_invalid"})
                else:
                    regen_log.append({"index": idx, "codes": reason_codes, "result": "parse_failed"})
            else:
                regen_log.append({"index": idx, "codes": reason_codes, "result": "empty_llm_response"})
        except Exception as e:
            regen_log.append({"index": idx, "codes": reason_codes, "result": f"error:{str(e)[:80]}"})

    # ── Step 6: Final validation pass — drop any still-bad questions ──────────
    final_report = validate_questions(repaired)
    still_bad = {iss.index for iss in final_report.issues if iss.index >= 0}
    final_qs = [q for i, q in enumerate(repaired) if i not in still_bad]
    for i, q in enumerate(final_qs):
        q.order_index = i

    # ── Step 7: Persist ───────────────────────────────────────────────────────
    mode = QuizMode.TEACHER if getattr(payload, "mode", "student") == "teacher" else QuizMode.STUDENT
    quiz_record = Quiz(
        owner_user_id=user_id,
        mode=mode,
        title=payload.title or f"Quiz: {payload.topic or payload.source_type.title()}",
        source_type=payload.source_type,
        source_ids=list(payload.source_ids),
        topic=payload.topic,
        status=QuizStatus.DRAFT,
        config=config,
        cache_key=f"idem:{payload.idempotency_key}" if payload.idempotency_key else None,
        roadmap_id=getattr(payload, "roadmap_id", None),
        stage_id=getattr(payload, "stage_id", None),
        lesson_id=getattr(payload, "lesson_id", None),
        teach_session_id=getattr(payload, "teach_session_id", None),
    )
    created_quiz = repo.create_quiz(quiz_record)
    quiz_id = created_quiz["id"]
    for q in final_qs:
        q.quiz_id = quiz_id
    created_questions = repo.insert_questions(quiz_id, final_qs)

    return {
        "quiz": created_quiz,
        "questions": created_questions,
        "generation_meta": {
            "source_type": payload.source_type,
            "context_chars": len(context),
            "initial_generated": len(parsed),
            "validator_issues": len(report.issues),
            "duplicate_pairs": len(report.duplicate_pairs),
            "regenerated": regen_log,
            "final_question_count": len(final_qs),
            "token_usage": {
                "initial_prompt": prompt_tok,
                "initial_completion": completion_tok,
                "regen_prompt": regen_prompt_tok,
                "regen_completion": regen_completion_tok,
                "total": prompt_tok + completion_tok + regen_prompt_tok + regen_completion_tok,
            },
        },
    }


async def run_single_question_regeneration(
    question: Dict[str, Any],
    quiz: Dict[str, Any],
    instruction: Optional[str],
    user_id: str,
) -> Dict[str, Any]:
    """
    Regenerate a single question for the /questions/{id}/regenerate endpoint.
    Ownership is already verified by the caller.
    Returns the new question dict if successful, raises on failure.
    """
    source_type = quiz.get("source_type", "topic")
    source_ids = quiz.get("source_ids") or []
    topic = quiz.get("topic")
    config_raw = quiz.get("config") or {}

    diff = config_raw.get("difficulty", "medium")
    types = config_raw.get("types", ["mcq"])
    language = config_raw.get("language", "english")

    config = QuizConfig(
        question_count=1,
        difficulty=Difficulty(diff),
        types=[QuestionType(t) for t in types],
        language=language,
    )

    # Retrieve context (same path as initial generation)
    context = ""
    stage_id = quiz.get("stage_id")
    if source_type in ("pdf", "ppt") and source_ids:
        context, _ = await _retrieve_pdf_context(
            source_ids=source_ids,
            user_id=user_id,
            topic=topic,
            count=1,
        )
    elif source_type == "stage" and stage_id:
        context = await _retrieve_stage_context(stage_id, user_id)

    # Build instruction-aware context addition
    if instruction:
        context = f"Special instruction: {instruction}\n\n{context}" if context else f"Special instruction: {instruction}"

    raw_list, prompt_tok, completion_tok = await _call_content_agent(
        context=context,
        topic=topic,
        config=config,
        source_ids=list(source_ids),
        source_type=source_type,
        count=1,
        is_regen=True,
    )

    if not raw_list:
        raise RuntimeError("LLM returned no questions during regeneration")

    new_q = _coerce_question(raw_list[0], question.get("order_index", 0))
    if not new_q:
        raise RuntimeError("Could not parse regenerated question")

    check = validate_questions([new_q])
    if not check.ok:
        raise RuntimeError(
            f"Regenerated question failed validation: {[i.code for i in check.issues]}"
        )

    new_q.quiz_id = question["quiz_id"]
    new_q.order_index = question.get("order_index", 0)

    return {
        "question_data": new_q.to_db_dict(),
        "token_usage": {
            "prompt": prompt_tok,
            "completion": completion_tok,
        },
    }
