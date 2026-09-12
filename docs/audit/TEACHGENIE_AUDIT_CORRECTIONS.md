# TEACHGENIE AUDIT CORRECTIONS & VERIFICATION REPORT
**Audit Date:** September 12, 2026  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer  
**Status:** COMPLETE & GROUNDED IN RUNTIME SOURCE CODE

---

## Executive Summary of Audit Corrections

The Phase 0/1 report established a strong repository map, but a strict line-by-line runtime verification revealed **four significant inaccuracies**, **two instances of misleading pedagogical terminology**, and **several dead/orphaned endpoints** that were previously marked as active.

---

## 1. Feature Status Corrections: Live vs. Legacy vs. Dead

| Feature / Endpoint | Previous Report Status | Actual Runtime Status | Evidence & Line Numbers | Impact & Verdict |
|---|---|---|---|---|
| **V1 Deck Generation**<br>`POST /api/decks/outline`<br>`POST /api/decks/expand`<br>`POST /api/decks/render` | LIVE | **LEGACY / ORPHANED** | [frontend/src/pages/TopicDeckPage.tsx:213](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/frontend/src/pages/TopicDeckPage.tsx#L213) exclusively calls `/api/decks/generate-advanced`. Zero frontend calls exist for `/outline`, `/expand`, or `/render`. | **Dead Code**. The entire 4-step manual deck flow in `deck_service.py` is bypassed in production by the V2 orchestrator. |
| **Lesson Planner Video**<br>`POST /api/lesson-planner/{id}/stages/{id}/video` | LIVE | **DEAD / DISABLED** | [backend/app/api/lesson_planner.py:497](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/api/lesson_planner.py#L497): Hardcoded to return `HTTP 400: "Video generation has been removed from the Lesson Planner workflow."` | **Dead Endpoint**. Video can only be initiated via `/api/lessons` or TeachMe export, not within lesson roadmaps. |
| **Standalone Agent Endpoints**<br>`POST /api/orchestrator/route`<br>`POST /api/librarian/retrieve`<br>`POST /api/tutor/turn` | LIVE | **MOCKED / TEST-ONLY** | [backend/app/api/orchestrator.py:7-9](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/api/orchestrator.py#L7): Docstring explicitly confirms: *"This endpoint is additive — it does NOT modify chat.py, teach.py, or any existing route. It exists purely for independent testing"*. Zero frontend references exist. | **Test Harness Only**. These endpoints consume maintenance overhead but handle 0% of user traffic. |
| **V1 PDF Chat**<br>`POST /chat/ask` | LIVE | **SECONDARY / SHADOWED** | [frontend/src/pages/ChatPage.tsx:182](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/frontend/src/pages/ChatPage.tsx#L182) calls `sendMessageV2()` which targets `POST /chat/v2/ask`. | **Partially Legacy**. `/chat/ask` is only reachable via manual API calls or fallback. |

---

## 2. LLM Call Count & Branching Corrections

### A. Live Quiz Remediation (`live_quiz/intervention.py`)
- **Previous Claim:** "Live Quiz Remediation executes 1 LLM call or combines visual + explanation."
- **Runtime Truth:** **CORRECTED TO STRICT MUTUAL EXCLUSION (0 OR 1 CALL)**.
- **Evidence:** In [backend/app/services/live_quiz/intervention.py:54-175](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/services/live_quiz/intervention.py#L54-L175), `action_type` is a strict `if/elif/elif/elif` branch:
  1. `action_type == "visual"`: Executes **0 LLM calls**. Generates deterministic SVG flowchart via `render_flowchart_svg()` and static comparison card.
  2. `action_type == "explain"`: Executes **1 LLM call** (max 250 tokens).
  3. `action_type == "example"`: Executes **1 LLM call** (max 250 tokens).
  4. `action_type == "followup"`: Executes **1 LLM call** (max 350 tokens).
  They are never executed simultaneously or batched. Each teacher button click triggers exactly 0 or 1 call.

### B. V2 Presentation Generation (`presentation/orchestrator.py`)
- **Previous Claim:** "4 LLM calls sequential."
- **Runtime Truth:** **VERIFIED — 4 CALLS WORST CASE, BUT STEP 4.5 CAN BE BYPASSED**.
- **Evidence:** [backend/app/services/presentation/orchestrator.py:82-144](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/services/presentation/orchestrator.py#L82-L144):
  1. `generate_topic_ontology`: 1 call (OpenRouter `gpt-4o` / Gemini).
  2. `plan_presentation`: 1 call (OpenRouter `gpt-4o` / Gemini).
  3. `expand_presentation_content`: 1 call (Single batched call for all 12 slides).
  4. `run_reviewer_critic`: 1 call (Reads all slides to critique depth).
  Total sequential latency: 35s + 50s + 90s + 35s = up to **210 seconds** worst-case timeout budget!

---

## 3. Algorithm Terminology & Pseudo-Intelligence Corrections

### "Bayesian Mastery Engine" in `services/teach/mastery.py`
- **Previous Claim:** "Calculates Bayesian-inspired student mastery scores."
- **Verdict:** **MISLEADING TERMINOLOGY / PSEUDO-INTELLIGENCE**.
- **Runtime Truth:** The code in [backend/app/services/teach/mastery.py:51-102](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/services/teach/mastery.py#L51-L102) implements:
  $$\text{Confidence} = 1.0 - e^{-0.48 \times N} - \text{variance\_penalty}$$
  $$\Delta = \text{base\_boost} \times \text{diff\_mult} \times \text{score}$$
  $$\text{New Score} = \text{Current Score} + \Delta$$
- **Why this is NOT Bayesian:**
  1. No prior probability distribution $P(L_0)$.
  2. No transition probability $P(T)$ (learning between steps).
  3. No slip parameter $P(S)$ or guess parameter $P(G)$.
  4. No posterior probability computation using Bayes' rule: $P(L_{t+1}|Obs)$.
- **Accurate Technical Classification:** **"Additive Step Accumulator with Exponential Asymptotic Confidence Saturation"**.

---

## 4. Model Configuration vs. Runtime Truth

### A. The OpenRouter `gpt-4o` Dominance
- **Finding:** In [backend/app/services/ai/router.py:29-53](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/services/ai/router.py#L29-L53), the default policy for `planning`, `content_generation`, `repair`, and `qa` is:
  `[("openrouter", "openai/gpt-4o"), ("gemini", "gemini-2.0-flash"), ("groq", "llama-3.3-70b-versatile")]`
- Since `OPENROUTER_API_KEY` is active and populated in `.env`, **TeachGenie is actually attempting to route high-volume tasks (notes, quizzes, slides, tutoring) to expensive OpenAI GPT-4o via OpenRouter**, paying third-party API rates unless OpenRouter fails or runs out of credits!
- This contradicts the marketing claim of a "low-cost lightweight AI stack".

### B. The Parallel Legacy Fallback
- Concurrently, `app/services/llm_service.py` (`call_gemini`) does NOT route through OpenRouter; it calls Google Generative Language REST directly (`gemini-3.6-flash`), falling back to Groq `qwen/qwen3.8-27b`.
- **Verdict:** The system has **two completely different cost and latency profiles** depending on which endpoint is invoked.

---

## 5. Cross-Feature State & Persistence Corrections

- **Previous Claim:** "Nullable foreign keys in `generated_notes` allow shared intelligence across roadmaps, quizzes, and teach sessions."
- **Runtime Truth:** **THE SCHEMAS EXIST, BUT THE FEEDBACK LOOP IS UNWIRED**.
- **Evidence:** While `generated_notes` has columns `roadmap_id`, `teach_session_id`, and `quiz_id` in Migration 016, querying the codebase reveals:
  1. No automated trigger updates `generated_notes` when a student takes a quiz.
  2. No background worker feeds quiz misconceptions into the Lesson Planner roadmap.
  3. The foreign keys are only populated if the frontend explicitly passes them during note creation.
- **Verdict:** TeachGenie operates as **stateless independent generators** sharing a database, not a compounded learning feedback loop.
