# TEACHGENIE — TRUE RUNTIME EXECUTION & CALL GRAPH
**Audit Date:** September 12, 2026  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer  
**Standard:** Verified line-by-line against runtime code in `backend/app/` and `frontend/src/`

---

## 1. Advanced Presentation Engine (V2)

### Execution Trace
```text
User clicks "Generate Deck" (TopicDeckPage.tsx)
  │
  ├──> HTTP POST /api/decks/generate-advanced
  │     │   Payload: {topic, slide_count: 12, audience, design, theme, depth, options}
  │     ├──> Auth Dependency: Depends(get_current_user), require_pro, check_topic_deck_limit
  │     ├──> DB Write 1: supabase.table("topic_decks").insert(status="processing")
  │     └──> Queue Background Task: _background_generate_deck (deck_id, config)
  │           │
  │           ▼
  └───> generate_presentation_pipeline (presentation/orchestrator.py)
        │
        ├── [STEP 0: CACHE CHECK]
        │   ├── Algorithm: SHA256 config hash lookup in presentation_cache table
        │   ├── CACHE HIT ───────────> Return PresentationSpec + python-pptx render (0 LLM Calls)
        │   └── CACHE MISS ──────────> Continue to Step 0.5
        │
        ├── [STEP 0.5: TOPIC ONTOLOGY AGENT] (topic_ontology_agent.py)
        │   ├── Context: Topic, audience, depth
        │   ├── Algorithm: ai_router.generate_text(task="planning")
        │   ├── LLM Call 1: OpenRouter (openai/gpt-4o) [Timeout: 35s]
        │   │   ├── Primary Success ──> Returns TopicOntologyChecklist (must_include, misconceptions)
        │   │   └── Timeout/Fail ─────> Graceful degradation: returns empty checklist (pipeline survives)
        │
        ├── [STEP 1: PLANNER AGENT] (planner_agent.py)
        │   ├── Context: Topic + ontology checklist + slide_count
        │   ├── LLM Call 2: OpenRouter (openai/gpt-4o) [Timeout: 50s]
        │   │   ├── Output: 12 planned SlideSpec skeletons (titles, slide types, archetype)
        │   │   └── Fail ─────────────> Fallback to Gemini 2.0 Flash -> Groq Llama 3.3 70B
        │
        ├── [STEP 2: CONTENT AGENT] (content_agent.py)
        │   ├── Context: 12 slide outlines batched into a single prompt
        │   ├── LLM Call 3: OpenRouter (openai/gpt-4o) [Timeout: 90s, max_tokens: 4096]
        │   │   ├── Output: Full body bullets, speaker notes, image queries, self_check
        │   │   └── Fail ─────────────> Fallback cascade (Gemini 2.0 Flash)
        │
        ├── [STEP 3: VISUAL AGENT] (visual_agent.py & image_source_router.py)
        │   ├── Algorithm: Deterministic stock query router (Pexels -> Pixabay -> Unsplash)
        │   ├── External API Calls: 6–12 HTTP calls across stock photo provider pools
        │   ├── Image Caching: SHA256 query hash in SimpleTTLCache (24h TTL)
        │   └── Zero LLM Calls: Uses exact image_query from Content Agent
        │
        ├── [STEP 4: STRUCTURAL QA AGENT] (qa_agent.py)
        │   ├── Algorithm: Deterministic Python bounds checks (word density, bullet count, contrast)
        │   ├── Repair: Truncates excessive text, auto-heals diagram schemas (0 LLM Calls)
        │   └── Fail ─────────────────> Graceful pass-through of unedited slides
        │
        ├── [STEP 4.5: REVIEWER / CRITIC AGENT] (reviewer_agent.py)
        │   ├── Context: Entire 12-slide presentation JSON + ontology checklist
        │   ├── LLM Call 4: OpenRouter (openai/gpt-4o) [Timeout: 35s]
        │   │   ├── Primary Success ──> Returns polished slides (fixing pedagogical repetition)
        │   │   └── Fail/Timeout ─────> Graceful degradation: returns Step 4 slides as-is
        │
        ├── [STEP 5: PPTX COMPILATION] (presentation_engine/builder.py)
        │   ├── Algorithm: python-pptx deterministic geometry builder
        │   └── Output: In-memory PPTX binary buffer (0 LLM Calls)
        │
        ├── [STEP 6: PERSISTENCE & STORAGE]
        │   ├── Storage Upload: Supabase Storage bucket 'topic_decks/{user_id}/{deck_id}.pptx'
        │   ├── DB Write 2: supabase.table("topic_decks").update(status="ready", storage_path=...)
        │   └── DB Write 3: supabase.table("presentation_cache").insert(config_hash, spec_json)
        │
        └── Frontend Polling: GET /api/decks/{deck_id} every 2.5s until status == "ready"
```

---

## 2. AI Study Notes Generation & Artifact Certification

### Execution Trace
```text
User clicks "Generate Notes" (NotesGeneratorPage.tsx)
  │
  ├──> HTTP POST /api/notes-generator/generate
  │     │   Payload: {topic, class_level, subject, curriculum, detail_level, student_id}
  │     ├──> Auth Dependency: Depends(get_current_user)
  │     ├──> Rate Limiter: slowapi 20 requests/minute
  │     │
  │     ▼
  └───> NotesGenerator.generate_notes (notes/generator.py)
        │
        ├── [STEP 1: CONTEXT ENGINE] (notes/context/analyzer.py)
        │   ├── Normalization: CanonicalNotesContext.from_raw()
        │   ├── Catalog Registry: TopicDescriptor matching (Class 3-12 syllabus)
        │   ├── Algorithm: Pure Python data prioritization (Tier 1 explicit -> Tier 6 fallback)
        │   ├── DB Write: ContextSnapshotManager persists immutable snapshot (0 LLM Calls)
        │   └── Output: CanonicalNotesContext
        │
        ├── [STEP 2: DECISION ENGINE] (notes/decision/learning_flow_planner.py)
        │   ├── Algorithm: Deterministic rule-based Learning Flow Planner
        │   │   ├── Evaluates LearnerEntryState (mastery, confidence, misconceptions)
        │   │   ├── Selects LearningMode (REMEDIATION vs ABSORPTION vs MASTERY)
        │   │   └── Prescribes exact stage sequence (e.g. prerequisite_bridge -> 6-part debunk)
        │   └── Output: NotesGenerationPlan (0 LLM Calls)
        │
        ├── [STEP 3: GENERATION ENGINE] (notes/generation/engine.py)
        │   ├── Prompt Construction: prompt_builder.py builds strict pedagogical prompt
        │   ├── LLM Call: ai_router.generate_text(task="content_generation")
        │   │   ├── Model: OpenRouter (openai/gpt-4o) / Gemini 2.0 Flash / Groq Llama 3.3 70B
        │   │   ├── JSON Parsing: safe_json_loads with regex fence & trailing comma repair
        │   │   └── Complete LLM Failure ──> Deterministic Fallback Generator executes plan
        │   └── Output: NotesDocument (strongly-typed Pydantic model)
        │
        ├── [STEP 4: VALIDATION ENGINE] (notes/validation/engine.py)
        │   ├── Deterministic Invariant Validators (0 LLM Calls):
        │   │   ├── StructureValidator (section counts, required types)
        │   │   ├── LearningFlowValidator (active inquiry check, misconception repair presence)
        │   │   ├── BloomTaxonomyValidator (practice question difficulty progression)
        │   │   └── TypesetterValidator (KaTeX formula balance, orphaned markdown tokens)
        │   └── Output: ValidationResult (Score 0-100%, status: VALID / VALID_WITH_WARNINGS / REJECTED)
        │
        ├── [STEP 5: RENDERING & CERTIFICATION] (notes/rendering/ & certification/)
        │   ├── HTMLNoteBuilder.build_html(): Assembles print-ready A4 HTML document
        │   ├── StudentArtifactCertifier.certify(): Evaluates objective coverage (100% deterministic)
        │   └── DB Write: supabase.table("generated_notes").insert(content_json, quality_score)
        │
        └── HTTP 200 Response: Returns complete NotesDocument + validation report
```

---

## 3. Canonical Quiz Engine (Generation & Regeneration)

### Execution Trace
```text
User triggers Quiz Generation (from Quiz page, PDF, TeachMe, or Lesson Planner)
  │
  ├──> HTTP POST /api/quiz/quizzes
  │     │   Payload: {topic, count: 10, difficulty, mode, source_type, source_ids, idempotency_key}
  │     ├──> Idempotency Check: repo.get_quiz_by_idempotency() ──> CACHE HIT: Returns existing quiz (0 calls)
  │     ├──> Ownership Check: repo.verify_source_ownership() (prevents cross-tenant leak)
  │     │
  │     ▼
  └───> run_quiz_generation (quiz/generator.py)
        │
        ├── [STEP 1: EVIDENCE RETRIEVAL] (knowledge/hybrid_search.py)
        │   ├── Embedding Call: gemini-embedding-001 generates query vector
        │   └── DB RPC: match_document_chunks (cosine similarity in pgvector scoped to user_id)
        │
        ├── [STEP 2: CONTENT GENERATION] (quiz/generator.py)
        │   ├── LLM Call: ai_router.generate_text(task="content_generation")
        │   │   ├── Model: OpenRouter (openai/gpt-4o) / Gemini 2.0 Flash
        │   │   └── Output: JSON with 10 questions, 4 options each, distractors, Bloom level, explanation
        │
        ├── [STEP 3: DETERMINISTIC VALIDATION & CLEANUP] (quiz/generator.py)
        │   ├── Prunes duplicate options
        │   ├── Verifies correct_answer exists exactly once in options
        │   └── Enforces minimum explanation length (0 LLM Calls)
        │
        ├── [STEP 4: PERSISTENCE]
        │   ├── DB Write 1: supabase.table("quizzes").insert(...)
        │   └── DB Write 2: supabase.table("quiz_questions").insert(batch_of_10)
        │
        └── HTTP 200 Response: Returns Quiz object with questions and metadata
              │
              ▼
[OPTIONAL WORKFLOW: SINGLE-QUESTION REGENERATION]
User clicks "Regenerate Question" on Question 4
  │
  ├──> HTTP POST /api/quiz/quizzes/{quiz_id}/questions/{question_id}/regenerate
  │     ├── Context: Parent quiz topic, existing questions (to prevent duplication), target question index
  │     ├── LLM Call: ai_router.generate_text(task="repair", max_tokens=600)
  │     │   └── Generates ONLY 1 single replacement question
  │     ├── DB Write: supabase.table("quiz_questions").update().eq("id", question_id)
  │     └── HTTP 200 Response: Returns updated Question object (1 LLM Call, zero full-quiz regeneration)
```

---

## 4. Live Classroom Quiz Engine & Interventions

### Execution Trace
```text
Teacher clicks "Start Live Session" (LiveQuizHostPage.tsx)
  │
  ├──> HTTP POST /api/live-quizzes/
  │     ├── Generates 6-character room PIN (e.g. "839201")
  │     ├── DB Write: supabase.table("live_quiz_sessions").insert(questions_snapshot)
  │     └── Returns session_id and PIN
  │
Students join at /join (JoinLiveQuizPage.tsx)
  │
  ├──> HTTP POST /api/live-quizzes/{session_id}/join
  │     ├── Generates signed Participant JWT
  │     ├── DB Write: supabase.table("live_quiz_participants").insert()
  │     └── Supabase Realtime broadcasts PARTICIPANT_JOINED event
  │
Teacher advances question -> Students submit answers
  │
  ├──> HTTP POST /api/live-quizzes/{session_id}/responses
  │     ├── Score Engine (scoring.py): Pure Python speed-decay calculation:
  │     │   $$\text{Score} = 500 + 500 \times \left(1 - \frac{\text{time\_taken}}{\text{time\_limit}}\right)$$
  │     ├── DB Write: supabase.table("live_quiz_responses").insert()
  │     └── Realtime Broadcast: RESPONSE_SUBMITTED to Host Dashboard
  │
[TEACHER REMEDIAL INTERVENTION WORKFLOW]
Teacher notices 65% of class chose Distractor B ("Confusing ionic with covalent")
Teacher clicks "Intervention: Visual" OR "Intervention: Explain"
  │
  ├──> HTTP POST /api/live-quizzes/{session_id}/intervene
  │     │   Payload: {action_type: "visual" | "explain" | "example" | "followup"}
  │     │
  │     ├── Branch A: action_type == "visual"
  │     │   ├── Algorithm: render_flowchart_svg() generates SVG diagram
  │     │   ├── Comparison Card: Assembled deterministically from correct answer vs top distractor
  │     │   └── TOTAL LLM CALLS: 0
  │     │
  │     └── Branch B: action_type in ["explain", "example", "followup"]
  │         ├── Context: Question stem + correct answer + top wrong distractor
  │         ├── LLM Call: ai_router.generate_text(task="content_generation", max_tokens=250-350)
  │         └── TOTAL LLM CALLS: 1
  │
  └── Realtime Broadcast: INTERVENTION_TRIGGERED sent to all participant screens
```

---

## 5. Teach Me (Adaptive Socratic AI Tutor)

### Execution Trace
```text
Student starts session on topic "Mitosis" (TeachMePage.tsx)
  │
  ├──> HTTP POST /api/teach/start
  │     ├── (Optional) Ingest YouTube URL -> transcripts chunked & embedded
  │     ├── LLM Call 1: Teacher Agent generates initial 4-concept LessonPlan + Concept 1 explanation + Checkpoint question
  │     ├── DB Write: supabase.table("teachme_sessions").insert(plan_json, state_json)
  │     └── Returns Concept 1 dialogue + Checkpoint prompt
  │
Student types answer: "The chromosomes pull apart because of magnetic fields"
  │
  ├──> HTTP POST /api/teach/answer
  │     │
  │     ├── [STEP 1: ASSESSMENT AGENT] (assessment_agent.py)
  │     │   ├── Context: Concept objective + student answer + expected criteria
  │     │   ├── LLM Call 2: Evaluates correctness (incorrect) + identifies misconception ("magnetic fields")
  │     │   └── Output: EvaluationResult(correctness="incorrect", misconception="Confusing spindle fibers with magnetism")
  │     │
  │     ├── [STEP 2: MASTERY CALCULATION] (mastery.py)
  │     │   ├── Algorithm: Additive step accumulator + exponential confidence
  │     │   │   $$\Delta = -0.22 \quad (\text{misconception penalty})$$
  │     │   │   $$\text{Score} = \max(0, \text{current} - 0.22)$$
  │     │   │   $$\text{Decision} = \text{"switch\_strategy\_reteach"}$$
  │     │   └── Zero LLM Calls (Pure Python math)
  │     │
  │     ├── [STEP 3: TEACHER AGENT] (teacher_agent.py)
  │     │   ├── Context: Reteach decision + detected misconception + conversation history
  │     │   ├── LLM Call 3: Generates targeted analogy explaining microtubule spindle fibers
  │     │   └── Returns warm Socratic response + simplified repair checkpoint
  │     │
  │     └── DB Write: supabase.table("teachme_turns").insert(student_msg, assistant_msg, mastery_delta)
  │
TOTAL COST PER STUDENT TURN: Exactly 2 LLM Calls (Assessment + Teacher)
```

---

## 6. Video Studio & Compiler Pipeline

### Execution Trace
```text
User creates video on "Photosynthesis" (VideoGeneratorPage.tsx)
  │
  ├──> HTTP POST /api/lessons/
  │     ├── DB Write: supabase.table("video_lessons").insert(status="processing")
  │     └── Background Task: generate_video_pipeline (video/orchestrator.py)
  │           │
  │           ├── [SCENE PLANNING]
  │           │   ├── Path A: Standalone Topic ──> LLM Call 1: plan_storyboard() generates 4–6 scenes
  │           │   └── Path B: TeachMe Export ───> 0 LLM Calls (build_storyboard_from_teach_me_state reuses concept text)
  │           │
  │           ├── [MEDIA RESOLUTION PER SCENE] (visual_router.py)
  │           │   ├── Algorithm: calculate_ai_video_necessity_score()
  │           │   ├── Branch: Uses SVG Diagrams (flowchart, card stack) -> 0 token cost
  │           │   └── Branch: Uses Stock Photo search (Pexels API) -> 0 token cost
  │           │
  │           ├── [TTS AUDIO SYNTHESIS] (tts/tts_service.py)
  │           │   ├── Cache Check: MD5 hash of narration text in tempfile tts_cache
  │           │   ├── CACHE HIT ───────────> Reuses existing .wav file
  │           │   └── CACHE MISS ──────────> Calls edge-tts (free) -> fallback gTTS -> fallback offline tone
  │           │
  │           ├── [SUBTITLES & COMPOSITION] (captions/ & compositor/)
  │           │   ├── generate_srt_subtitles(): Word-count rate mathematical alignment (0 LLM Calls)
  │           │   ├── compose_single_scene_clip(): Local FFmpeg stitches slide image + audio + captions
  │           │   └── concatenate_scenes_to_final_video(): Merges scene clips into final .mp4
  │           │
  │           ├── [PERSISTENCE]
  │           │   ├── Uploads final .mp4 to Supabase Storage bucket 'videos/'
  │           │   └── DB Write: supabase.table("video_lessons").update(status="ready", storage_path=...)
  │           │
  │           └── [SINGLE SCENE REGENERATION] (POST /api/lessons/{id}/regenerate-scene)
  │               ├── Re-renders ONLY the targeted scene with new audio/visuals
  │               └── Concatenates unchanged scenes + new scene via FFmpeg (0 full-video re-runs)
```

---

## 7. Chat with PDF (V1 RAG vs. V2 Multi-Agent)

### Execution Trace
```text
Student sends question in ChatPage.tsx
  │
  ├───> Frontend calls sendMessageV2() ──> HTTP POST /chat/v2/ask
  │     │
  │     ├── [STEP 1: ORCHESTRATOR AGENT] (agents/orchestrator.py)
  │     │   ├── LLM Call 1: Gemini 3.6 Flash classifies intent: 'doubt' | 'content_request' | 'clarify' | 'chat'
  │     │
  │     ├── [BRANCH 1: INTENT == 'doubt']
  │     │   ├── Librarian Agent (agents/librarian.py):
  │     │   │   ├── Searches user notes in pgvector (gemini-embedding-001)
  │     │   │   └── If insufficient -> DDGS web search fallback
  │     │   └── Tutor Agent (agents/tutor.py):
  │     │       └── LLM Call 2: Gemini 3.6 Flash produces Socratic explanation
  │     │
  │     ├── [BRANCH 2: INTENT == 'content_request']
  │     │   └── Content Creator Agent (agents/content_creator.py):
  │     │       └── Generates flashcards or delegates to Deck / Video background job
  │     │
  │     └── DB Write: supabase.table("chat_messages").insert(role, content, session_id)
  │
  └───> (Legacy Shadowed Path: HTTP POST /chat/ask)
        ├── Embedding Call: gemini-embedding-001
        ├── RPC: match_document_chunks
        └── LLM Call 1: Gemini 3.6 Flash directly synthesizes answer with page citations
```
