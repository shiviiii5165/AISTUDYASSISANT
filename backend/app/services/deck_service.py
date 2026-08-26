import json
import asyncio
from typing import Dict, Any, List
from app.db.supabase_client import supabase
from app.services.llm_service import call_gemini, call_best_llm, call_parallel_merge, safe_json_loads
from app.services.ppt_renderer import generate_pptx_bytes

# ══════════════════════════════════════════════════════════════════════════════
# WORLD-CLASS PROMPTS — Engineered for maximum depth and quality
# ══════════════════════════════════════════════════════════════════════════════

STAGE_1_OUTLINE_PROMPT = """You are an expert curriculum designer, subject matter expert, and world-class presentation architect. Given a topic, produce the MOST comprehensive, deeply-structured slide-deck outline possible.

Return strict JSON:
{
  "deck_title": "An attention-grabbing, professional title",
  "sections": [
    { "id": "learning_objectives", "title": "...", "type": "objectives" },
    { "id": "concept_1", "title": "...", "type": "concept" }
  ]
}

REQUIREMENTS:
1. For "full" depth: 12-16 sections. For "quick" depth: 8-10 sections.
2. Each section must have a unique "id" and highly descriptive "title".
3. Adapt section TYPES to match the topic domain perfectly.
4. MUST include ALL of these:
   - Introduction & Overview
   - Learning Objectives
   - Core Concepts (multiple sections for different subtopics)
   - Deep Dive / Advanced Analysis
   - Real-World Applications & Industry Use Cases
   - Common Misconceptions & Pitfalls
   - Case Study / Worked Example
   - Comparison with Related Concepts
   - Best Practices & Key Principles
   - Future Trends & Emerging Developments
   - Summary & Key Takeaways
5. No LaTeX. Plain text only.
6. Think like a Stanford/MIT professor creating a lecture series.

Output JSON only, nothing else."""

STAGE_2_EXPANSION_PROMPT = """You are a world-class lecturer at a top university, preparing the BEST presentation slides ever created on this topic. Your goal is to create content that rivals the quality of the best courses on Coursera, MIT OpenCourseWare, and TED talks.

Return strict JSON:
{
  "deck_title": "...",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3", "takeaway 4", "takeaway 5"],
  "sections": [
    {
      "id": "...",
      "title": "...",
      "body_bullets": ["concrete, insightful bullet point with SPECIFIC data/facts", "..."],
      "example": "A vivid, real-world example or analogy that makes the concept click. Include specific names, dates, numbers, or companies. 3-4 sentences minimum.",
      "speaker_note": "5-6 sentences of deep teaching context. Include what to emphasize, common student questions, and connections to other topics.",
      "visual_hint": "generated_image",
      "image_prompt": "A clean, minimal flat-design illustration of [VERY specific visual description with exact elements to show], educational diagram style, white background, professional quality"
    }
  ]
}

CONTENT RULES FOR WORLD-CLASS QUALITY:
1. "body_bullets": 5-7 bullets. Each MUST contain SPECIFIC facts, numbers, dates, or named examples. NO vague generalities.
2. "example": MUST be a REAL, verifiable example. Include company names, historical events, scientific discoveries, or real data. Minimum 3 sentences.
3. "speaker_note": 5-6 sentences minimum. Include pedagogical insights, common misconceptions to address, and connections to prior/next sections.
4. "image_prompt": Be EXTREMELY specific — describe exact elements, layout, colors, and what each part of the illustration represents.
5. "key_takeaways": 5 powerful, memorable one-liners that a student would highlight and remember.
6. No LaTeX. Plain text only.
7. Every single piece of content must be factually accurate and substantive. Zero filler.

Output JSON only, nothing else."""

QUALITY_REVIEWER_PROMPT = """You are a harsh academic reviewer and quality assurance expert. Review this presentation content and IMPROVE it.

Your job:
1. Find any vague, generic, or weak bullet points and replace them with SPECIFIC, data-rich alternatives.
2. Ensure every example is REAL and includes specific names, numbers, or verifiable facts.
3. Add any CRITICAL subtopics that are missing.
4. Improve speaker notes to be more pedagogically rich.
5. Ensure the flow between sections is logical and builds understanding progressively.

Return the IMPROVED version in the EXACT same JSON structure. Only output JSON, nothing else.
Make SIGNIFICANT improvements - don't just rephrase. Add real depth and substance."""


# ══════════════════════════════════════════════════════════════════════════════
# HELPER — Parse JSON from any LLM with robust error handling
# ══════════════════════════════════════════════════════════════════════════════

async def _call_llm_with_json(
    messages: list, 
    temperature: float = 0.3, 
    max_tokens: int = 8192, 
    stage_name: str = "unknown",
    use_racing: bool = False,
    required_json_keys: list = None,
) -> dict:
    """
    Call LLM and parse the response as JSON with repair.
    use_racing=True runs Gemini + Groq in parallel and picks the best.
    """
    for attempt in range(2):
        try:
            if use_racing:
                raw_response = await call_best_llm(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    required_json_keys=required_json_keys,
                )
            else:
                raw_response = await call_gemini(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    retries=1
                )
            return safe_json_loads(raw_response)
        except Exception as e:
            if attempt == 0:
                print(f"[{stage_name}] Attempt 1 failed, retrying: {e}")
                await asyncio.sleep(1)
                continue
            raise Exception(f"[{stage_name}] Failed after 2 attempts: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1: OUTLINE GENERATION — Parallel race for best structure
# ══════════════════════════════════════════════════════════════════════════════

async def generate_outline_step(topic: str, depth: str, audience: str) -> dict:
    """Step 1: Generate the outline using parallel racing for best quality."""
    # Check cache first
    cache_res = supabase.table("deck_cache").select("*").eq("topic", topic).eq("depth", depth).eq("audience", audience).execute()
    if cache_res.data:
        return cache_res.data[0]["deck_json"]
    
    # 🏆 Race Gemini vs Groq — pick the outline with more sections and better structure
    outline_data = await _call_llm_with_json(
        messages=[
            {"role": "system", "content": STAGE_1_OUTLINE_PROMPT},
            {"role": "user", "content": f"Topic: {topic}\nDepth: {depth}\nAudience: {audience}"}
        ],
        temperature=0.3,
        max_tokens=4096,
        stage_name="Stage 1: Outline (Racing)",
        use_racing=True,
        required_json_keys=["deck_title", "sections"],
    )
    return outline_data


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2: EXPANSION — Parallel race for richest content per batch
# ══════════════════════════════════════════════════════════════════════════════

async def _merge_expansion_results(results: list, required_sections: int) -> dict:
    """
    Given multiple expansion results from different LLMs, merge them into
    the best possible output by picking the richest sections from each.
    """
    if len(results) == 1:
        return safe_json_loads(results[0])
    
    parsed_results = []
    for r in results:
        try:
            parsed_results.append(safe_json_loads(r))
        except Exception:
            continue
    
    if not parsed_results:
        raise Exception("No valid JSON from any provider")
    
    if len(parsed_results) == 1:
        return parsed_results[0]
    
    # Merge: for each section, pick the version with more content
    base = parsed_results[0]
    alt = parsed_results[1]
    
    base_sections = {s.get("id", i): s for i, s in enumerate(base.get("sections", []))}
    alt_sections = {s.get("id", i): s for i, s in enumerate(alt.get("sections", []))}
    
    merged_sections = []
    for sid, base_sec in base_sections.items():
        alt_sec = alt_sections.get(sid)
        if alt_sec:
            # Pick the richer version
            base_len = len(json.dumps(base_sec))
            alt_len = len(json.dumps(alt_sec))
            
            # Check specific quality markers
            base_bullets = len(base_sec.get("body_bullets", []))
            alt_bullets = len(alt_sec.get("body_bullets", []))
            
            base_example_len = len(str(base_sec.get("example", "")))
            alt_example_len = len(str(alt_sec.get("example", "")))
            
            # Score: more bullets + longer example + more content = better
            base_score = base_len + (base_bullets * 100) + (base_example_len * 2)
            alt_score = alt_len + (alt_bullets * 100) + (alt_example_len * 2)
            
            merged_sections.append(base_sec if base_score >= alt_score else alt_sec)
        else:
            merged_sections.append(base_sec)
    
    # Add any sections from alt that base doesn't have
    for sid, alt_sec in alt_sections.items():
        if sid not in base_sections:
            merged_sections.append(alt_sec)
    
    # Pick best takeaways (longer/more)
    base_takeaways = base.get("key_takeaways", [])
    alt_takeaways = alt.get("key_takeaways", [])
    best_takeaways = base_takeaways if len(base_takeaways) >= len(alt_takeaways) else alt_takeaways
    
    return {
        "deck_title": base.get("deck_title") or alt.get("deck_title", ""),
        "key_takeaways": best_takeaways,
        "sections": merged_sections,
    }


async def expand_outline_step(topic: str, audience: str, outline_data: dict) -> dict:
    """Step 2: Expand outline sections using parallel calls for richest content."""
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
        user_content = f"Topic: {topic}\nAudience: {audience}\n\nSections to expand:\n{json.dumps({'deck_title': deck_title, 'sections': batch})}"
        
        # 🔀 Run both LLMs in parallel and MERGE the best sections from each
        raw_results = await call_parallel_merge(
            messages=[
                {"role": "system", "content": STAGE_2_EXPANSION_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.4,
            max_tokens=8192,
        )
        
        # Merge results — pick richest content from each provider
        exp_data = await _merge_expansion_results(raw_results, len(batch))
        
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


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3: QUALITY REVIEW — Optional AI reviewer pass for premium quality
# ══════════════════════════════════════════════════════════════════════════════

async def quality_review_step(topic: str, audience: str, deck_data: dict) -> dict:
    """
    Stage 3 (Optional): Run an AI quality review pass to improve content.
    Uses the fastest available model since this is an enhancement pass.
    """
    try:
        review_result = await _call_llm_with_json(
            messages=[
                {"role": "system", "content": QUALITY_REVIEWER_PROMPT},
                {"role": "user", "content": f"Topic: {topic}\nAudience: {audience}\n\nPresentation to review and improve:\n{json.dumps(deck_data)}"}
            ],
            temperature=0.2,
            max_tokens=8192,
            stage_name="Stage 3: Quality Review",
            use_racing=False,  # Use fastest available (cascading)
            required_json_keys=["sections"],
        )
        
        # Validate the review actually returned content
        if review_result.get("sections") and len(review_result["sections"]) >= len(deck_data.get("sections", [])) * 0.8:
            print("✅ Quality review pass improved the content")
            # Preserve original title and takeaways if review didn't include them
            if not review_result.get("deck_title"):
                review_result["deck_title"] = deck_data.get("deck_title", topic)
            if not review_result.get("key_takeaways"):
                review_result["key_takeaways"] = deck_data.get("key_takeaways", [])
            return review_result
        else:
            print("⚠️ Quality review returned insufficient content, keeping original")
            return deck_data
            
    except Exception as e:
        print(f"⚠️ Quality review failed (non-critical), keeping original: {e}")
        return deck_data


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4: RENDER — Build PPTX file and upload
# ══════════════════════════════════════════════════════════════════════════════

async def render_deck_step(deck_id: str, user_id: str, topic: str, depth: str, audience: str, final_deck_json: dict) -> str:
    """Step 4: Render the PPTX, upload to storage, and return the download URL."""
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
