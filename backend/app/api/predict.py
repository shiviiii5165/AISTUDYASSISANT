"""
Exam question predictor endpoint.
Uses Gemini (gemini-3.6-flash) for prediction.
Uses vector_service.get_all_chunks_text() for context retrieval.
"""

import json
import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro
from app.services.vector_service import get_all_chunks_text
from app.services.llm_service import call_gemini

router = APIRouter()


class PredictRequest(BaseModel):
    pdfId: str
    examType: str = "CBSE"


PREDICT_SYSTEM_PROMPT = """You are an experienced exam paper setter for Indian school and competitive exams. Analyze the provided chapter content and predict the most likely exam questions.

Return ONLY a valid JSON object inside a ```json block. No other text.

{
  "predictions": [
    {
      "id": "<random 6-char id>",
      "question": "<predicted exam question>",
      "topic": "<specific topic slug in kebab-case>",
      "likelihood": "High",
      "questionType": "MCQ",
      "reason": "<1 sentence why this is likely to appear>"
    }
  ],
  "examType": "CBSE",
  "chapterSummary": "<one line summary of what this chapter is about>"
}

likelihood must be exactly one of: High, Medium, Low
questionType must be exactly one of: MCQ, Short Answer, Long Answer

Prediction rules:
- High = definitions, laws, fundamental concepts that appear in almost every exam
- Medium = application-based questions, numerical problems
- Low = edge cases, very specific details

For CBSE: predict 5 MCQs, 4 Short Answer, 3 Long Answer
For JEE or NEET: predict 8 MCQs, 4 numerical, 3 conceptual
For UPSC: predict 3 essay questions, 5 short answer"""


@router.post("/exam-questions")
async def predict_exam_questions(
    request: PredictRequest,
    current_user=Depends(require_pro),
):
    """Predict likely exam questions from document content using Groq."""

    # 1. Fetch all chunks for the document
    try:
        chunks = get_all_chunks_text(request.pdfId, limit=30)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not fetch document content: {str(e)}",
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content found for this document. Make sure it has been processed.",
        )

    # 2. Join chunks into context
    context = "\n\n---\n\n".join(chunks)

    # 3. Call Groq for prediction
    user_message = (
        f"Exam type: {request.examType}\n\n"
        f"Chapter content:\n{context}\n\n"
        f"Generate predicted exam questions based on this content for {request.examType} exam."
    )

    try:
        ai_response = await call_gemini(
            messages=[
                {"role": "system", "content": PREDICT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model="gemini-3.6-flash",
            max_tokens=4000,
            temperature=0.3,
        )
        print(f"Gemini prediction response length: {len(ai_response)}")

    except Exception as e:
        print(f"Gemini API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI prediction failed: {str(e)}",
        )

    # 4. Parse JSON from response
    try:
        # Extract JSON block from ```json ... ```
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", ai_response)
        if json_match:
            parsed = json.loads(json_match.group(1))
        else:
            # Try parsing the entire response as JSON
            parsed = json.loads(ai_response)

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {ai_response[:500]}")
        # Return the raw response wrapped in a fallback structure
        return {
            "predictions": [],
            "examType": request.examType,
            "chapterSummary": "Could not parse predictions. Raw response returned.",
            "rawResponse": ai_response,
        }
