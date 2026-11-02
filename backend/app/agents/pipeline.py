from app.core.logging import logger
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import traceback

from app.agents.orchestrator import classify_and_route, OrchestratorOutput
from app.agents.librarian import retrieve_context, LibrarianOutput
from app.agents.tutor import tutor_turn, TutorTurn
from app.agents.content_creator import create_content, ContentRequest, ContentType, ContentCreatorOutput
from app.services.tutor.schemas import TutorTurnResponse, TutorMode, PedagogicalState, HintLevel
from app.services.tutor.service import PersonalizedTutorService


class PipelineOutput(BaseModel):
    response_type: str  # "tutor_turn" | "content" | "direct_message"
    message: Optional[str] = None
    tutor_data: Optional[TutorTurn] = None
    tutor_response: Optional[TutorTurnResponse] = None
    content_data: Optional[ContentCreatorOutput] = None
    intent: str
    session_id: Optional[str] = None


async def handle_student_message(
    user_id: str,
    message: str,
    pdf_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    mode: Optional[str] = None,
    session_id: Optional[str] = None,
    user_action: Optional[str] = None,
) -> PipelineOutput:
    """
    Main orchestration pipeline that connects Orchestrator -> Librarian -> Tutor/Content Creator.
    Incorporates Feature 4 Socratic Tutor V2 and Quick Ask modes (§2, §3, §4).
    """
    history = conversation_history or []

    # 1. Orchestrator always called first (with optional explicit mode override §3)
    try:
        orch_out: OrchestratorOutput = await classify_and_route(
            message,
            history,
            explicit_mode=mode
        )
    except Exception as e:
        logger.error(f"[Pipeline] Orchestrator exception: {e}")
        return PipelineOutput(
            response_type="direct_message",
            message="Sorry, I'm having trouble understanding right now. Let's try that again.",
            intent="error",
            session_id=session_id
        )

    # 2. Branch based on intent
    intent = orch_out.intent

    # Educational Teaching / Doubt / Quick QA intents
    if intent in ("doubt", "quick_qa", "concept_learning", "document_learning", "practice_request"):
        try:
            # Ground with librarian if topic exists or pdf_id provided
            librarian_ctx = None
            retrieved_material = []
            search_query = orch_out.topic or message

            if search_query:
                try:
                    librarian_ctx = await retrieve_context(topic=search_query, user_id=user_id)
                    if librarian_ctx and librarian_ctx.context:
                        retrieved_material = [
                            {
                                "source_document": c.source_document,
                                "page_or_location": c.page_or_location,
                                "text": c.text,
                                "source": c.source
                            }
                            for c in librarian_ctx.context
                        ]
                except Exception as lib_e:
                    logger.error(f"[Pipeline] Librarian exception during doubt flow: {lib_e}")
                    librarian_ctx = LibrarianOutput(context=[], related_context=[], sufficient=False, used_web_fallback=False)
            else:
                librarian_ctx = LibrarianOutput(context=[], related_context=[], sufficient=False, used_web_fallback=False)

            # Determine effective mode (explicit parameter overrides §3)
            eff_mode_str = mode or orch_out.teaching_mode
            eff_mode = TutorMode.QUICK_ASK if eff_mode_str == "QUICK_ASK" else TutorMode.TUTOR

            # Call tutor_turn (preserves mock and contract compatibility with existing tests)
            t_out: TutorTurn = await tutor_turn(
                topic=orch_out.topic or "general",
                librarian_context=librarian_ctx,
                conversation_history=history,
                student_message=message
            )

            # Build enriched tutor response from t_out without redundant second LLM call (§38)
            ped_state = PedagogicalState.WRAP_UP if t_out.is_topic_complete else (
                PedagogicalState.RETEACH if t_out.understanding_level == "struggling" else PedagogicalState.EXPLAIN
            )
            sess_id = session_id or f"sess_{user_id[:8]}"
            tutor_rich_resp = TutorTurnResponse(
                session_id=sess_id,
                message=t_out.message,
                mode=eff_mode,
                pedagogical_state=ped_state,
                active_check=None,
                hint_level=HintLevel.NONE,
                citations=[
                    {"source": c.source_document, "page": c.page_or_location}
                    for c in (librarian_ctx.context if librarian_ctx else [])
                ]
            )

            return PipelineOutput(
                response_type="tutor_turn",
                message=t_out.message,
                tutor_data=t_out,
                tutor_response=tutor_rich_resp,
                intent=intent,
                session_id=sess_id
            )
        except Exception as e:
            logger.error(f"[Pipeline] Tutor exception: {e}\n{traceback.format_exc()}")
            return PipelineOutput(
                response_type="direct_message",
                message="I encountered an issue while trying to help you. Could you rephrase your question?",
                intent=intent,
                session_id=session_id
            )

    elif intent in ("content_request", "content_creation"):
        subtype = orch_out.content_subtype
        if not subtype or subtype == "unknown":
            return PipelineOutput(
                response_type="direct_message",
                message="I can generate flashcards, a presentation, or a video for you. Which format would you prefer?",
                intent=intent,
                session_id=session_id
            )

        try:
            librarian_ctx = None
            if orch_out.topic:
                try:
                    librarian_ctx = await retrieve_context(topic=orch_out.topic, user_id=user_id)
                except Exception as lib_e:
                    logger.error(f"[Pipeline] Librarian exception during content flow: {lib_e}")
                    librarian_ctx = None

            content_type_enum = ContentType(subtype)

            req = ContentRequest(
                content_type=content_type_enum,
                topic=orch_out.topic or message,
                librarian_context=librarian_ctx
            )

            c_out: ContentCreatorOutput = await create_content(req)
            return PipelineOutput(
                response_type="content",
                content_data=c_out,
                intent=intent,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"[Pipeline] Content Creator exception: {e}\n{traceback.format_exc()}")
            return PipelineOutput(
                response_type="direct_message",
                message="I ran into a problem while trying to generate that content. Please try again later.",
                intent=intent,
                session_id=session_id
            )

    elif intent == "progress_check":
        return PipelineOutput(
            response_type="direct_message",
            message="Progress tracking is coming soon!",
            intent=intent,
            session_id=session_id
        )

    elif intent in ("general_chat", "clarify", "general_conversation"):
        return PipelineOutput(
            response_type="direct_message",
            message=orch_out.direct_reply or "Could you clarify?",
            intent=intent,
            session_id=session_id
        )

    elif intent == "document_summary":
        if not pdf_id:
            return PipelineOutput(
                response_type="direct_message",
                message="I don't see a document selected. Please open a PDF first so I can summarize it for you.",
                intent=intent,
                session_id=session_id
            )

        try:
            from app.services.rag_service import answer_question
            result = await answer_question(
                pdf_id=pdf_id,
                user_id=user_id,
                question=message,
                mode="Full Chapter Crux",
                chat_history=history
            )
            return PipelineOutput(
                response_type="direct_message",
                message=result.get("answer", "Here is a summary of the document."),
                intent=intent,
                session_id=session_id
            )
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[Pipeline] document_summary exception: {e}")
            if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
                return PipelineOutput(
                    response_type="direct_message",
                    message="The AI is currently overloaded. Please try again in a few moments.",
                    intent=intent,
                    session_id=session_id
                )
            return PipelineOutput(
                response_type="direct_message",
                message="I had trouble reading the document for a summary. Please try again.",
                intent=intent,
                session_id=session_id
            )

    else:
        return PipelineOutput(
            response_type="direct_message",
            message="I'm not sure how to handle that right now.",
            intent=intent,
            session_id=session_id
        )
