import json
import asyncio
from typing import Dict, Any, List
from app.db.supabase_client import supabase
from app.services.llm_service import call_gemini

# ──────────────────────────────────────────────
# Prompts for the 3-stage lesson generation
# ──────────────────────────────────────────────

LESSON_PLAN_PROMPT = """
You are an expert educational content creator. Given a topic, student level, language preference, 
and approximate duration, produce a complete structured lesson plan that an AI teacher would follow 
to create an educational video lesson.

Return strict JSON:
{
  "lesson_title": "...",
  "language": "hindi" | "english" | "hinglish",
  "estimated_duration_seconds": 300,
  "learning_objectives": ["...", "..."],
  "prerequisites": ["...", "..."],
  "scenes": [
    {
      "id": "scene_01",
      "type": "intro" | "concept" | "definition" | "formula" | "diagram" | "example" | "comparison" | "quiz" | "summary" | "outro",
      "title": "...",
      "duration_seconds": 30,
      "teacher_speech": "Full script the teacher would say (in the requested language/style)",
      "visual_type": "slide" | "diagram" | "formula" | "handwriting" | "comparison_table" | "flowchart" | "bullet_points",
      "visual_content": {
        "title": "...",
        "bullets": ["...", "..."],
        "formula": "optional formula text",
        "diagram_description": "optional description"
      },
      "teacher_emotion": "neutral" | "excited" | "serious" | "curious" | "encouraging"
    }
  ],
  "key_takeaways": ["...", "..."],
  "summary_notes": "A 200-300 word summary of the entire lesson in paragraph form",
  "revision_notes": ["Short bullet point 1", "Short bullet point 2", "..."],
  "quiz": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "..."
    }
  ],
  "important_questions": ["...", "..."],
  "flashcards": [
    {"front": "...", "back": "..."}
  ]
}

RULES:
1. Create 8-15 scenes for a full lesson, 4-6 for a quick one.
2. Teacher speech should be natural, conversational, and in the requested language style.
3. For "hinglish", mix Hindi and English naturally as a real Indian teacher would.
4. Include at least 3 quiz questions.
5. Include at least 5 flashcards.
6. Include at least 5 important questions.
7. Make the lesson engaging with real-world examples and analogies.
8. No LaTeX. Plain text only for formulas. 
9. Output JSON only, nothing else.
"""

LESSON_AUDIT_PROMPT = """
You are a strict curriculum reviewer. Review this lesson plan for the topic "{topic}" 
at {level} level. Check for:
1. Missing important subtopics
2. Incorrect or incomplete information
3. Poor flow between scenes
4. Insufficient examples

Return strict JSON:
{{
  "missing_topics": ["...", "..."],
  "improvements": ["...", "..."],
  "is_acceptable": true/false
}}
Output JSON only, nothing else.
"""

LESSON_ENHANCE_PROMPT = """
You are enhancing an educational lesson plan. Given the original lesson and audit feedback,
produce the final enhanced version.

Integrate any missing topics, fix issues, and ensure the lesson flows perfectly.
Keep the EXACT same JSON structure as the input but with improvements applied.
Output JSON only, nothing else.
"""

def extract_json(text: str) -> str:
    """Extract JSON from markdown code blocks if present."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def generate_lesson(topic: str, level: str, duration: str, language: str, user_id: str, lesson_id: str):
    """Orchestrates the lesson generation pipeline."""
    try:
        # STAGE 1: Generate lesson plan
        duration_map = {"5": 300, "8": 480, "10": 600, "15": 900}
        target_duration = duration_map.get(duration, 480)
        
        user_msg = f"Topic: {topic}\nLevel: {level}\nLanguage: {language}\nApproximate Duration: {target_duration} seconds ({duration} minutes)"
        
        plan_response = await call_gemini(
            messages=[
                {"role": "system", "content": LESSON_PLAN_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.4,
            max_tokens=8000
        )
        plan_raw = extract_json(plan_response)
        lesson_data = json.loads(plan_raw)
        
        # Update status to auditing
        supabase.table("video_lessons").update({
            "status": "auditing"
        }).eq("id", lesson_id).execute()
        
        # STAGE 2: Audit
        audit_sys = LESSON_AUDIT_PROMPT.format(topic=topic, level=level)
        audit_response = await call_gemini(
            messages=[
                {"role": "system", "content": audit_sys},
                {"role": "user", "content": json.dumps(lesson_data)}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        audit_raw = extract_json(audit_response)
        audit_data = json.loads(audit_raw)
        
        # STAGE 3: Enhance if needed
        if not audit_data.get("is_acceptable", True) or audit_data.get("missing_topics", []):
            supabase.table("video_lessons").update({
                "status": "enhancing"
            }).eq("id", lesson_id).execute()
            
            enhance_response = await call_gemini(
                messages=[
                    {"role": "system", "content": LESSON_ENHANCE_PROMPT},
                    {"role": "user", "content": json.dumps({
                        "original_lesson": lesson_data,
                        "audit_feedback": audit_data
                    })}
                ],
                temperature=0.3,
                max_tokens=8000
            )
            enhance_raw = extract_json(enhance_response)
            lesson_data = json.loads(enhance_raw)
        
        # Calculate scene count and total duration
        scene_count = len(lesson_data.get("scenes", []))
        total_duration = sum(s.get("duration_seconds", 30) for s in lesson_data.get("scenes", []))
        
        # Save completed lesson
        supabase.table("video_lessons").update({
            "status": "ready",
            "lesson_json": lesson_data,
            "scene_count": scene_count,
            "total_duration_seconds": total_duration
        }).eq("id", lesson_id).execute()

    except Exception as e:
        print(f"Lesson generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        supabase.table("video_lessons").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", lesson_id).execute()
