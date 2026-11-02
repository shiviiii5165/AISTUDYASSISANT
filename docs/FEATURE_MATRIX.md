# LearnByGenie — Comprehensive Feature Matrix

**Status:** Canonical Engineering Truth  
**Classification System:**
1. **Working** — End-to-end verified with real backend APIs, database persistence, and UI.
2. **Partially working** — Backend or UI functional but missing cross-module integration, full validation, or data persistence.
3. **UI only** — Front-end view exists but communicates with mocks or lacks backend endpoints.
4. **Broken** — Feature fails at runtime due to code defects, unhandled exceptions, or schema mismatches.
5. **Missing** — Not yet implemented in code or database.

---

## 1. Portals Feature Matrix

| Portal / Module | Status | Backend API Route | Frontend Route / Component | Database Tables | Notes & Defect Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Student Portal — Home Dashboard** | **Partially working** | `/pdfs/list`, `/api/learner/context` | `/dashboard` (`Dashboard.tsx`) | `learner_profiles`, `pdfs` | Document stats and learner context work; study streak is static; lacks centralized learning recommendations panel. |
| **Student Portal — Learner Profile** | **Working** | `GET/PATCH /api/learner/profile`, `/api/learner/academic-config` | `/profile` (`LearnerProfilePage.tsx`) | `learner_profiles`, `academic_catalog` | Class 3-12 + UG, boards, streams, exam tracks, language preferences, durable writes. |
| **Student Portal — Diagnostic Assessment** | **Working** | `/api/diagnostic/start`, `/api/diagnostic/{id}/response` | `/diagnostic` (`DiagnosticPage.tsx`) | `diagnostic_sessions`, `diagnostic_responses`, `diagnostic_results` | Multi-stage adaptive domain/skill assessment with prerequisite probing. |
| **Student Portal — Mastery Map** | **Working** | `GET /api/mastery/graph`, `/api/mastery/summary` | `/mastery`, `/mastery-map` (`MasteryMapPage.tsx`) | `learner_skill_states`, `skill_prerequisites`, `learner_skill_evidence` | Explainable DAG visualizer, prerequisite dependencies, mastery progression. |
| **Student Portal — Mistake DNA** | **Working** | `GET /api/mistakes/summary`, `GET /api/mistakes/patterns` | `/mistakes` (`MistakesPage.tsx`) | `mistake_events`, `mistake_patterns`, `mistake_repair_events` | Classifies Sign, Arithmetic, Concept, Formula errors; tracks isolated/recurring/persistent. |
| **Student Portal — Adaptive Practice** | **Working** | `/api/practice/start`, `/api/practice/{id}/response` | `/practice` (`PracticePage.tsx`) | `practice_sessions`, `practice_responses`, `practice_items` | Policy-driven item selection focusing on prerequisite repair and mistake DNA repair. |
| **Student Portal — Step Check Reasoning** | **Working** | `/api/step-grader/start`, `/api/step-grader/{id}/step` | `/step-check` (`StepCheckPage.tsx`) | `step_grader_sessions`, `step_grader_attempts`, `step_grader_steps` | First-wrong-step detection in math/science algebraic derivations. |
| **Student Portal — AI-Off Transfer Check**| **Working** | `/api/transfer/start`, `/api/transfer/{id}/response` | `/transfer-check` (`TransferCheckPage.tsx`) | `transfer_sessions`, `transfer_responses` | Evaluates independent mastery without AI scaffolding. |
| **Student Portal — AI Socratic Chat** | **Working** | `/api/tutor/session/turn`, `/chat/ask` | `/chat` (`ChatPage.tsx`) | `socratic_tutor_sessions`, `chat_sessions`, `chat_messages` | Socratic multi-turn dialogue with student-uploaded document grounding. |
| **Student Portal — Teach Me Lecture Mode** | **Working** | `/api/teach/session` | `/teach` (`TeachMePage.tsx`) | `teach_sessions` | Interactive concept teaching with checkpoint assessments. |
| **Parent Portal — Dashboard** | **Missing** | None | None | None | Needs `/parent/dashboard`, child linkage, and weekly mastery digest. |
| **Parent Portal — Child Linkage & Approvals**| **Missing** | None | None | None | Needs invite code verification and guardian linking API. |
| **Parent Portal — Mistake DNA Alerts** | **Missing** | None | None | None | Needs alerts when a child develops persistent error patterns. |
| **Teacher Portal — Class Management** | **Missing** | None | None | None | Needs `/teacher/classes` and student roster enrollment. |
| **Teacher Portal — Aggregated Analytics** | **Missing** | None | None | None | Needs class-wide mastery heatmaps and common mistake detection. |
| **Teacher Portal — AI Lesson Planner** | **Working** | `/api/lesson-planner/v2/plan` | `/lesson-planner` (`LessonPlannerPage.tsx`) | `course_graphs`, `learning_roadmaps`, `roadmap_stages` | Generates structured syllabus roadmaps with verified YouTube timestamps. |
| **Teacher Portal — PPT Generator** | **Working** | `/api/decks/generate` | `/decks` (`TopicDeckPage.tsx`) | `topic_decks`, `ontology_cache`, `image_cache` | Produces download-ready PowerPoint decks with structured slide archetypes. |
| **Teacher Portal — Live Quiz Classroom** | **Working** | `/api/live-quizzes/create`, `/live-quizzes/{id}/*` | `/quiz/:id/live`, `/live/:id` | `live_quiz_sessions`, `live_quiz_participants`, `live_quiz_responses` | Low-latency classroom assessment with anti-tamper client journals. |
| **School Admin Portal — Institution Hub** | **Missing** | None | None | None | Needs `/school-admin/dashboard`, teacher allocations, license management. |
| **School Admin Portal — School Analytics** | **Missing** | None | None | None | Needs school-wide pass rates, mastery trends, and department breakdown. |
| **Content Creator Portal — Curricula Studio**| **Partially working** | `/api/content-creator/generate` | None (fragmented in `/decks`, `/notes`) | `knowledge_packs`, `curriculum_objectives` | Lacks dedicated portal dashboard to review, edit, and publish curricula. |
| **Content Creator Portal — Question Bank** | **Partially working** | Internal item banks | None | `diagnostic_items`, `practice_items` | Items are code-defined; no UI to author/calibrate new items. |
| **Super Admin Portal — Operations & Health**| **UI only / Missing** | `/api/health` | None | `canary_managed_vault` | Backend has `get_current_admin_user` stub; lacks admin dashboard and telemetry UI. |

---

## 2. Core Learning Capabilities Matrix

| Capability | Status | Backend Service / Module | Frontend Component | Database Table | Notes & Defect Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Student Onboarding** | **Partially working** | `app/api/learner.py` | `components/OnboardingModal.tsx` | `learner_profiles` | Component exists untracked; needs automatic modal trigger when `onboarding_completed == false`. |
| **2. Curriculum Selection** | **Working** | `app/services/learner_context/` | `pages/LearnerProfilePage.tsx` | `academic_catalog`, `learner_profiles` | Comprehensive support for CBSE, ICSE, JEE, NEET, State Boards, and UG. |
| **3. Diagnostic Assessments** | **Working** | `app/services/diagnostic/` | `pages/DiagnosticPage.tsx` | `diagnostic_sessions`, `diagnostic_responses` | 31+ calibrated items, dynamic domain probing, prerequisite detection. |
| **4. Adaptive Question Engine** | **Working** | `app/services/practice/` | `pages/PracticePage.tsx` | `practice_sessions`, `practice_items` | Policy-driven adaptation with fallback, hints, and explanatory feedback. |
| **5. Error-to-Mastery** | **Working** | `app/services/mistake_dna/` | `pages/MistakesPage.tsx` | `mistake_repair_events` | Verifies repair through subsequent independent checks; prevents false repairs. |
| **6. Misconception Classification**| **Working** | `mistake_dna/classifier.py` | `pages/MistakesPage.tsx` | `mistake_patterns` | Deterministic categorization: Sign, Arithmetic Slip, Unit/Dimension, Formula Recall, Misread Question. |
| **7. Personalized Study Plans** | **Partially working** | `app/api/lesson_planner_v2.py` | `pages/LessonPlannerPage.tsx` | `learning_roadmaps` | Generates roadmaps; needs automated synchronization with active Mastery Graph gaps. |
| **8. Learning Content & Lessons** | **Working** | `app/api/notes.py`, `lessons.py` | `pages/NotesGeneratorPage.tsx` | `generated_notes`, `video_lessons` | Structured educational notes with strict LaTeX formatting and PDF download. |
| **9. Practice & Mock Examinations** | **Working** | `app/api/quiz.py`, `live_quiz.py` | `pages/QuizPage.tsx` | `quizzes`, `quiz_attempts` | Full examination engine with timers, instant grading, and explanation reviews. |
| **10. AI Socratic Tutor** | **Working** | `app/services/tutor/`, `pipeline.py` | `pages/ChatPage.tsx` | `socratic_tutor_sessions` | Socratic scaffolding, Quick Ask escape hatch, zero gamified hallucination. |
| **11. Mastery Tracking** | **Working** | `app/services/mastery/` | `pages/MasteryMapPage.tsx` | `learner_skill_states` | Mathematically sound DAG state transitions (`NOT_STARTED` -> `IN_PROGRESS` -> `MASTERED` / `NEEDS_REPAIR`). |
| **12. Spaced Repetition** | **Missing** | None | None | None | Needs SuperMemo SM-2 algorithm, card review queue, and ease factor updates. |
| **13. Gamification & XP Ledger** | **Missing** | None | None | None | Needs append-only `xp_ledger` table, streak counter, and achievement badges. |
| **14. Learning Analytics** | **Partially working** | Fragmented in live quiz/stats | `LiveQuizReportPage.tsx` | `live_quiz_question_stats` | Class-level live reports work; lacks unified student cross-skill progress analytics. |

