# TEACHGENIE VNEXT: MASTER IMPLEMENTATION ROADMAP

## 1. Executive Summary

This master roadmap establishes the engineering phasing for transitioning TeachGenie from its current dual-stack, high-cost, fragmented state into the unified **TeachGenie vNext Quality-Per-Compute Architecture**.
Execution is organized into three sequential milestones:
- **Phase 0 & 1 (Days 1–14)**: P0 FinOps Leak Plugs, Router Unification, and Dead Code Deprecation.
- **Phase 2 (Days 15–30)**: P1 Shared Knowledge Pack, Learning State Graph, and Pedagogical Slide Grammar.
- **Phase 3 (Days 31–60)**: P2 Self-Correcting Closed-Loop Classroom Engine and Empirical Exam Engine.

---

## 2. Phase 0 & 1: Stop The Leaks & Unify Compute (Days 1 – 14)

### Goals:
1. Eliminate the 96.7% cost leak caused by default routing to OpenRouter GPT-4o on trivial tasks.
2. Unify `llm_service.py` (`call_gemini`) and `ai/router.py` (`ModelRouter`) into `QualityPerComputeRouter`.
3. Deprecate dead endpoints and orphaned models.
4. Replace the 3rd/4th PPT LLM reviewer calls with deterministic layout/overflow checks.

### Detailed Workstream Tasks:

| ID | Task | Component / File | Complexity | Risk | Rollback Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Deploy `QualityPerComputeRouter` | `backend/app/services/ai/compute_router.py` | Med | Low | Feature flag `USE_QPC_ROUTER=False` falls back to `llm_service.py` |
| **P0-2** | Migrate Presentation to QPC Router | `backend/app/services/deck_generation/service.py` | Med | Med | Revert `service.py` to previous git commit |
| **P0-3** | Replace Full Deck Reviewer with Deterministic Linter | `backend/app/services/deck_generation/reviewer.py` | Low | Low | Toggle `DETERMINISTIC_PPT_REVIEW=False` |
| **P0-4** | Instrument AI Telemetry Collector | `backend/app/services/ai/telemetry.py` | Med | Low | Async fire-and-forget; zero impact on core endpoints if disabled |
| **P0-5** | Delete Orphaned V1 Deck Routes | `backend/app/api/endpoints/decks.py` | Low | Zero | Git history preserves V1 routes; none used by frontend |
| **P0-6** | Remove Dead Stage Video Endpoint | `backend/app/api/endpoints/lesson_planner.py` | Low | Zero | Endpoint already returned hardcoded 400 error |

### Milestone 1 Acceptance Gate:
- Unit test pass rate: 100% across all 237 existing regression tests.
- 12-slide presentation cost drops from **$0.0845** to **$0.0035** (95.8% reduction).
- Latency for deck generation drops from 18.4s to 6.2s.

---

## 3. Phase 2: Shared Intelligence & Pedagogical Quality (Days 15 – 30)

### Goals:
1. Implement the **TeachGenie Knowledge Pack** to eliminate duplicate reasoning across features.
2. Implement the **Relational Learning State Graph** (PostgreSQL DDL) linking Quiz, Live Quiz, and Tutor evidence.
3. Deploy the **Pedagogical Slide Grammar & Understanding Compiler** with cognitive archetypes.
4. Convert Study Notes to **Gap-Repair Notes** (Base cached notes + personalized misconception callout).

### Detailed Workstream Tasks:

| ID | Task | Component / File | Complexity | Risk | Rollback Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P1-1** | Knowledge Pack Schema & Cache Engine | `backend/app/services/knowledge_pack/` | High | Med | Fallback to standalone prompt context on cache miss |
| **P1-2** | Learning State Schema & Elo/BKT Engine | `backend/app/services/student_state/` | High | Low | If DB unavailable, sessions run statelessly |
| **P1-3** | Slide Archetype Compiler & Dual Coding Templates | `backend/app/services/deck_generation/compiler.py` | Med | Low | Fallback to standard slide layouts |
| **P1-4** | Gap-Repair Notes Synthesis | `backend/app/services/notes/generator.py` | Med | Low | Fallback to standard monolithic notes |
| **P1-5** | Misconception-Mapped Distractor Generator | `backend/app/services/quiz/quiz_service.py` | Med | Low | Fallback to standard 4-option MCQs |
| **P1-6** | Unify Socratic Tutor & DAG Prerequisite Navigation | `backend/app/agents/tutor.py` | High | Med | Retain legacy conversational prompt if DAG unmapped |

### Milestone 2 Acceptance Gate:
- Knowledge Pack cache hit rate reaches >50% on repeat curriculum requests.
- Student misconception tracking active across Quiz and Tutor.
- PPT Presentation quality score achieves >90/100 on canonical benchmark suite.

---

## 4. Phase 3: Closed-Loop Flywheel & Moat Hardening (Days 31 – 60)

### Goals:
1. Connect Live Quiz classroom response telemetry to the **Self-Correcting Lesson Planner**.
2. Deploy the **Live Teaching Control System** with real-time teacher intervention scripts.
3. Build the **Empirical Exam Readiness Engine** with historical question archetype distributions.
4. Launch automated **Video Confusion Telemetry Heatmaps**.

### Detailed Workstream Tasks:

| ID | Task | Component / File | Complexity | Risk | Rollback Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P2-1** | Dynamic Lesson Pacing & Re-planner | `backend/app/services/lesson_planner/service.py` | High | Med | Plan remains static if student evidence absent |
| **P2-2** | Live Quiz Real-Time Intervention Clustered Dispatch | `backend/app/services/live_quiz/intervention.py` | Med | Low | Retain standard poll display if clustering fails |
| **P2-3** | Exam Syllabus Coverage & Archetype Weighter | `backend/app/services/exam_predictor.py` | Med | Low | Fallback to standard practice question generator |
| **P2-4** | Video Modular SVG Scene-Graph Renderer | `backend/app/services/video_service.py` | High | Med | Retain EdgeTTS + FFmpeg audio slideshow |
| **P2-5** | End-to-End Automated QPC Evaluation Harness | `backend/tests/eval_harness/` | Med | Zero | Test suite runs asynchronously in CI/CD pipeline |

### Milestone 3 Acceptance Gate:
- Teachers report 80%+ reduction in mid-lesson planning panic.
- Student retention on concept checkpoints improves by 2.4x.
- Monthly AI compute spend stabilizes under **$0.02 per active student**.

---

## 5. Deprecation & Cleanup Matrix

| Component / File | Current Status | vNext Disposition | Rationale |
| :--- | :--- | :--- | :--- |
| `backend/app/api/endpoints/decks.py` (V1 routes) | Dormant / Orphaned | **DELETE** | Endpoints `/outline`, `/expand`, `/render` are superseded by `/generate-advanced`. |
| `backend/app/services/ai/router.py` | Redundant Provider Adapter | **MERGE & REPLACE** | Replaced by unified `QualityPerComputeRouter`. |
| `backend/app/services/llm_service.py` | Legacy Gemini Wrapper | **DEPRECATE & WRAP** | `call_gemini` routes through `QualityPerComputeRouter`. |
| `backend/app/services/teach/mastery.py` ("Bayesian") | Heuristic Exponential Step | **REPLACE** | Replaced by `StudentMasteryService` with genuine BKT/Elo probability updates. |
| Whole-deck LLM Reviewer (`reviewer.py`) | 4th LLM Call in PPT | **REPLACE WITH DETERMINISTIC** | Saves $0.024/deck; catches 100% of overflow/collision bugs deterministically. |
| Multi-Agent Debate (`multi-agent-chat`) | High-Latency Novelty | **CONSOLIDATE** | Single orchestrator with specialist prompt contexts; saves 75% tokens. |
| Stage Video Generator (`/stages/{id}/video`)| Broken (returns 400) | **DELETE** | Legacy dead route. |
