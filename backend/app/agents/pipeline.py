from app.core.logging import logger
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import traceback

from app.agents.orchestrator import classify_and_route, OrchestratorOutput
from app.agents.librarian import retrieve_context, LibrarianOutput
from app.agents.tutor import tutor_turn, TutorTurn
from app.agents.content_creator import create_content, ContentRequest, ContentType, ContentCreatorOutput


class PipelineOutput(BaseModel):
    response_type: str  # "tutor_turn" | "content" | "direct_message"
    message: Optional[str] = None
    tutor_data: Optional[TutorTurn] = None
    content_data: Optional[ContentCreatorOutput] = None
    intent: str


async def handle_student_message(
    user_id: str,
    message: str,
    pdf_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> PipelineOutput:
    """
    Main orchestration pipeline that connects Orchestrator -> Librarian -> Tutor/Content Creator.
    """
    history = conversation_history or []

    # 1. Orchestrator always called first
    try:
        orch_out: OrchestratorOutput = await classify_and_route(message, history)
    except Exception as e:
        logger.error(f"[Pipeline] Orchestrator exception: {e}")
        return PipelineOutput(
            response_type="direct_message",
            message="Sorry, I'm having trouble understanding right now. Let's try that again.",
            intent="error"
        )

    # 2. Branch based on intent
    intent = orch_out.intent

    if intent == "doubt":
        try:
            # Optionally ground with librarian if topic exists
            librarian_ctx = None
            if orch_out.topic:
                try:
                    librarian_ctx = await retrieve_context(topic=orch_out.topic, user_id=user_id)
                except Exception as lib_e:
                    logger.error(f"[Pipeline] Librarian exception during doubt flow: {lib_e}")
                    # Librarian failure shouldn't crash the tutor. Pass empty context.
                    librarian_ctx = LibrarianOutput(context=[], related_context=[], sufficient=False, used_web_fallback=False)
            else:
                librarian_ctx = LibrarianOutput(context=[], related_context=[], sufficient=False, used_web_fallback=False)
                
            t_out: TutorTurn = await tutor_turn(
                topic=orch_out.topic or "general",
                librarian_context=librarian_ctx,
                conversation_history=history,
                student_message=message
            )
            return PipelineOutput(
                response_type="tutor_turn",
                tutor_data=t_out,
                intent=intent
            )
        except Exception as e:
            logger.error(f"[Pipeline] Tutor exception: {e}")
            return PipelineOutput(
                response_type="direct_message",
                message="I encountered an issue while trying to help you. Could you rephrase your question?",
                intent=intent
            )

    elif intent == "content_request":
        subtype = orch_out.content_subtype
        if not subtype or subtype == "unknown":
            return PipelineOutput(
                response_type="direct_message",
                message="I can generate flashcards, a presentation, or a video for you. Which format would you prefer?",
                intent=intent
            )
        
        try:
            librarian_ctx = None
            if orch_out.topic:
                try:
                    librarian_ctx = await retrieve_context(topic=orch_out.topic, user_id=user_id)
                except Exception as lib_e:
                    logger.error(f"[Pipeline] Librarian exception during content flow: {lib_e}")
                    librarian_ctx = None
            
            # Map Orchestrator subtype string to Enum
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
                intent=intent
            )
        except Exception as e:
            logger.error(f"[Pipeline] Content Creator exception: {e}\n{traceback.format_exc()}")
            return PipelineOutput(
                response_type="direct_message",
                message="I ran into a problem while trying to generate that content. Please try again later.",
                intent=intent
            )

    elif intent == "progress_check":
        return PipelineOutput(
            response_type="direct_message",
            message="Progress tracking is coming soon!",
            intent=intent
        )

    elif intent in ("general_chat", "clarify"):
        return PipelineOutput(
            response_type="direct_message",
            message=orch_out.direct_reply or "Could you clarify?",
            intent=intent
        )

    elif intent == "document_summary":
        if not pdf_id:
            return PipelineOutput(
                response_type="direct_message",
                message="I don't see a document selected. Please open a PDF first so I can summarize it for you.",
                intent=intent
            )
            
        try:
            from app.services.rag_service import answer_question
            # Re-use V1's RAG pipeline directly
            result = await answer_question(
                pdf_id=pdf_id,
                user_id=user_id,
                question=message,
                mode="Full Chapter Crux",  # Standard high-level summary mode
                chat_history=history
            )
            return PipelineOutput(
                response_type="direct_message",
                message=result.get("answer", "Here is a summary of the document."),
                intent=intent
            )
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[Pipeline] document_summary exception: {e}")
            if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
                return PipelineOutput(
                    response_type="direct_message",
                    message="The AI is currently overloaded. Please try again in a few moments.",
                    intent=intent
                )
            return PipelineOutput(
                response_type="direct_message",
                message="I had trouble reading the document for a summary. Please try again.",
                intent=intent
            )

    else:
        # Fallback for completely unknown intent string
        return PipelineOutput(
            response_type="direct_message",
            message="I'm not sure how to handle that right now.",
            intent=intent
        )
