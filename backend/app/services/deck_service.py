import json
import asyncio
from typing import Dict, Any, List
from app.db.supabase_client import supabase
from app.services.rag_service import get_groq_client
from app.services.ppt_renderer import generate_pptx_bytes

# Prompt constants
STAGE_1_OUTLINE_PROMPT = """
You are an expert curriculum designer. Given a topic, produce a complete slide-deck outline
that a university/school teacher would consider thorough — the kind of outline that would NOT
be flagged as "missing something" by a subject expert.

Return strict JSON:
{
  "deck_title": "...",
  "sections": [
    { "id": "learning_objectives", "title": "...", "type": "objectives" },
    { "id": "concept_1", "title": "...", "type": "concept" },
    { "id": "syntax", "title": "...", "type": "code_anatomy" },
    { "id": "example", "title": "...", "type": "worked_example" },
    { "id": "comparison", "title": "...", "type": "comparison_table" },
    { "id": "misconceptions", "title": "...", "type": "myth_fact" },
    { "id": "recap", "title": "...", "type": "recap" },
    { "id": "practice", "title": "...", "type": "questions" }
  ]
}
Aim for 10-16 sections for "full" depth, 6-8 for "quick" depth. Adapt section TYPES to the topic
(a history topic needs a timeline type, not code_anatomy — invent types as needed but keep them
generic/reusable).
No LaTeX. Plain text only. Output JSON only, nothing else.
"""

STAGE_2_AUDIT_PROMPT = """
You are a strict external examiner reviewing this slide outline for the topic "{topic}"
at {audience} level. List any standard subtopics a syllabus would expect that are MISSING.
Return strict JSON: { "missing_subtopics": ["...", "..."], "notes": "..." }
If nothing is missing, return an empty array.
Output JSON only, nothing else.
"""

STAGE_3_EXPANSION_PROMPT = """
For each section below, write presentation-ready content as strict JSON:
{
  "sections": [
    {
      "id": "...",
      "title": "...",
      "body_bullets": ["short punchy bullet", "..."],
      "example": "a concrete worked example or analogy in plain language, 1-3 sentences",
      "speaker_note": "1-2 sentences a teacher could read aloud",
      "visual_hint": "generated_image",
      "image_prompt": "A clean, minimal illustration of [subject], flat educational diagram style, soft color palette, no text overlays"
    }
  ]
}
RULES:
1. "body_bullets" must be 3-5 max, <18 words each.
2. "visual_hint" can be "generated_image" or "diagram".
3. If "generated_image", ALWAYS provide an "image_prompt" for a clean illustration/diagram (never photorealistic for history/events).
4. No LaTeX or MathJax. Plain text math only.
5. Simple language. Real examples over abstract description. No filler.
Output JSON only, nothing else.
"""

STAGE_4_SYNTHESIS_PROMPT = """
Review this full deck JSON for consistency. 
Fix tone consistency, remove duplicate points across sections, ensure intro promised objectives are covered.
Output the final cleaned JSON strictly matching the input format.
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

async def generate_deck(topic: str, depth: str, audience: str, user_id: str, deck_id: str):
    """Orchestrates the 4-stage generation pipeline and uploads the result."""
    try:
        # Check cache first
        cache_res = supabase.table("deck_cache").select("*").eq("topic", topic).eq("depth", depth).eq("audience", audience).execute()
        
        if cache_res.data:
            final_deck_json = cache_res.data[0]["deck_json"]
        else:
            client = get_groq_client()
            
            # STAGE 1: Outline
            sys_msg = STAGE_1_OUTLINE_PROMPT
            user_msg = f"Topic: {topic}\nDepth: {depth}\nAudience: {audience}"
            
            completion = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.3
            )
            outline_raw = extract_json(completion.choices[0].message.content)
            outline_data = json.loads(outline_raw)
            
            # STAGE 2: Audit
            audit_sys = STAGE_2_AUDIT_PROMPT.format(topic=topic, audience=audience)
            audit_comp = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": audit_sys},
                    {"role": "user", "content": json.dumps(outline_data)}
                ],
                temperature=0.2
            )
            audit_raw = extract_json(audit_comp.choices[0].message.content)
            audit_data = json.loads(audit_raw)
            
            # Inject missing subtopics
            missing = audit_data.get("missing_subtopics", [])
            for i, ms in enumerate(missing):
                outline_data["sections"].append({
                    "id": f"added_{i}", "title": ms, "type": "concept"
                })
                
            # STAGE 3: Expansion (Batched)
            sections = outline_data["sections"]
            batch_size = 4
            expanded_sections = []
            
            for i in range(0, len(sections), batch_size):
                batch = sections[i:i+batch_size]
                
                exp_comp = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": STAGE_3_EXPANSION_PROMPT},
                        {"role": "user", "content": json.dumps({"sections": batch})}
                    ],
                    temperature=0.4
                )
                exp_raw = extract_json(exp_comp.choices[0].message.content)
                exp_data = json.loads(exp_raw)
                expanded_sections.extend(exp_data.get("sections", []))
                
            outline_data["sections"] = expanded_sections
            
            # STAGE 4: Synthesis
            synth_comp = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": STAGE_4_SYNTHESIS_PROMPT},
                    {"role": "user", "content": json.dumps(outline_data)}
                ],
                temperature=0.3
            )
            synth_raw = extract_json(synth_comp.choices[0].message.content)
            final_deck_json = json.loads(synth_raw)
            
            # Save to Cache
            try:
                supabase.table("deck_cache").insert({
                    "topic": topic, "depth": depth, "audience": audience, "deck_json": final_deck_json
                }).execute()
            except Exception as e:
                print("Cache insert failed", e)

        # 5. Render PPTX
        pptx_bytes = await generate_pptx_bytes(final_deck_json)
        
        # 6. Upload to Supabase Storage
        file_path = f"{user_id}/{deck_id}.pptx"
        res = supabase.storage.from_("topic-decks").upload(
            file_path, 
            pptx_bytes,
            {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
        )
        
        # 7. Update topic_decks status
        slide_count = len(final_deck_json.get("sections", [])) + 2 # Title + Closing
        supabase.table("topic_decks").update({
            "status": "ready",
            "storage_path": file_path,
            "slide_count": slide_count
        }).eq("id", deck_id).execute()

    except Exception as e:
        print(f"Deck generation failed: {str(e)}")
        supabase.table("topic_decks").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", deck_id).execute()
