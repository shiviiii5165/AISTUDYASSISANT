import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.chat import ChatRequest, ChatResponse, PipelineRequest
from app.agents.pipeline import handle_student_message, PipelineOutput
from app.services.rag_service import answer_question
from app.core.dependencies import get_current_user
from app.core.plan_guards import check_daily_question_limit, require_pro
router = APIRouter()

@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest, current_user=Depends(check_daily_question_limit)):
    try:
        try:
            uuid.UUID(request.pdf_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF ID format."
            )

        pro_modes = ["Full Chapter Crux", "No Fact Miss", "Formula Coverage", "Exam Shield Notes"]
        if request.mode in pro_modes:
            require_pro(current_user)
            
        result = await answer_question(
            pdf_id=request.pdf_id,
            user_id=current_user.id,  # Fix: current_user is an object, not a dict
            question=request.question,
            mode=request.mode,
            chat_history=request.history or []
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except PermissionError:
        # PDF not found or not owned by this user (e.g. a stale pdf_id from a chat
        # sent after the document list failed to load). Return a clear 404, not a 500.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That document is unavailable. Please reselect a document and try again."
        )
    except Exception as e:
        import traceback
        err_msg = str(e)
        print(f"FULL ERROR: {traceback.format_exc()}")  # log server-side only
        
        # If this is our explicit LLM/Embedding exhaustion exception, surface as 503
        if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI is currently overloaded. Please try again in a few moments."
            )
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="I had trouble generating a response just now. Please try asking again."
        )


@router.post("/v2/ask", response_model=PipelineOutput)
async def ask_question_v2(request: PipelineRequest, current_user=Depends(get_current_user)):
    """
    V2 chat endpoint that routes through the new multi-agent pipeline (Orchestrator -> Librarian -> Tutor/Content).
    """
    try:
        result = await handle_student_message(
            user_id=current_user.id,
            message=request.message,
            pdf_id=request.pdf_id,
            conversation_history=request.history
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = str(e)
        print(f"FULL ERROR in /v2/ask: {traceback.format_exc()}")
        
        # If this is our explicit LLM/Embedding exhaustion exception, surface as 503
        if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI is currently overloaded. Please try again in a few moments."
            )
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The study assistant is currently unavailable. Please try again later."
        )

