"""
Quiz Engine API (§54)
=====================
Canonical quiz endpoints. ALL entry points (Quiz page, PDF "Generate Quiz",
Teach Me "Test Me", Lesson Planner "Create Quiz", Study Pack) call THIS service
— there is no per-entry-point divergence (§3).

Security invariants:
  * Depends(get_current_user) on EVERY endpoint (non-negotiable — security.md
    Critical finding was missing auth on agent endpoints).
  * Every quiz/source access is ownership-checked server-side (§38, §39).
  * Scoring is server-side only (§10, §38); no client score is ever accepted.

Phase-3 gate: generation and single-question regeneration require the RAG
retrieval path. Migrations 007/008 are unverified in this environment (no DB
access to confirm), so those two endpoints return 503 rather than build against
a possibly-unpatched, cross-tenant-leaking retrieval path. The ownership check
still runs first, so the security boundary is exercised even while generation is
gated.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.core.dependencies import get_current_user
from app.models.quiz import (
    GenerateQuizRequest, QuestionEditModel, ReorderQuestionsRequest,
    RegenerateQuestionRequest, StartAttemptRequest, SubmitAttemptRequest,
    UpdateQuizStatusRequest,
)
from app.services.quiz import repository as repo
from app.services.quiz import attempts as attempt_svc
from app.services.quiz.schemas import (
    Quiz, QuizMode, QuizStatus, TEACHER_STATUSES, STUDENT_STATUSES,
)

router = APIRouter()

_GENERATION_BLOCKED_DETAIL = (
    "Quiz generation is temporarily unavailable: the source-retrieval path "
    "depends on migrations 007/008 (cross-tenant isolation) which are not "
    "verified applied in this environment. Generation is gated until the "
    "isolation verifier passes against the live database."
)


def _handle_ownership(exc: Exception):
    if isinstance(exc, repo.NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if isinstance(exc, repo.OwnershipError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    raise exc


# ─── Generation (§54: POST /quizzes) — Phase 3 gated ─────────────────────────

@router.post("/quizzes")
async def generate_quiz(request: GenerateQuizRequest, current_user=Depends(get_current_user)):
    # Idempotent generation (§55): same key → same quiz.
    existing = repo.get_quiz_by_idempotency(current_user.id, request.idempotency_key or "")
    if existing:
        return {"quiz": existing, "idempotent_replay": True}

    # Ownership MUST be verified before any retrieval (§39). This runs even
    # while generation is gated, so the boundary is enforced now.
    try:
        repo.verify_source_ownership(request.source_type, request.source_ids, current_user.id)
    except Exception as e:
        _handle_ownership(e)

    # Phase-3 retrieval + generation is blocked on the migration gate.
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=_GENERATION_BLOCKED_DETAIL)


# ─── Quiz read/list/status/delete ────────────────────────────────────────────

@router.get("/quizzes")
async def list_my_quizzes(current_user=Depends(get_current_user)):
    return {"quizzes": repo.list_quizzes(current_user.id)}


@router.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: str, current_user=Depends(get_current_user)):
    try:
        quiz = repo.verify_quiz_owner(quiz_id, current_user.id)
    except Exception as e:
        _handle_ownership(e)
    questions = repo.get_questions(quiz_id)
    # Owner (teacher) view includes correct answers; this is the authoring view.
    return {"quiz": quiz, "questions": questions}


@router.patch("/quizzes/{quiz_id}/status")
async def set_quiz_status(quiz_id: str, request: UpdateQuizStatusRequest,
                          current_user=Depends(get_current_user)):
    try:
        quiz = repo.verify_quiz_owner(quiz_id, current_user.id)
    except Exception as e:
        _handle_ownership(e)

    # Status must be valid for the quiz's mode (§23).
    try:
        new_status = QuizStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status value")
    valid = TEACHER_STATUSES if quiz.get("mode") == QuizMode.TEACHER.value else STUDENT_STATUSES
    if new_status not in valid:
        raise HTTPException(status_code=422, detail=f"Status '{request.status}' invalid for {quiz.get('mode')} quiz")

    repo.update_quiz_status(quiz_id, new_status.value)
    return {"quiz_id": quiz_id, "status": new_status.value}


@router.delete("/quizzes/{quiz_id}")
async def remove_quiz(quiz_id: str, current_user=Depends(get_current_user)):
    try:
        repo.verify_quiz_owner(quiz_id, current_user.id)
    except Exception as e:
        _handle_ownership(e)
    repo.delete_quiz(quiz_id)
    return {"deleted": quiz_id}


# ─── Question editor (§21, §22, §50) ─────────────────────────────────────────

def _authorize_question(question_id: str, user_id: str) -> Dict[str, Any]:
    q = repo.get_question(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    # Ownership flows through the parent quiz.
    try:
        repo.verify_quiz_owner(q["quiz_id"], user_id)
    except Exception as e:
        _handle_ownership(e)
    return q


@router.patch("/questions/{question_id}")
async def edit_question(question_id: str, request: QuestionEditModel,
                        current_user=Depends(get_current_user)):
    _authorize_question(question_id, current_user.id)
    fields = {k: v for k, v in request.dict(exclude_unset=True).items() if v is not None}
    if "correct_answer" in fields and not isinstance(fields["correct_answer"], list):
        fields["correct_answer"] = [fields["correct_answer"]]
    repo.update_question(question_id, fields)
    return {"question_id": question_id, "updated": list(fields.keys())}


@router.delete("/questions/{question_id}")
async def remove_question(question_id: str, current_user=Depends(get_current_user)):
    _authorize_question(question_id, current_user.id)
    repo.delete_question(question_id)
    return {"deleted": question_id}


@router.post("/quizzes/{quiz_id}/reorder")
async def reorder(quiz_id: str, request: ReorderQuestionsRequest,
                  current_user=Depends(get_current_user)):
    try:
        repo.verify_quiz_owner(quiz_id, current_user.id)
    except Exception as e:
        _handle_ownership(e)
    repo.reorder_questions(quiz_id, request.ordered_question_ids)
    return {"quiz_id": quiz_id, "order": request.ordered_question_ids}


@router.post("/questions/{question_id}/regenerate")
async def regenerate_question(question_id: str, request: RegenerateQuestionRequest,
                              current_user=Depends(get_current_user)):
    # Ownership enforced now; the regeneration itself needs retrieval context and
    # is wired in Phase 3. A failed regeneration must leave the original intact
    # (§58) — hence this never mutates before generation succeeds.
    _authorize_question(question_id, current_user.id)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=_GENERATION_BLOCKED_DETAIL)


# ─── Attempt lifecycle (§54, §57) ────────────────────────────────────────────

@router.post("/attempts/start")
async def start_attempt(request: StartAttemptRequest, current_user=Depends(get_current_user)):
    # The taker must be authorized for the quiz. In V1 that means the owner (a
    # teacher previewing, or a student on their own quiz); broader assignment is
    # a V2 class/cohort concern (§5, §9).
    try:
        quiz = repo.verify_quiz_owner(request.quiz_id, current_user.id)
    except Exception as e:
        _handle_ownership(e)
    return attempt_svc.start_attempt(request.quiz_id, current_user.id, quiz)


@router.post("/attempts/submit")
async def submit_attempt(request: SubmitAttemptRequest, current_user=Depends(get_current_user)):
    answers = {a.question_id: a.answer for a in request.answers}
    try:
        return attempt_svc.submit_attempt(
            attempt_id=request.attempt_id,
            user_id=current_user.id,
            answers=answers,
            idempotency_key=request.idempotency_key,
        )
    except (repo.NotFoundError, repo.OwnershipError) as e:
        _handle_ownership(e)


@router.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: str, current_user=Depends(get_current_user)):
    attempt = repo.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return attempt
