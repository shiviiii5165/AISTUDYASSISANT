# LearnByGenie — Comprehensive Repository & Engineering Audit

**Audit Date:** November 2026  
**Auditor Roles:** Principal Software Architect, Senior Full-Stack Engineer, Database Architect, AI Engineer, Application Security Engineer  
**Codebase:** LearnByGenie (`e:\AISTUDYASSISANT-main\AISTUDYASSISANT-main`)  
**Active Production Domain:** `https://learnbygenie.online` | API: `https://learnbygenie.onrender.com`  

---

## 1. Executive Summary

LearnByGenie (formerly TeachGenie) is an enterprise-grade AI study assistant and smart learning platform. The codebase contains sophisticated pedagogical intelligence, multi-agent AI pipelines, and deep domain algorithms. However, previous development cycles focused heavily on student-facing diagnostic, mastery graph, mistake classification, step grading, and presentation modules, while omitting foundational institutional primitives (Parent, School Admin, unified Content Creator, and Super Admin portals) and gamification/spaced-repetition ledgers.

This audit provides a complete, forensic baseline of the existing codebase, verifying what works, what is partially integrated, what is UI-only, what is broken, and what is missing.

---

## 2. Codebase Structure & Entry Points

```
AISTUDYASSISANT-main/
├── backend/
│   ├── app/
│   │   ├── main.py                     # Primary FastAPI application entry point
│   │   ├── api/                        # 26 API router modules (auth, pdfs, chat, tutor, diagnostic, etc.)
│   │   ├── agents/                     # Multi-agent pipeline (Orchestrator, Librarian, Tutor, Content Creator)
│   │   ├── core/                       # Config, dependencies (auth), logging, security & rate limiting
│   │   ├── db/                         # Supabase client instantiation
│   │   ├── models/                     # Pydantic & DB entity models
│   │   └── services/                   # Core business logic & pedagogical domain engines
│   │       ├── ai/                     # LLM providers (Gemini, Groq, OpenRouter), circuit breakers
│   │       ├── diagnostic/             # Feature 2: Adaptive diagnostic assessment engine
│   │       ├── learner_context/        # Feature 1: Canonical learner profile & academic catalog
│   │       ├── mastery/                # Feature 3: Mastery knowledge graph & prerequisite DAG
│   │       ├── mistake_dna/            # Feature 5: Mistake DNA classification & repair engine
│   │       ├── practice/               # Feature 6: Adaptive practice engine & item selection
│   │       ├── step_grader/            # Feature 8: First-wrong-step detection & reasoning engine
│   │       ├── transfer/               # Feature 7: AI-off independent transfer check engine
│   │       ├── tutor/                  # Feature 4: Socratic tutor engine with pedagogical states
│   │       ├── presentation/           # PPT generation pipeline & layout compiler
│   │       ├── lesson_planner/         # Curriculum roadmap generator & YouTube aligner
│   │       ├── quiz/                   # Quiz generator & attempt evaluator
│   │       └── live_quiz/              # Real-time multi-tenant live classroom quiz
│   ├── migrations/                     # 29 SQL migrations (001 to 029)
│   ├── scripts/                        # Production certification & verification harnesses
│   └── tests/                          # 50+ Pytest suites (unit, integration, regression, smoke)
├── frontend/
│   ├── index.html                      # Single page application HTML shell
│   ├── vite.config.ts                  # Vite build configuration (React 19, TailwindCSS, proxy)
│   ├── package.json                    # Frontend dependencies
│   └── src/
│       ├── main.tsx                    # React DOM entry point
│       ├── App.tsx                     # React Router 7 v6 DOM routing & ProtectedRoute
│       ├── components/                 # Reusable UI components (AppLayout, DynamicText, OnboardingModal, etc.)
│       ├── lib/                        # Axios API client, Supabase client, domain API wrappers
│       ├── store/                      # Zustand state stores (useAuthStore.ts, useSidebarCollapse.ts)
│       ├── types/                      # TypeScript definitions for learner, diagnostic, mastery, mistakes, etc.
│       └── pages/                      # 26+ Application pages across Study, Teach, SEO, Legal, and Blog
└── docs/                               # Architectural blueprints, prior verification audits, and specs
```

---

## 3. Technology Stack Analysis

| Layer | Technologies | Status / Observations |
| :--- | :--- | :--- |
| **Frontend Framework** | React 19, TypeScript, Vite 8, TailwindCSS | Compiles cleanly (`tsc -b && vite build`). Fast bundle execution. |
| **Frontend State & Nav**| Zustand, React Router 7 (v6 compatibility), Lucide Icons | Clean architecture, centralized auth store, responsive layouts. |
| **Backend Framework** | FastAPI (Python 3.11/3.13), Pydantic v2, Uvicorn | Clean ASGI async pipeline, strict schema validation. |
| **Database & Auth** | Supabase PostgreSQL, Supabase Auth (GoTrue), PostgREST | 29 migrations in SQL. Remote free-tier instance has DNS issues; local fallback required. |
| **AI / LLM Providers** | Google Gemini (3.6-flash, 2.5-flash), Groq (gpt-oss-120b, Qwen 3.8-27b), OpenRouter (gpt-4o) | Live API keys confirmed operational. Resilient circuit breaker & key rotator implemented. |
| **Client Persistence** | IndexedDB, LocalStorage | Write-ahead journaling for Live Quiz participants; dev auth flag support. |

---

## 4. Portals Audit Baseline

Learn Genie is required to deliver six interconnected portals. Here is the exact status of each portal in the existing codebase:

### 1. Student Portal (`/dashboard`, `/practice`, `/diagnostic`, `/mastery-map`, `/mistakes`, `/step-check`, `/transfer-check`, `/chat`, `/notes`, `/teach`, `/library`)
- **Status:** **Partially Working / Advanced**
- **Existing:** Comprehensive student capabilities exist across diagnostic assessments, mastery tracking, mistake DNA analysis, step check reasoning, and adaptive practice.
- **Defects / Gaps:** Onboarding modal is untracked and disconnected from initial login flow; no gamification/XP progression display; study streak is static; lacks centralized learning recommendations panel based on mastery DAG.

### 2. Parent Portal (`/parent/*`)
- **Status:** **Missing (0% complete)**
- **Existing:** No frontend pages, no API routes, no backend models, and no database tables exist for parent-student linking, weekly performance summaries, or mastery progress digests.

### 3. Teacher Portal (`/teacher/*`, `/lesson-planner`, `/decks`, `/quizzes`, `/join`, `/video`)
- **Status:** **Partially Working (Fragmented)**
- **Existing:** High-powered teacher tools exist in isolation: AI Lesson Planner (`/lesson-planner`), PPT Generator (`/decks`), Video Generator (`/video`), Quiz Generator (`/quizzes`), and Live Quiz Classroom Host (`/quiz/:id/live`).
- **Defects / Gaps:** No consolidated Teacher Portal dashboard; no classroom/batch management; no student roster assignment flow; cannot view collective mastery maps or mistake DNA trends for a specific class.

### 4. School Administrator Portal (`/school-admin/*`)
- **Status:** **Missing (0% complete)**
- **Existing:** No school organization model, no department/grade management, no teacher allocation, and no school-wide academic telemetry.

### 5. Content Creator Portal (`/creator/*`)
- **Status:** **Partially Working (Fragmented)**
- **Existing:** Content generation engines exist in backend (`content_creator.py`, `notes_generator.py`, `presentation/`, `video/`).
- **Defects / Gaps:** No dedicated Creator Portal dashboard to curate curriculum objectives, manage question banks, review AI-generated lesson templates, or publish official study modules.

### 6. Super Administrator Portal (`/admin/*`)
- **Status:** **Missing / Stub Only**
- **Existing:** Backend has a simple stub `get_current_admin_user` in `dependencies.py` requiring `role in ["admin", "super_admin"]`. No UI exists, no user management, no LLM cost monitoring, no system health telemetry.

---

## 5. Core Learning Capabilities Status

| Capability | Backend Engine | Frontend Interface | Database Persistence | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **1. Student Onboarding** | `app/api/learner.py` | `OnboardingModal.tsx` (uncommitted) | `learner_profiles` table | **Partially Working** |
| **2. Curriculum Selection** | `academic_catalog.py` | `LearnerProfilePage.tsx` | `academic_catalog` table | **Working** |
| **3. Diagnostic Assessments** | `app/services/diagnostic/` | `DiagnosticPage.tsx` | 7 tables (022 migration) | **Working** |
| **4. Adaptive Question Engine** | `app/services/practice/` | `PracticePage.tsx` | 4 tables (026 migration) | **Working** |
| **5. Error-to-Mastery** | `app/services/mistake_dna/` | `MistakesPage.tsx` | 3 tables (025 migration) | **Working** |
| **6. Misconception Classification**| `mistake_dna/classifier.py` | `MistakesPage.tsx` | `mistake_patterns` table | **Working** |
| **7. Personalized Study Plans** | `app/api/lesson_planner_v2.py`| `LessonPlannerPage.tsx` | 6 tables (017-018 migration)| **Partially Working** |
| **8. Learning Content & Lessons** | `app/api/lessons.py`, `notes.py` | `NotesGeneratorPage.tsx`, `TopicDeckPage.tsx` | `video_lessons`, `topic_decks`, `generated_notes` | **Working** |
| **9. Practice & Mock Examinations** | `app/api/quiz.py`, `live_quiz.py`| `QuizPage.tsx`, `LiveQuizHostPage.tsx` | `quizzes`, `quiz_questions`, `quiz_attempts` | **Working** |
| **10. AI Socratic Tutor** | `app/services/tutor/`, `pipeline.py`| `ChatPage.tsx`, `TeachMePage.tsx` | `socratic_tutor_sessions` | **Working** |
| **11. Mastery Tracking** | `app/services/mastery/` | `MasteryMapPage.tsx` | `learner_skill_states`, `learner_skill_evidence` | **Working** |
| **12. Spaced Repetition** | None | None | None | **Missing** |
| **13. Gamification & XP Ledger** | None | Static "Streak 1" in Dashboard | None | **Missing** |
| **14. Learning Analytics** | Fragmented in quiz/diagnostic | Fragmented across pages | `live_quiz_question_stats`, `quiz_scores` | **Partially Working** |

---

## 6. Critical Defects & Systemic Risks Identified

### Bug 1: Supabase Free-Tier DNS Failure & Hard Dependency
- **Symptom:** Remote project `https://inszhwwwadjifuheyxhv.supabase.co` does not resolve via DNS (`[Errno 11001] getaddrinfo failed`).
- **Impact:** Backend profile updates, auth token verification, and DB operations fail with 503 Service Unavailable or 401 Unauthorized unless offline fallback resilience is active.
- **Remediation:** Implement local SQLite / in-memory hybrid repository fallback and offline token validation so tests and local development run reliably without external cloud network dependencies.

### Bug 2: Missing Role-Based Authorization Guards
- **Symptom:** Only `get_current_admin_user` exists. No role guard verifies student, parent, teacher, school_admin, content_creator.
- **Impact:** Any authenticated user can access any registered endpoint or route, violating multi-tenant boundaries.
- **Remediation:** Create a generic `require_role(["teacher", "school_admin", ...])` FastAPI dependency and enforce role validation on both client and server.

### Bug 3: Absence of Portals 2, 4, 6 and Incomplete Portals 3, 5
- **Symptom:** Only student views and loose teacher tools exist; Parent, School Admin, and Super Admin do not exist.
- **Impact:** System fails enterprise multi-stakeholder operational requirements.
- **Remediation:** Build dedicated portal layouts, role-based dashboards, and interconnecting APIs for all 6 target portals.

### Bug 4: Missing Spaced Repetition Engine
- **Symptom:** Spaced repetition is listed as a core requirement but has zero backend models, zero scheduler algorithms (SM-2/Leitner), and no frontend review queues.
- **Remediation:** Implement `SpacedRepetitionService` with SuperMemo SM-2 interval calculations and daily flashcard/concept review endpoints.

### Bug 5: Missing Gamification & XP Ledger
- **Symptom:** No XP ledger table exists; Dashboard streak counter is hardcoded or tied to static document counts.
- **Impact:** Student engagement and gamified motivation loops are non-functional.
- **Remediation:** Implement an append-only `xp_ledger` table with idempotent reward triggers (e.g. diagnostic completion, streak maintenance, step check success, mistake repair).

