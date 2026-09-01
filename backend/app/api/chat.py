import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.chat import ChatRequest, ChatResponse, PipelineRequest
from app.agents.pipeline import handle_student_message, PipelineOutput
from app.services.rag_service import answer_question
from app.core.dependencies import get_current_user
from app.db.supabase_client import supabase
from app.core.plan_guards import check_daily_question_limit, require_pro
router = APIRouter()

@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest, current_user=Depends(check_daily_question_limit)):
    session_id = getattr(request, 'session_id', None)
    user_id = str(current_user.id)
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
        
        # Save to DB if supabase is connected
        if supabase:
            try:
                # If no session, create one
                if not session_id:
                    session_res = supabase.table("chat_sessions").insert({
                        "user_id": user_id,
                        "title": request.question[:50] + ("..." if len(request.question) > 50 else ""),
                        "pdf_id": request.pdf_id
                    }).execute()
                    session_id = session_res.data[0]['id'] if session_res.data else None

                if session_id:
                    # Insert user message
                    supabase.table("chat_messages").insert({
                        "session_id": session_id,
                        "role": "user",
                        "content": request.question
                    }).execute()
                    
                    # Insert assistant message
                    supabase.table("chat_messages").insert({
                        "session_id": session_id,
                        "role": "assistant",
                        "content": result['answer'],
                        "sources": result.get('sources', [])
                    }).execute()
                    
                    result['session_id'] = session_id
            except Exception as e:
                print(f"Failed to save chat history: {e}")
                
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
        
        session_id = getattr(request, 'session_id', None)
        user_id = str(current_user.id)
        if supabase:
            try:
                if not session_id:
                    session_res = supabase.table("chat_sessions").insert({
                        "user_id": user_id,
                        "title": request.message[:50] + ("..." if len(request.message) > 50 else ""),
                        "pdf_id": request.pdf_id
                    }).execute()
                    session_id = session_res.data[0]['id'] if session_res.data else None

                if session_id:
                    supabase.table("chat_messages").insert({
                        "session_id": session_id,
                        "role": "user",
                        "content": request.message
                    }).execute()
                    
                    # Try to extract the string content depending on response type
                    assistant_content = ""
                    if result.response_type == 'direct_message':
                        assistant_content = result.content
                    elif result.response_type == 'tutor_turn' and result.tutor_data:
                        assistant_content = result.tutor_data.message
                        
                    if assistant_content:
                        supabase.table("chat_messages").insert({
                            "session_id": session_id,
                            "role": "assistant",
                            "content": assistant_content
                        }).execute()
                    
                    result.session_id = session_id
            except Exception as e:
                print(f"Failed to save v2 chat history: {e}")
                
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

@router.get("/")
async def list_chats(current_user=Depends(get_current_user)):
    if not supabase:
        return {"sessions": []}
    res = supabase.table("chat_sessions").select("id, title, pdf_id, created_at").eq("user_id", str(current_user.id)).order("created_at", desc=True).execute()
    return {"sessions": res.data or []}

@router.get("/{session_id}")
async def get_chat(session_id: str, current_user=Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=404, detail="DB not connected")
        
    # Verify ownership
    session_res = supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", str(current_user.id)).maybe_single().execute()
    if not session_res or not session_res.data:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    # Get messages
    msgs_res = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
    
    return {
        "session": session_res.data,
        "messages": msgs_res.data or []
    }

