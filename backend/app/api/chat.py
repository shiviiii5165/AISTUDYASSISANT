from fastapi import APIRouter, Depends
from app.models.chat import ChatRequest, ChatResponse
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
    except Exception as e:
        import traceback
        print(f"FULL ERROR: {traceback.format_exc()}")  # log server-side only
        return ChatResponse(
            answer="I had trouble generating a response just now. Please try asking again.",
            sources=[],
            model="error"
        )
