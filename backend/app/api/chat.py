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
    except Exception as e:
        import traceback
        print(f"FULL ERROR: {traceback.format_exc()}")  # log server-side only
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
            conversation_history=request.history
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"FULL ERROR in /v2/ask: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The study assistant is currently unavailable. Please try again later."
        )

