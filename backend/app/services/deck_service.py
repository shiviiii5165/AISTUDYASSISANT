import json
import asyncio
from typing import Dict, Any, List
from app.db.supabase_client import supabase
from app.services.llm_service import call_gemini, safe_json_loads
from app.services.ppt_renderer import generate_pptx_bytes

# ──────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ──────────────────────────────────────────────────────────────────────────────

STAGE_1_OUTLINE_PROMPT = """
You are an expert curriculum designer, subject matter expert, AND professional presentation designer.
Given a topic, produce a comprehensive, audience-appropriate slide-deck outline.

CRITICAL: You are designing a PRESENTATION, not a document. Each slide should communicate ONE primary idea clearly.

Return strict JSON:
{
  "deck_title": "A compelling, specific title (NOT just the topic name)",
  "sections": [
    {
      "id": "unique_id",
      "title": "Meaningful, insight-oriented title (avoid generic titles like 'Introduction' or 'Overview')",
      "slide_purpose": "concept|two_column|image_insight|architecture|process_flow|timeline|comparison|kpi_metrics|case_study|quote_insight|summary"
    }
  ]
}

TITLE QUALITY RULES:
- BAD: "Cloud Architecture"
- GOOD: "Modern Cloud Architecture Separates Compute, Storage and Networking"
- BAD: "Introduction"
- GOOD: "Why Cloud Architecture Matters for Every Modern System"

SLIDE PURPOSE GUIDE — pick the purpose that best fits the section's communication goal:
- "concept": Define or explain a single idea with supporting bullets
- "two_column": Side-by-side explanation (text+visual or text+example)
- "image_insight": Visual-led slide with key insight callout
- "architecture": Layered system/component diagram
- "process_flow": Step-by-step numbered workflow
- "timeline": Chronological milestones or phase progression
- "comparison": A vs B, pros vs cons, old vs new
- "kpi_metrics": Key numbers/statistics with context
- "case_study": Real-world example structured as Context → Solution → Outcome
- "quote_insight": A single powerful statement or key takeaway
- "summary": Numbered key takeaways recap

VARIETY IS CRITICAL: Use at least 5 different slide_purpose types across the deck. Do NOT make every slide "concept".

REQUIREMENTS:
1. Aim for 10-14 sections for "full" depth, 6-8 for "quick" depth.
2. Each section must have a unique "id" and descriptive "title".
3. Include: Core Concepts, Real-World Applications, Case Study, Summary.
4. No LaTeX. Plain text only.

Output JSON only, nothing else.
"""


STAGE_2_EXPANSION_PROMPT = """
You are a world-class presentation designer and lecturer. For each section below,
create PRESENTATION-READY content — concise, visual, and impactful.

CRITICAL: Slides are NOT documents. Never write paragraphs. Every bullet must be a concise, scannable statement.

Return strict JSON:
{
  "deck_title": "...",
  "key_takeaways": ["5 impactful one-liner takeaways"],
  "sections": [
    {
      "id": "...",
      "title": "Compelling, insight-oriented title",
      "body_bullets": ["Concise, specific bullet under 80 characters", "..."],
      "example": "A vivid, REAL-WORLD example with specific names, metrics, or mechanisms. 2-3 sentences max.",
      "speaker_note": "4-5 sentences: what the slide means, what to emphasize, explanation of visual, and transition to next slide.",
      "visual_hint": "generated_image",
      "image_prompt": "Professional flat-design educational illustration of [SPECIFIC visual description], clean modern style, white background, no text or labels in image"
    }
  ]
}

CONTENT QUALITY RULES:
1. "body_bullets": 4-5 bullets max. Each bullet must be under 80 characters. Must contain SPECIFIC facts, numbers, or mechanisms. No vague generalities.
2. "example": Must cite a REAL company, study, technology, or event. Include specific metrics when possible.
3. "speaker_note": Include (a) what the slide communicates, (b) what to emphasize verbally, (c) how to explain the visual, (d) transition to next slide.
4. "visual_hint": Use "generated_image" for concept/explanation slides, "diagram" for architecture/process slides.
5. "image_prompt": Be EXTREMELY specific about the visual subject, style, composition, and color mood. Never say "image of topic" — describe WHAT should be illustrated.
6. "key_takeaways": 5 impactful one-liners that a viewer should remember after the presentation.
7. No LaTeX. Plain text only.
8. NEVER write paragraphs in body_bullets. Each bullet is a standalone scannable statement.

Output JSON only, nothing else.
"""


async def _call_gemini_with_json(messages: list, temperature: float = 0.3, max_tokens: int = 8192, stage_name: str = "unknown") -> dict:
    """Call Gemini and parse the response as JSON with repair. Retries once."""
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
                print(f"[{stage_name}] JSON parse failed, retrying: {e}")
                await asyncio.sleep(1)
                continue
            raise Exception(f"[{stage_name}] Failed to parse JSON: {e}")


async def generate_outline_step(topic: str, depth: str, audience: str) -> dict:
    """Step 1: Generate the outline."""
    # Check cache first
    cache_res = supabase.table("deck_cache").select("*").eq("topic", topic).eq("depth", depth).eq("audience", audience).execute()
    if cache_res.data:
        return cache_res.data[0]["deck_json"]
        
    outline_data = await _call_gemini_with_json(
        messages=[
            {"role": "system", "content": STAGE_1_OUTLINE_PROMPT},
            {"role": "user", "content": f"Topic: {topic}\nDepth: {depth}\nAudience: {audience}"}
        ],
        temperature=0.3,
        max_tokens=4096,
        stage_name="Stage 1: Outline"
    )
    return outline_data


async def expand_outline_step(topic: str, audience: str, outline_data: dict) -> dict:
    """Step 2: Expand the outline sections into full slide content."""
    # If the outline is already fully expanded (e.g. from cache), skip
    if outline_data.get("sections") and "body_bullets" in outline_data["sections"][0]:
        return outline_data

    sections = outline_data.get("sections", [])
    batch_size = 5
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
        if not key_takeaways and exp_data.get("key_takeaways"):
            key_takeaways = exp_data["key_takeaways"]
        if not deck_title or deck_title == topic:
            deck_title = exp_data.get("deck_title", deck_title)
            
    return {
        "deck_title": deck_title,
        "key_takeaways": key_takeaways,
        "sections": expanded_sections
    }


async def render_deck_step(deck_id: str, user_id: str, topic: str, depth: str, audience: str, final_deck_json: dict) -> str:
    """Step 3: Render the PPTX, upload to storage, and return the download URL."""
    try:
        # Save to Cache for future fast-loads
        supabase.table("deck_cache").insert({
            "topic": topic, "depth": depth, "audience": audience, "deck_json": final_deck_json
        }).execute()
    except:
        pass
        
    pptx_bytes = await generate_pptx_bytes(final_deck_json, audience=audience)
    
    file_path = f"{user_id}/{deck_id}.pptx"
    try:
        res = supabase.storage.from_("topic-decks").upload(
            file_path, 
            pptx_bytes,
            {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
        )
    except Exception as storage_err:
        raise Exception(f"Storage upload failed: {storage_err}")
    
    slide_count = len(final_deck_json.get("sections", [])) + 2
    supabase.table("topic_decks").update({
        "status": "ready",
        "storage_path": file_path,
        "slide_count": slide_count
    }).eq("id", deck_id).execute()
    
    return file_path
