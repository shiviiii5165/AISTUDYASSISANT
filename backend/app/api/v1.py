"""Public /api/v1 contract. Identity always comes from the token, never the request body."""
from __future__ import annotations

import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from app.core.dependencies import AuthenticatedUser, get_current_user, require_role
from app.modules import context, rate_limit
from app.modules.curriculum.ncert_seed import CONCEPTS
from app.modules.error_to_mastery import engine
from app.modules.gamification_v1 import quests
from app.modules.learning_core import math_verifier
from app.modules.privacy import mfa, service as privacy
from app.modules.rag_tutor import service as tutor
from app.modules.rag_tutor.modes import Mode
from app.modules.reporting import dashboards

router = APIRouter()
Confidence = Literal["Sure", "Unsure", "Guess"]


def limit_ip(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limit.allow_ip(ip):
        raise HTTPException(429, "Too many requests", headers={"Retry-After": "60"})


def _class_of(user: AuthenticatedUser) -> int:
    level = context.student_class(user.id)
    if level is None:
        raise HTTPException(409, detail={"code": "class_required", "message": "Set your class in your profile first"})
    return level


def require_learning_consent(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Blocks analytics on a child's data until a guardian has verified consent."""
    if user.role == "student" and not privacy.has_consent(user.id, "learning_analytics"):
        raise HTTPException(403, detail={"code": "consent_required", "purpose": "learning_analytics"})
    return user


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, engine.NotFound):
        return HTTPException(404, "Not found")
    if isinstance(exc, engine.Conflict):
        return HTTPException(409, str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(403, str(exc))
    if isinstance(exc, privacy.ConsentError):
        return HTTPException(exc.status, detail={"code": exc.code})
    raise exc


# ---- Curriculum and maths --------------------------------------------------

@router.get("/curriculum/concepts", dependencies=[Depends(limit_ip)])
def list_concepts(user: AuthenticatedUser = Depends(get_current_user)):
    return [{"concept_id": c.concept_id, "title": c.title, "subject": c.subject, "class_level": c.class_level,
             "prerequisites": list(c.prerequisites), "simulation": c.simulation} for c in CONCEPTS]


class VerifyStepBody(BaseModel):
    previous: str = Field(max_length=200)
    current: str = Field(max_length=200)


@router.post("/math/verify-step", dependencies=[Depends(limit_ip)])
def verify_step(body: VerifyStepBody, user: AuthenticatedUser = Depends(get_current_user)):
    return {"verdict": math_verifier.verify_derivation([body.previous, body.current]).verdict.value}


# ---- Diagnostics -----------------------------------------------------------

class DiagnosticStart(BaseModel):
    subject: Literal["Mathematics", "Science"]


class DiagnosticAnswer(BaseModel):
    item_id: str
    response: str = Field(max_length=200)


@router.post("/diagnostics/start", dependencies=[Depends(limit_ip)])
def diagnostics_start(body: DiagnosticStart, user: AuthenticatedUser = Depends(require_learning_consent)):
    try:
        return engine.start_diagnostic(user.id, body.subject, _class_of(user))
    except (engine.NotFound, engine.Conflict) as exc:
        raise _translate(exc)


@router.post("/diagnostics/{session_id}/answer", dependencies=[Depends(limit_ip)])
def diagnostics_answer(session_id: str, body: DiagnosticAnswer, user: AuthenticatedUser = Depends(require_learning_consent)):
    try:
        return engine.answer_diagnostic(user.id, session_id, body.item_id, body.response)
    except (engine.NotFound, engine.Conflict) as exc:
        raise _translate(exc)


# ---- Practice --------------------------------------------------------------

class PracticeStart(BaseModel):
    concept_id: str
    kind: Literal["practice", "transfer", "retention"] = "practice"


class PracticeSubmit(BaseModel):
    item_id: str
    response: str = Field(max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=80)
    steps: list[str] = Field(default_factory=list, max_length=20)
    confidence: Optional[Confidence] = None
    hints_used: int = Field(default=0, ge=0, le=3)


@router.post("/practice/start", dependencies=[Depends(limit_ip)])
def practice_start(body: PracticeStart, user: AuthenticatedUser = Depends(require_learning_consent)):
    try:
        return engine.start_practice(user.id, body.concept_id, _class_of(user), body.kind)
    except (engine.NotFound, engine.Conflict) as exc:
        raise _translate(exc)


@router.post("/practice/{session_id}/submit", dependencies=[Depends(limit_ip)])
def practice_submit(session_id: str, body: PracticeSubmit, user: AuthenticatedUser = Depends(require_learning_consent)):
    try:
        result = engine.submit(user.id, session_id, body.item_id, body.response, body.idempotency_key,
                               body.steps, body.confidence, body.hints_used)
    except (engine.NotFound, engine.Conflict) as exc:
        raise _translate(exc)
    quests.record_activity(user.id)
    return result


@router.post("/practice/{session_id}/intervention-complete", dependencies=[Depends(limit_ip)])
def practice_intervention(session_id: str, user: AuthenticatedUser = Depends(require_learning_consent)):
    try:
        return engine.complete_intervention(user.id, session_id)
    except engine.NotFound as exc:
        raise _translate(exc)


# ---- Tutor -----------------------------------------------------------------

class TutorAsk(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    mode: Optional[Mode] = None
    concept_id: Optional[str] = None
    session_id: Optional[str] = None
    item_id: Optional[str] = None
    answer: Optional[str] = Field(default=None, max_length=200)
    answers: Optional[dict[str, str]] = None
    confidence: Optional[Confidence] = None
    hint_level: int = Field(default=1, ge=1, le=3)
    fade_stage: int = Field(default=0, ge=0, le=3)
    attribution: Optional[dict] = None
    subject: Optional[Literal["Mathematics", "Science"]] = None


@router.post("/tutor/ask", dependencies=[Depends(limit_ip)])
async def tutor_ask(body: TutorAsk, user: AuthenticatedUser = Depends(require_learning_consent)):
    if not rate_limit.allow_ai_query(user.id):
        raise HTTPException(429, detail={"code": "daily_ai_limit", "limit": 30})
    try:
        return await tutor.ask(tutor.Ask(student_id=user.id, student_class=_class_of(user), **body.model_dump()))
    except LookupError:
        raise HTTPException(404, "Not found")


# ---- Consent, privacy and MFA ----------------------------------------------

class OtpRequest(BaseModel):
    guardian_contact: str = Field(min_length=5, max_length=120)
    purpose: Literal["learning_analytics", "parent_reports", "school_sharing"] = "learning_analytics"


class OtpVerify(BaseModel):
    request_id: str
    otp: str = Field(pattern=r"^\d{6}$")


class Withdraw(BaseModel):
    purpose: Literal["learning_analytics", "parent_reports", "school_sharing"]


class Erase(BaseModel):
    confirm: Literal["ERASE"]
    student_id: Optional[str] = None


def _subject_of_request(user: AuthenticatedUser, student_id: Optional[str]) -> str:
    """A student acts on their own data; a verified guardian may act for a linked child."""
    if not student_id or student_id == user.id:
        return user.id
    if user.role == "parent" and privacy.is_linked_guardian(user.id, student_id):
        return student_id
    raise HTTPException(404, "Not found")


@router.post("/consent/request-otp", dependencies=[Depends(limit_ip)])
def consent_request(body: OtpRequest, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        return privacy.request_otp(user.id, body.guardian_contact, body.purpose)
    except privacy.ConsentError as exc:
        raise _translate(exc)


@router.post("/consent/verify-otp", dependencies=[Depends(limit_ip)])
def consent_verify(body: OtpVerify, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        return privacy.verify_otp(user.id, body.request_id, body.otp)
    except privacy.ConsentError as exc:
        raise _translate(exc)


@router.get("/consent/status")
def consent_status(user: AuthenticatedUser = Depends(get_current_user)):
    return privacy.consent_status(user.id)


@router.post("/consent/withdraw")
def consent_withdraw(body: Withdraw, user: AuthenticatedUser = Depends(get_current_user)):
    return {"withdrawn": privacy.withdraw(user.id, body.purpose)}


@router.get("/privacy/export", dependencies=[Depends(limit_ip)])
def privacy_export(format: Literal["json", "pdf"] = "json", student_id: Optional[str] = None,
                   user: AuthenticatedUser = Depends(get_current_user)):
    data = privacy.collect_export(_subject_of_request(user, student_id))
    if format == "pdf":
        return Response(privacy.export_pdf(data), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="learn-genie-data.pdf"'})
    return Response(json.dumps(data, default=str), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="learn-genie-data.json"'})


@router.delete("/privacy/erase", dependencies=[Depends(limit_ip)])
def privacy_erase(body: Erase, user: AuthenticatedUser = Depends(get_current_user)):
    return privacy.request_erasure(_subject_of_request(user, body.student_id), user.id)


@router.post("/privacy/erasure/run")
def privacy_erasure_run(user: AuthenticatedUser = Depends(require_role(["admin", "super_admin"])),
                        _: AuthenticatedUser = Depends(mfa.require_mfa)):
    return {"processed": privacy.run_pending_erasures()}


class MfaCode(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


@router.post("/auth/mfa/enroll", dependencies=[Depends(limit_ip)])
def mfa_enroll(user: AuthenticatedUser = Depends(get_current_user)):
    return mfa.enroll(user.id, user.email)


@router.post("/auth/mfa/verify", dependencies=[Depends(limit_ip)])
def mfa_verify(body: MfaCode, user: AuthenticatedUser = Depends(get_current_user)):
    return mfa.verify(user.id, body.code)


class PkceCheck(BaseModel):
    code_verifier: str = Field(max_length=128)
    code_challenge: str = Field(max_length=128)


@router.post("/auth/pkce/verify", dependencies=[Depends(limit_ip)])
def pkce_verify(body: PkceCheck):
    return {"valid": mfa.verify_pkce(body.code_verifier, body.code_challenge)}


# ---- Quests, guilds and leagues --------------------------------------------

class BossStart(BaseModel):
    concept_ids: list[str] = Field(min_length=2, max_length=5)


class AnswerSheet(BaseModel):
    answers: dict[str, str]


class GuildCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)


class GuildJoin(BaseModel):
    join_code: str = Field(max_length=20)


def _guarded(call, *args):
    try:
        return call(*args)
    except (engine.NotFound, engine.Conflict, PermissionError) as exc:
        raise _translate(exc)


@router.get("/quests/daily")
def quest_daily(user: AuthenticatedUser = Depends(require_learning_consent)):
    return quests.daily_quest(user.id)


@router.get("/quests/recovery")
def quest_recovery(user: AuthenticatedUser = Depends(require_learning_consent)):
    return [q for q in engine.store.select("quests", student_id=user.id, kind="recovery") if q["status"] == "active"]


@router.post("/quests/boss/start")
def boss_start(body: BossStart, user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.start_boss, user.id, body.concept_ids, _class_of(user))


@router.post("/quests/boss/{quest_id}/submit")
def boss_submit(quest_id: str, body: AnswerSheet, user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.submit_boss, user.id, quest_id, body.answers)


@router.get("/shield")
def shield(user: AuthenticatedUser = Depends(require_learning_consent)):
    return quests.weekly_shield(user.id)


@router.post("/guilds")
def guild_create(body: GuildCreate, user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.create_guild, user.id, body.name, _class_of(user))


@router.post("/guilds/join")
def guild_join(body: GuildJoin, user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.join_guild, user.id, body.join_code, _class_of(user))


@router.get("/guilds/quest")
def guild_quest(user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.guild_quest, user.id)


@router.post("/leagues/opt-in")
def league_in(user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.league_opt_in, user.id, context.student_class(user.id))


@router.post("/leagues/opt-out")
def league_out(user: AuthenticatedUser = Depends(get_current_user)):
    quests.league_opt_out(user.id)
    return {"opted_in": False}


@router.get("/leagues/board")
def league_board(user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.league_board, user.id, context.student_class(user.id))


@router.get("/class-goal/{classroom_id}")
def class_goal(classroom_id: str, user: AuthenticatedUser = Depends(require_learning_consent)):
    return _guarded(quests.class_goal, classroom_id, user.id)


# ---- Dashboards ------------------------------------------------------------

class Intention(BaseModel):
    when: str = Field(min_length=2, max_length=120)
    action: str = Field(min_length=2, max_length=120)


class Remediation(BaseModel):
    concept_id: str
    token: Optional[str] = Field(default=None, pattern=r"^E(0[1-9]|1\d|20)$")


class UtmRequest(BaseModel):
    concept_id: str
    campaign: str = Field(min_length=1, max_length=60)


class TrackEvent(BaseModel):
    code: str = Field(max_length=20)
    event: Literal["click", "signup", "diagnostic_completed", "paid"]


require_teacher_mfa = [Depends(require_role(["teacher"])), Depends(mfa.require_mfa)]


@router.get("/dashboard/student")
def dashboard_student(user: AuthenticatedUser = Depends(require_learning_consent)):
    return dashboards.student_dashboard(user.id, _class_of(user))


@router.post("/dashboard/student/intention")
def dashboard_intention(body: Intention, user: AuthenticatedUser = Depends(require_learning_consent)):
    return dashboards.set_intention(user.id, body.when, body.action)


@router.get("/dashboard/parent")
def dashboard_parent(user: AuthenticatedUser = Depends(require_role(["parent"]))):
    return dashboards.parent_dashboard(user.id)


@router.get("/dashboard/teacher", dependencies=require_teacher_mfa)
def dashboard_teacher(user: AuthenticatedUser = Depends(get_current_user)):
    return dashboards.teacher_dashboard(user.id)


@router.get("/dashboard/teacher/{classroom_id}/heatmap", dependencies=require_teacher_mfa)
def teacher_heatmap(classroom_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    return _guarded(dashboards.heatmap, user.id, classroom_id)


@router.post("/dashboard/teacher/{classroom_id}/assign", dependencies=require_teacher_mfa)
def teacher_assign(classroom_id: str, body: Remediation, user: AuthenticatedUser = Depends(get_current_user)):
    return _guarded(dashboards.assign_remediation, user.id, classroom_id, body.concept_id, body.token)


@router.get("/dashboard/teacher/{classroom_id}/export.csv", dependencies=require_teacher_mfa)
def teacher_csv(classroom_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    return PlainTextResponse(_guarded(dashboards.sis_csv, user.id, classroom_id), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="class-export.csv"'})


@router.post("/creator/links")
def creator_link(body: UtmRequest, origin: Optional[str] = Header(default=None),
                 user: AuthenticatedUser = Depends(require_role(["content_creator"]))):
    from app.core.config import settings

    allowed = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip() and o.strip() != "*"]
    base = origin if origin in allowed else (allowed[0] if allowed else "https://learnbygenie.com")
    return _guarded(dashboards.create_utm_link, user.id, body.concept_id, body.campaign, base)


@router.get("/dashboard/creator")
def dashboard_creator(user: AuthenticatedUser = Depends(require_role(["content_creator"]))):
    return dashboards.creator_analytics(user.id)


@router.post("/creator/track", dependencies=[Depends(limit_ip)])
def creator_track(body: TrackEvent):
    return {"recorded": dashboards.track_event(body.code, body.event)}
