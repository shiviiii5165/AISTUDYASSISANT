# LearnByGenie — Comprehensive Feature Matrix

**Status:** Canonical Engineering Truth  
**Classification System:**
1. **Verified Working** — Tested end-to-end through UI/API, authoritative database persistence, and passing test suites.
2. **Partially Working** — Backend or UI functional but missing cross-module integration, full validation, or data persistence.
3. **UI Only** — Front-end view exists but communicates with mocks or lacks backend endpoints.
4. **API Only** — Backend endpoint exists but user workflow is incomplete.
5. **Broken** — Feature fails at runtime due to code defects, unhandled exceptions, or schema mismatches.
6. **Missing** — Not yet implemented in code or database.
7. **Blocked** — External service, credentials, data or deployment prevents verification.

---

## 1. Portals Feature Matrix

| Portal / Module | Status | Backend API Route | Frontend Route / Component | Database Tables | Notes & Defect Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Student Portal — Home Dashboard** | **Verified Working** | `/api/portals/student/roadmap`, `/api/gamification/summary`, `/api/spaced-repetition/queue` | `/dashboard` (`Dashboard.tsx`) | `learner_profiles`, `xp_ledger`, `spaced_repetition_cards` | Stage 8 Daily Roadmap (30% Spaced Repair / 50% Core / 20% Transfer) with choice cards, XP progress, SM-2 flashcard review active. |
| **Student Portal — Learner Profile** | **Verified Working** | `GET/PATCH /api/learner/profile`, `/api/learner/academic-config` | `/profile` (`LearnerProfilePage.tsx`) | `learner_profiles`, `academic_catalog` | Class 3-12 + UG, boards, streams, exam tracks, language preferences, durable writes. |
| **Student Portal — Diagnostic Assessment** | **Verified Working** | `/api/diagnostic/start`, `/api/diagnostic/{id}/response` | `/diagnostic` (`DiagnosticPage.tsx`) | `diagnostic_sessions`, `diagnostic_responses`, `diagnostic_results` | Multi-stage adaptive domain/skill assessment with prerequisite probing. |
| **Student Portal — Mastery Map** | **Verified Working** | `GET /api/mastery/graph`, `/api/mastery/summary` | `/mastery`, `/mastery-map` (`MasteryMapPage.tsx`) | `learner_skill_states`, `skill_prerequisites`, `learner_skill_evidence` | Explainable DAG visualizer, prerequisite dependencies, 5-tier mastery progression. |
| **Student Portal — Mistake DNA** | **Verified Working** | `GET /api/mistakes/summary`, `GET /api/mistakes/patterns` | `/mistakes` (`MistakesPage.tsx`) | `mistake_events`, `mistake_patterns`, `mistake_repair_events` | Classifies E01–E20 Canonical ErrorTokens; tracks isolated, recurring, persistent, repaired states. |
| **Student Portal — Adaptive Practice** | **Verified Working** | `/api/practice/start`, `/api/practice/{id}/response` | `/practice` (`PracticePage.tsx`) | `practice_sessions`, `practice_responses`, `practice_items` | Policy-driven item selection focusing on prerequisite repair and productive struggle. |
| **Student Portal — Step Check Reasoning** | **Verified Working** | `/api/step-grader/start`, `/api/step-grader/{id}/step` | `/step-check` (`StepCheckPage.tsx`) | `step_grader_sessions`, `step_grader_attempts`, `step_grader_steps` | First-wrong-step detection in math/science algebraic derivations. |
| **Student Portal — AI-Off Transfer Check**| **Verified Working** | `/api/transfer/start`, `/api/transfer/{id}/response` | `/transfer-check` (`TransferCheckPage.tsx`) | `transfer_sessions`, `transfer_responses` | Evaluates independent Tier 4 mastery without AI scaffolding. |
| **Student Portal — AI Socratic Chat** | **Verified Working** | `/api/tutor/session/turn`, `/chat/ask` | `/chat` (`ChatPage.tsx`) | `socratic_tutor_sessions`, `chat_sessions`, `chat_messages` | Socratic multi-turn dialogue with student-uploaded document grounding. |
| **Student Portal — Teach Me Lecture Mode** | **Verified Working** | `/api/teach/session` | `/teach` (`TeachMePage.tsx`) | `teach_sessions` | Interactive concept teaching with checkpoint assessments. |
| **Parent Portal — Dashboard & Digest** | **Verified Working** | `GET /api/portals/parent/dashboard` | `/parent/dashboard` (`ParentDashboard.tsx`) | `parent_student_links`, `parent_digest_settings` | Linked children summary, weekly study time, active misconception alerts. |
| **Parent Portal — Child Linkage Handshake** | **Verified Working** | `POST /api/portals/parent/link-child`, `POST /api/portals/student/generate-parent-code` | `/parent/dashboard` (Link Modal) | `parent_student_links` | Verifiable invitation code handshake (e.g. `GENIE-XXXXXX`); unverified links rejected. |
| **Parent Portal — Child Detailed Progress** | **Verified Working** | `GET /api/portals/parent/child/{id}/progress` | `/parent/child/:id` (`ChildDetailPage.tsx`) | `learner_skill_states`, `mistake_patterns` | Deep dive into child's mastery graph, quiz history, and specific error patterns. |
| **Teacher Portal — Class Management** | **Verified Working** | `GET /api/portals/teacher/dashboard`, `POST /api/portals/teacher/classrooms` | `/teacher/dashboard` (`TeacherDashboard.tsx`) | `classrooms`, `classroom_enrollments` | Cohort creation, student rosters, grade/stream assignments. |
| **Teacher Portal — Class Misconception Heatmaps** | **Verified Working** | `GET /api/portals/teacher/dashboard` | `/teacher/dashboard` | `mistake_patterns`, `classrooms` | Aggregates most common class-wide misconceptions and recommends targeted reteach strategies. |
| **Teacher Portal — Classroom Detail & Roster** | **Verified Working** | `GET /api/portals/teacher/classrooms/{id}/roster` | `/teacher/classroom/:id` (`ClassroomDetailPage.tsx`) | `classroom_enrollments`, `learner_skill_states` | Individual student roster with individual mastery status and activity dates. |
| **Teacher Portal — AI Lesson Planner** | **Verified Working** | `/api/lesson-planner/v2/plan` | `/lesson-planner` (`LessonPlannerPage.tsx`) | `course_graphs`, `learning_roadmaps`, `roadmap_stages` | Generates structured syllabus roadmaps with verified YouTube timestamps. |
| **Teacher Portal — PPT Generator** | **Verified Working** | `/api/decks/generate` | `/decks` (`TopicDeckPage.tsx`) | `topic_decks`, `ontology_cache`, `image_cache` | Produces download-ready PowerPoint decks with structured slide archetypes. |
| **Teacher Portal — Live Quiz Classroom** | **Verified Working** | `/api/live-quizzes/create`, `/live-quizzes/{id}/*` | `/quiz/:id/live`, `/live/:id` | `live_quiz_sessions`, `live_quiz_participants`, `live_quiz_responses` | Low-latency classroom assessment with anti-tamper client journals. |
| **School Admin Portal — Institution Hub** | **Verified Working** | `GET /api/portals/school-admin/overview` | `/school-admin/dashboard` (`SchoolAdminDashboard.tsx`) | `schools`, `school_memberships` | Multi-tenant school overview, teacher allocations, seat quota utilization. |
| **School Admin Portal — Teacher Management** | **Verified Working** | `POST /api/portals/school-admin/teachers` | `/school-admin/dashboard` | `school_memberships` | Faculty provisioning and department assignments. |
| **Content Creator Portal — Curricula Studio**| **Verified Working** | `GET /api/portals/creator/dashboard` | `/creator/dashboard` (`CreatorDashboard.tsx`) | `diagnostic_items`, `practice_items` | Item bank metrics, review queues, curriculum domain breakdowns. |
| **Content Creator Portal — Question Authoring** | **Verified Working** | `POST /api/portals/creator/items` | `/creator/dashboard` | `practice_items` | Question authoring with LaTeX QA, difficulty banding, and ErrorToken distractor tagging. |
| **Super Admin Portal — Operations & Health**| **Verified Working** | `GET /api/portals/super-admin/overview` | `/admin/dashboard` (`SuperAdminDashboard.tsx`) | `user_roles`, `canary_managed_vault` | Platform health, multi-provider LLM latency/error tracking, and role promotion. |

---

## 2. Core Learning Capabilities Matrix

| Capability | Status | Backend Service / Module | Frontend Component | Database Table | Notes & Defect Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Student Onboarding** | **Verified Working** | `app/api/learner.py` | `components/OnboardingModal.tsx` | `learner_profiles` | Complete profile setup for Class 6–12, boards, exam tracks, language. |
| **2. Curriculum Selection** | **Verified Working** | `app/services/learner_context/` | `pages/LearnerProfilePage.tsx` | `academic_catalog`, `learner_profiles` | Comprehensive support for CBSE, ICSE, JEE, NEET, State Boards, and UG. |
| **3. Diagnostic Assessments** | **Verified Working** | `app/services/diagnostic/` | `pages/DiagnosticPage.tsx` | `diagnostic_sessions`, `diagnostic_responses` | 31+ calibrated items, dynamic domain probing, downward prerequisite detection. |
| **4. Adaptive Question Engine** | **Verified Working** | `app/services/practice/` | `pages/PracticePage.tsx` | `practice_sessions`, `practice_items` | Policy-driven adaptation with fallback, hints (L1/L2/L3), and explanatory feedback. |
| **5. Error-to-Mastery** | **Verified Working** | `app/services/mistake_dna/` | `pages/MistakesPage.tsx` | `mistake_repair_events` | Verifies repair through subsequent independent checks; prevents false repairs. |
| **6. Misconception Classification**| **Verified Working** | `mistake_dna/classifier.py` | `pages/MistakesPage.tsx` | `mistake_patterns` | Canonical E01–E20 ErrorToken taxonomy with deterministic heuristics. |
| **7. Daily Personalized Roadmap** | **Verified Working** | `app/services/portals/service.py` | `pages/Dashboard.tsx` | `learner_skill_states`, `spaced_repetition_cards` | 30% Spaced Repair / 50% Core Progression / 20% Interleaved Transfer choice tasks. |
| **8. Learning Content & Lessons** | **Verified Working** | `app/api/notes.py`, `lessons.py` | `pages/NotesGeneratorPage.tsx` | `generated_notes`, `video_lessons` | Structured educational notes with strict LaTeX formatting and PDF download. |
| **9. Practice & Mock Examinations** | **Verified Working** | `app/api/quiz.py`, `live_quiz.py` | `pages/QuizPage.tsx` | `quizzes`, `quiz_attempts` | Full examination engine with timers, instant grading, and explanation reviews. |
| **10. AI Socratic Tutor** | **Verified Working** | `app/services/tutor/`, `pipeline.py` | `pages/ChatPage.tsx` | `socratic_tutor_sessions` | Socratic scaffolding, Quick Ask escape hatch, zero gamified hallucination. |
| **11. Mastery Tracking** | **Verified Working** | `app/services/mastery/` | `pages/MasteryMapPage.tsx` | `learner_skill_states` | Mathematically sound DAG state transitions (Tier 0 to Tier 5). |
| **12. Spaced Repetition (SM-2)** | **Verified Working** | `app/services/spaced_repetition/` | `pages/Dashboard.tsx` | `spaced_repetition_cards`, `spaced_repetition_reviews` | SuperMemo SM-2 algorithm: updates ease factor, interval days, and due review queues. |
| **13. Gamification Two-Ledger XP** | **Verified Working** | `app/services/gamification/` | `pages/Dashboard.tsx` | `xp_ledger`, `learner_streaks`, `learner_badges` | Ledger A (Effort XP) strictly separated from Ledger B (Mastery Evidence). Idempotent. |
| **14. Learning Analytics** | **Verified Working** | `app/services/portals/service.py` | `TeacherDashboard.tsx`, `LiveQuizReportPage.tsx` | `classroom_enrollments`, `live_quiz_question_stats` | Class-level live reports and student cross-skill progress analytics. |
