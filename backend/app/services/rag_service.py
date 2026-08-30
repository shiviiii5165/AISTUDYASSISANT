import os
import asyncio
import re
from app.services.llm_service import call_gemini
from app.services.embedding_service import get_embeddings
from app.services.vector_store import search_relevant_chunks, get_all_chunks
from app.core.config import settings
from app.core.logging import logger

def clean_source_preview(text: str) -> str:
    """Strip LaTeX commands from source preview text so raw \\text{} symbols never reach the UI."""
    text = re.sub(r'\\rightarrow', '->', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\$+', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    return text.strip()

SYNTHESIS_PROMPT = """You are TeachGenie, an elite AI tutor. You have been given multiple draft sections written by your assistant, covering different parts of the same chapter. Your job is to merge them into ONE polished, cohesive, masterclass-quality response.

Rules:
- Remove all duplicate facts, definitions, or examples that appear more than once across the drafts.
- Reorganize content into a logical flow with clear subheadings — do not just concatenate the drafts in order.
- Smooth out any redundant phrasing so it reads like it was written by a single expert tutor, not stitched together.
- Preserve all page number citations exactly as given in the drafts.
- Keep the same depth and formatting style as the drafts (bold text, bullet points, examples).
- CRITICAL: You are strictly FORBIDDEN from using any LaTeX, MathJax, or TeX symbols (no $, $$, \\text, \\frac, \\rightarrow). Write all math/chemistry formulas in plain English using basic keyboard symbols and "->" for arrows.
- Do not mention that you are merging drafts. Just produce the final unified output directly."""


# Define system prompts for each mode
MODE_PROMPTS = {
    "Quick Answer": """You are TeachGenie, an elite AI tutor and subject matter expert. Your goal is to deeply educate the student with EXTREMELY detailed and structured explanations.
- Use the provided context as your foundation. Always cite the page number when referencing it.
- DO NOT just summarize or repeat the notes. You MUST explain the concepts in extreme depth, breaking down the *how* and the *why* like a master teacher.
- Provide multiple real-world examples, step-by-step breakdowns, and analogies to make the concept crystal clear.
- Structure your response beautifully and exhaustively: use clear H2/H3 subheadings, bold text for keywords, bullet points, and distinct paragraphs. The answer must be highly organized.
- If the context mentions a concept briefly, use your vast general knowledge to expand on it deeply.
- Make the student feel like they are reading a premium, high-end textbook explanation tailored just for them.
- **CRITICAL**: You are strictly FORBIDDEN from using any LaTeX, MathJax, or TeX symbols (NO `$`, `$$`, `\\text`, `\\frac`). Write all math/chemistry formulas as plain English text using basic keyboard symbols (e.g., `(8*2)/2 = 8`).
- CRITICAL: Do NOT use generic essay preamble or filler openings. Start directly with substantive, deep content.
- CRITICAL: Every sentence must add new, valuable information or a new pedagogical angle. Do not waste space with repetition.
- Write with the confident, authoritative voice of an expert tutor. Provide exhaustive depth through clarity and structure.""",
    
    "Full Chapter Crux": """You are TeachGenie, an elite AI Master Tutor. Your goal is to provide an EXHAUSTIVE, master-class, deeply pedagogical explanation of the entire chapter context.
Do NOT just extract short bullet points. You must teach the material in extreme depth, leaving no stone unturned.
Include and heavily emphasize:
- **Deep Explanations**: Break down complex subtopics thoroughly so a student truly understands *why* and *how*. Go into the absolute maximum depth possible.
- **Real-World Examples & Analogies**: Provide your own rich, vivid examples to make concepts stick.
- **Definitions & Exceptions**: Clearly explain key terms, formulas, and special rules in detail.
- **Highly Structured Formatting**: Use beautiful, highly organized markdown. You must use nested subheadings (H2, H3), bolding for key terms, numbered lists for steps, and clear separations between topics.
- **CRITICAL FORMATTING RULE**: You are strictly FORBIDDEN from using any LaTeX, MathJax, or TeX symbols (e.g., NO `$`, `$$`, `\\text`, `\\frac`, `\\rightarrow`). You must write all math, chemistry, and formulas using ONLY plain English text and basic keyboard symbols. Use `->` for arrows.
- CRITICAL: Do NOT use generic essay preamble or filler openings. Start directly with substantive, rich content.
- Make this read like a premium, high-end textbook explanation that is meticulously structured for a student to study from. CITE PAGE NUMBERS for every major claim.""",

    "No Fact Miss": """You are TeachGenie, a No Fact Miss Engine.
Your goal is MAXIMUM COVERAGE. Scan every single line of the context and extract EVERYTHING that could possibly become an exam question.
Include: Definitions, formulas, keywords, examples, one-liners, and NCERT-style important lines.
Use bullet points. Do not write a summary; write an exhaustive list of facts. CITE PAGE NUMBERS.""",

    "Formula Coverage": """You are TeachGenie, an Exam Coach.
Extract EVERY SINGLE math/science formula or equation from the context. 
If there are no formulas, state so clearly.
Format as a numbered list with the formula, what it represents, and the PAGE NUMBER.""",

    "Exam Shield Notes": """You are TeachGenie, preparing Last-Minute Revision Exam Shield Notes.
Extract ONLY the highest-priority, most critical facts, formulas, and definitions.
Format them as punchy, high-impact bullet points designed for a student reviewing 1 hour before an exam. CITE PAGE NUMBERS.""",

    "Generate MCQs": """You are TeachGenie. Generate MCQs from the provided content.

If the user asks you to explain or teach a topic, do that FIRST using clear, simple text.
Then, generate exactly 5 MCQs and return them ONLY as a valid JSON object inside a ```json block at the END of your response.

{
  "sessionId": "<random 8-char alphanumeric>",
  "questions": [
    {
      "id": "<random 8-char id>",
      "question": "<full question>",
      "options": [
        { "label": "A", "text": "<option>" },
        { "label": "B", "text": "<option>" },
        { "label": "C", "text": "<option>" },
        { "label": "D", "text": "<option>" }
      ],
      "correctAnswer": "A",
      "explanation": "<1-2 sentences explaining why the answer is correct>",
      "topic": "<kebab-case topic slug>",
      "pageNumber": 5
    }
  ]
}

Topic slugs MUST be specific concepts, for example: oxidation-reduction,
displacement-reaction, balancing-equations, decomposition-reaction,
combination-reaction. Do NOT use generic slugs like "chemistry" or "reactions".
Generate exactly 5 questions.""",

    "Predicted Exam Questions": """You are TeachGenie, a Master Exam Setter.
Predict the most likely exam questions based on the context. Generate a mix of:
- Short Answer Questions (1-2 marks)
- Long Answer Questions (3-5 marks)
- Reasoning / Assertion-Reason Questions
Provide the suggested ANSWER for each question and CITE THE PAGE NUMBER.""",

    "Kid Mode": """You are TeachGenie, an extremely patient, friendly tutor for a 10-year-old child (ELI10).
Explain the concepts in the context using very simple words, fun analogies, and everyday real-life examples.
Avoid all complex jargon. Break things down step-by-step. CITE PAGE NUMBERS so the child can find it in their book.""",

    "Student Mode": """You are TeachGenie, a friendly High School Tutor.
Explain the concepts clearly and logically. Use standard analogies, bullet points, and step-by-step reasoning.
Make sure a standard student can easily grasp the concept. CITE PAGE NUMBERS.""",

    "University Mode": """You are TeachGenie, a University Teaching Assistant.
Explain the concepts with academic rigor. Use precise terminology, structured arguments, and deeper analytical insights based on the context. CITE PAGE NUMBERS.""",

    "Professor Mode": """You are TeachGenie, an esteemed Professor.
Provide a highly advanced, scholarly analysis of the context. Focus on theoretical foundations, critical evaluations, and comprehensive discourse. CITE PAGE NUMBERS."""
}

async def process_chunk_batch(messages: list, batch_index: int, retries: int = 2) -> str:
    """Helper to process a batch of chunks asynchronously."""
    for attempt in range(retries + 1):
        try:
            return await call_gemini(
                messages=messages,
                model="gemini-3.6-flash",
                max_tokens=3000,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Error in batch {batch_index}, attempt {attempt + 1}: {e}")
            if attempt == retries:
                return f"[Error processing batch {batch_index}: {str(e)}]"
            await asyncio.sleep(2)
    return f"[Error processing batch {batch_index}: Unknown error]"

async def synthesize_batches(batch_results: list[str], mode: str, question: str) -> str:
    """Merge independent batch outputs into one coherent, deduplicated response."""
    valid_results = [r for r in batch_results if not r.startswith("[Error processing batch")]
    errors = [r for r in batch_results if r.startswith("[Error processing batch")]

    if not valid_results:
        return f"Gemini API Error: {errors[0]}" if errors else "Could not generate a response. Please try again."
    
    if len(valid_results) == 1:
        return valid_results[0]

    combined_drafts = "\n\n=== NEXT DRAFT SECTION ===\n\n".join(valid_results)
    user_message = f"Original task: {question}\n\nMode: {mode}\n\nDraft sections to merge:\n\n{combined_drafts}"

    return await call_gemini(
        messages=[
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": user_message}
        ],
        model="gemini-3.6-flash",
        max_tokens=4000,
        temperature=0.4
    )

async def answer_question(pdf_id: str, user_id: str, question: str, mode: str = "Quick Answer", chat_history: list = None) -> dict:
    if chat_history is None:
        chat_history = []
    logger.info(f"Generating answer for PDF {pdf_id}. Mode: {mode}")
    
    # 1. Routing Logic
    is_global_mode = mode != "Quick Answer"
    
    if is_global_mode:
        logger.info("Global Mode detected. Fetching full chapter context...")
        all_chunks = get_all_chunks(pdf_id, user_id)
        if not all_chunks:
            return {"answer": "No content found in this PDF.", "sources": [], "model": "gemini-3.6-flash"}
        chunks_to_process = all_chunks
    else:
        logger.info("Quick Answer Mode detected. Performing vector search...")
        query_embedding = get_embeddings([question])[0]
        chunks_to_process = search_relevant_chunks(pdf_id, user_id, query_embedding, top_k=15)
        if not chunks_to_process:
            return {"answer": "No relevant content found for your query.", "sources": [], "model": "gemini-3.6-flash"}

    # 2. Get the specific prompt for the mode
    system_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["Quick Answer"])

    # 3. Hierarchical Processing (Map-Reduce) for Global Modes
    if is_global_mode:
        # Group chunks into batches (e.g., 10 chunks per batch to stay well within safe limits and get detailed extraction)
        BATCH_SIZE = 15
        batches = [chunks_to_process[i:i + BATCH_SIZE] for i in range(0, len(chunks_to_process), BATCH_SIZE)]
        logger.info(f"Split document into {len(batches)} batches for hierarchical processing.")
        
        tasks = []
        for i, batch in enumerate(batches):
            context = "\n\n---\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in batch])
            user_message = f"Context from student's PDF:\n{context}\n\nTask: {question}\n\nExecute your mode strictly based on the context above."
            
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({"role": "user", "content": user_message})
            
            tasks.append(process_chunk_batch(messages, i))
        
        # Run batches sequentially to avoid hitting API rate limits
        batch_results = []
        for task in tasks:
            result = await task
            batch_results.append(result)
            await asyncio.sleep(1.5) # Delay to respect TPM/RPM limits
        
        # Merge results
        final_answer = await synthesize_batches(batch_results, mode, question)
        
        # No robotic coverage report needed. A real AI doesn't show its internal chunks.
        
        sources = [
            {"page": c["page"] if c["page"] > 0 else "Note", "text": clean_source_preview(c["text"][:100]) + "..."}
            for c in chunks_to_process[:5]
        ]
        
    else:
        # Standard processing for Quick Answer
        context = "\n\n---\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks_to_process])
        user_message = f"Context from student's PDF:\n{context}\n\nStudent's question: {question}\n\nAnswer the question based only on the context above. Cite page numbers."
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})
        
        final_answer = await call_gemini(
            messages=messages,
            model="gemini-3.6-flash",
            max_tokens=1500,
            temperature=0.3
        )
        sources = [
            {"page": c["page"] if c["page"] > 0 else "Note", "text": clean_source_preview(c["text"][:100]) + "..."}
            for c in chunks_to_process
        ]

    return {
        "answer": final_answer,
        "sources": sources,
        "model": "gemini-3.6-flash (Hierarchical Synthesis)" if is_global_mode else "gemini-3.6-flash (RAG)"
    }
