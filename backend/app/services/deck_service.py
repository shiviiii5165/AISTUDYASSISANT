import json
import asyncio
from typing import Dict, Any, List
from app.db.supabase_client import supabase
from app.services.llm_service import call_gemini, safe_json_loads
from app.services.ppt_renderer import generate_pptx_bytes

# ──────────────────────────────────────────────────────────────────────────────
# PROMPTS — Tuned for deep, world-class content
# ──────────────────────────────────────────────────────────────────────────────

STAGE_1_OUTLINE_PROMPT = """
You are an expert curriculum designer and subject matter expert. Given a topic, produce a comprehensive, 
university-grade slide-deck outline that covers the subject with real depth — not surface-level.

Return strict JSON:
{
  "deck_title": "...",
  "sections": [
    { "id": "learning_objectives", "title": "...", "type": "objectives" },
    { "id": "concept_1", "title": "...", "type": "concept" },
    ...
  ]
}

REQUIREMENTS:
1. Aim for 10-14 sections for "full" depth, 6-8 for "quick" depth.
2. Each section must have a unique "id" and descriptive "title".
3. Adapt section TYPES to the topic (history needs timelines, CS needs code anatomy, science needs experimental design).
4. Include: Introduction/Overview, Core Concepts (2-4 sections), Real-World Applications, 
   Common Misconceptions, Case Study or Worked Example, Comparison/Contrast, Summary/Recap, Practice Questions.
5. Sections should flow logically — build on each other like a real lecture.
6. No LaTeX. Plain text only.

Output JSON only, nothing else.
"""

STAGE_2_EXPANSION_PROMPT = """
You are a world-class lecturer writing presentation slides. For each section below, 
create rich, educational, presentation-ready content. Think like a professor preparing 
slides for an engaged audience — every bullet should teach something concrete.

Return strict JSON:
{
  "deck_title": "...",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3", "takeaway 4", "takeaway 5"],
  "sections": [
    {
      "id": "...",
      "title": "...",
      "body_bullets": ["concrete, insightful bullet point", "..."],
      "example": "A vivid, real-world example or analogy that makes the concept click, 2-3 sentences",
      "speaker_note": "3-4 sentences of teaching context a presenter would say aloud. Add depth, history, or nuance NOT in the bullets.",
      "visual_hint": "generated_image",
      "image_prompt": "A clean, minimal flat-design illustration of [specific visual], educational diagram style, soft color palette, no text overlays, white background"
    }
  ]
}

CONTENT RULES:
1. "body_bullets": 4-5 bullets, each 10-20 words. Must contain SPECIFIC facts, numbers, names, or concrete details — NOT vague generalities.
2. "example": Must be a REAL example (real company, real event, real formula, real code snippet in plain text). No made-up examples.
3. "speaker_note": Add historical context, why this matters, common student questions, or connections to other topics. 
4. "visual_hint": Use "generated_image" for most sections. Use "diagram" for simple flowcharts.
5. "image_prompt": Be VERY specific — describe exactly what the illustration should show. Mention style: flat, minimal, educational.
6. "key_takeaways": 5 impactful one-liners summarizing the entire deck. These appear on the closing slide.
7. No LaTeX. No markdown. Plain text only.

Output JSON only, nothing else.
"""


async def _call_gemini_with_json(messages: list, temperature: float = 0.3, max_tokens: int = 8192, stage_name: str = "unknown") -> dict:
    """Call Gemini and parse the response as JSON with repair. Retries once on parse failure."""
    for attempt in range(2):
        raw_response = await call_gemini(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=1
        )
        try:
            return safe_json_loads(raw_response)
        except Exception as e:
            if attempt == 0:
                print(f"[{stage_name}] JSON parse failed (attempt 1), retrying: {e}")
                await asyncio.sleep(1)
                continue
            raise Exception(f"[{stage_name}] Failed to parse JSON after 2 attempts: {e}\nRaw: {raw_response[:300]}")


async def generate_deck(topic: str, depth: str, audience: str, user_id: str, deck_id: str):
    """
    Optimized 2-stage generation pipeline (reduced from 4 stages for speed on Vercel):
    Stage 1: Generate outline  
    Stage 2: Expand all sections with deep content (batched for reliability)
    Then: Render PPTX with AI images
    """
    try:
        # Check cache first
        cache_res = supabase.table("deck_cache").select("*").eq("topic", topic).eq("depth", depth).eq("audience", audience).execute()
        
        if cache_res.data:
            final_deck_json = cache_res.data[0]["deck_json"]
        else:
            # STAGE 1: Generate comprehensive outline
            outline_data = await _call_gemini_with_json(
                messages=[
                    {"role": "system", "content": STAGE_1_OUTLINE_PROMPT},
                    {"role": "user", "content": f"Topic: {topic}\nDepth: {depth}\nAudience: {audience}"}
                ],
                temperature=0.3,
                max_tokens=4096,
                stage_name="Stage 1: Outline"
            )
            
            # STAGE 2: Expand sections with deep content (batched for reliability)
            sections = outline_data.get("sections", [])
            batch_size = 5  # Process 5 at a time for better context
            expanded_sections = []
            key_takeaways = []
            deck_title = outline_data.get("deck_title", topic)
            
            for i in range(0, len(sections), batch_size):
                batch = sections[i:i+batch_size]
                
                exp_data = await _call_gemini_with_json(
                    messages=[
                        {"role": "system", "content": STAGE_2_EXPANSION_PROMPT},
                        {"role": "user", "content": f"Topic: {topic}\nAudience: {audience}\n\nSections to expand:\n{json.dumps({'deck_title': deck_title, 'sections': batch})}"}
                    ],
                    temperature=0.4,
                    max_tokens=8192,
                    stage_name=f"Stage 2: Expansion (batch {i//batch_size + 1})"
                )
                expanded_sections.extend(exp_data.get("sections", []))
                
                # Grab key_takeaways from the first batch response
                if not key_takeaways and exp_data.get("key_takeaways"):
                    key_takeaways = exp_data["key_takeaways"]
                if not deck_title or deck_title == topic:
                    deck_title = exp_data.get("deck_title", deck_title)
            
            final_deck_json = {
                "deck_title": deck_title,
                "key_takeaways": key_takeaways,
                "sections": expanded_sections
            }
            
            # Save to Cache
            try:
                supabase.table("deck_cache").insert({
                    "topic": topic, "depth": depth, "audience": audience, "deck_json": final_deck_json
                }).execute()
            except Exception as e:
                print("Cache insert failed", e)

        # 3. Render PPTX (includes AI image generation)
        pptx_bytes = await generate_pptx_bytes(final_deck_json, audience=audience)
        
        # 4. Upload to Supabase Storage
        file_path = f"{user_id}/{deck_id}.pptx"
        try:
            res = supabase.storage.from_("topic-decks").upload(
                file_path, 
                pptx_bytes,
                {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
            )
        except Exception as storage_err:
            raise Exception(f"Storage upload failed: {storage_err}")
        
        # 5. Update topic_decks status
        slide_count = len(final_deck_json.get("sections", [])) + 2  # Title + Closing
        supabase.table("topic_decks").update({
            "status": "ready",
            "storage_path": file_path,
            "slide_count": slide_count
        }).eq("id", deck_id).execute()

    except Exception as e:
        print(f"Deck generation failed: {str(e)}")
        supabase.table("topic_decks").update({
            "status": "failed",
            "error_message": str(e)[:500]
        }).eq("id", deck_id).execute()
