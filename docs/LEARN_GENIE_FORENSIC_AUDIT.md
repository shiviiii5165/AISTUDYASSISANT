# LEARN GENIE — FORENSIC REPOSITORY AUDIT & SYSTEM RECONCILIATION

**Audit Date:** November 2026  
**Auditor Roles:** Principal EdTech Product Architect, Senior Full-Stack Engineer, AI/ML & Learning Intelligence Engineer, Application Security Engineer  
**Codebase:** LearnByGenie (`e:\AISTUDYASSISANT-main\AISTUDYASSISANT-main`)  
**Git Commit Baseline:** `f0c848c` (Branch: `main`, Remote: `https://github.com/shiviiii5165/AISTUDYASSISANT.git`)  
**Active Production Domain:** `https://learnbygenie.online` | API: `https://learnbygenie.onrender.com`  

---

## 1. Executive Summary & Verification Methodology

Learn Genie (LearnByGenie) is an enterprise AI-powered personalized learning and mastery-verification platform for Indian students in Classes 6–12, competitive exam aspirants (JEE Main, JEE Advanced, NEET-UG), and foundational learners.

Its core competitive advantage is a deterministic + AI-powered **Error-to-Mastery Learning Intelligence Engine**. The platform is strictly structured so that learning improvement is proven through authoritative, server-side verified evidence rather than inflated engagement metrics or passive content consumption.

### Audit Methodology
This forensic audit reconciles all historical documents (`README.md`, `docs/PROJECT_AUDIT.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_DESIGN.md`, `docs/FEATURE_MATRIX.md`, `docs/SECURITY_AUDIT.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/audit/*`), migrations (`001` through `031`), API routers (`backend/app/api/`), pedagogical domain engines (`backend/app/services/`), repositories, multi-agent pipelines, frontend components (`frontend/src/`), and active test suites.

Statuses are classified using the canonical taxonomy:
- **VERIFIED WORKING**: Tested end-to-end through UI/API with authoritative database persistence and verified passing test suites.
- **PARTIALLY WORKING**: Core engine/API exists and functions, but cross-module integration, full validation, or client-server binding is incomplete.
- **UI ONLY**: Visible frontend interface exists but operates on mock data, hard-coded identifiers, or disconnected state.
- **API ONLY**: Backend endpoint and service exist, but user workflow is incomplete or missing in the frontend.
- **BROKEN**: Runtime, logic, security, schema, or integration failure.
- **MISSING**: No functional implementation in codebase.
- **BLOCKED**: External service, credentials, cloud provider, or legal review prevents complete live verification.

---

## 2. Repository Layout & Architecture Verification

```
AISTUDYASSISANT-main/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entry point, CORS, RateLimiting, SecurityHeaders
│   │   ├── api/                        # 26 API router modules (auth, portals, diagnostic, mastery, etc.)
│   │   ├── agents/                     # Multi-agent RAG pipeline (Orchestrator, Librarian, Tutor, Content)
│   │   ├── core/                       # Config, dependencies (RBAC), logging, security
│   │   ├── db/                         # Supabase client instantiation with fallback
│   │   ├── models/                     # Pydantic domain models
│   │   └── services/                   # Pedagogical domain engines
│   │       ├── diagnostic/             # Stage 1: Adaptive diagnostic assessment
│   │       ├── mistake_dna/            # Stage 2: Mistake DNA & misconception classifier
│   │       ├── mastery/                # Stage 3 & 6: Mastery DAG & 5-tier transition engine
│   │       ├── practice/               # Stage 5: Adaptive practice & item selection
│   │       ├── transfer/               # Stage 6: AI-off independent transfer check
│   │       ├── step_grader/            # First-wrong-step derivation reasoning
│   │       ├── tutor/                  # Stage 4: Socratic tutor engine
│   │       ├── spaced_repetition/      # Stage 7: SM-2 review scheduler
│   │       ├── gamification/           # Effort XP Ledger & streaks
│   │       ├── portals/                # 6 Stakeholder portals service
│   │       ├── presentation/           # PPT generation pipeline
│   │       ├── lesson_planner/         # Curriculum roadmap generator
│   │       ├── quiz/                   # Quiz generation & attempt evaluator
│   │       └── live_quiz/              # Real-time multi-tenant live classroom quiz
│   ├── migrations/                     # 31 SQL migrations (001 to 031)
│   └── tests/                          # 50+ Pytest suites
├── frontend/
│   ├── index.html                      # Single page application HTML shell
│   ├── vite.config.ts                  # Vite 8 build config (React 19, TailwindCSS, proxy)
│   └── src/
│       ├── main.tsx                    # React DOM entry point
│       ├── App.tsx                     # React Router 7 v6 DOM routing & ProtectedRoute
│       ├── components/                 # AppLayout, OnboardingModal, PortalSwitcher, etc.
│       ├── lib/                        # Axios API client, domain API wrappers
│       ├── store/                      # Zustand state stores (useAuthStore.ts)
│       ├── types/                      # TypeScript definitions
│       └── pages/                      # 30+ Application pages across 6 Portals
└── docs/                               # Architectural blueprints, audits, and roadmaps
```

---

## 3. Technology Stack & Runtime Verification

| Component | Technology | Version | Verification Status | Forensic Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Runtime** | React 19, TypeScript | React 19.2, TS 5.8 | **VERIFIED WORKING** | `npm run build` succeeds (`tsc -b && vite build`) in 1.75s, 0 errors. |
| **Styling & Motion** | TailwindCSS, Framer Motion | Tailwind 3.4, FM 12 | **VERIFIED WORKING** | Design tokens, responsive containers, smooth drawer transitions active. |
| **Backend ASGI** | FastAPI, Uvicorn | FastAPI 0.115, Python 3.13 | **VERIFIED WORKING** | Async endpoint execution, strict Pydantic v2 validation. |
| **Database** | PostgreSQL / Supabase | PG 15+ / PostgREST | **PARTIALLY WORKING** | Migrations 001–031 present in SQL. Remote free-tier instance has DNS/pause risk; local fallback active. |
| **Authentication** | Supabase Auth + JWT | HS256 JWT, Bearer | **PARTIALLY WORKING** | Remote auth + local JWT decode; dev bypasses exist in `dependencies.py` requiring production hardening. |
| **AI LLM Providers** | Gemini, Groq, OpenRouter | Gemini 3.6/2.5 Flash, Groq | **VERIFIED WORKING** | Provider key rotator, fallback pipeline, circuit breakers operational. |

---

## 4. The Core Eight-Stage Error-to-Mastery Engine Forensic Status

### Stage 1: Adaptive Diagnostic Assessment
- **Status:** **VERIFIED WORKING**
- **Code:** `backend/app/services/diagnostic/` (`adaptive_engine.py`, `service.py`, `item_bank.py`)
- **API:** `POST /api/diagnostic/start`, `POST /api/diagnostic/{id}/response`, `GET /api/diagnostic/{id}/result`
- **Frontend:** `frontend/src/pages/DiagnosticPage.tsx` (`/diagnostic`)
- **Verification Evidence:** `test_adaptive_diagnostic_engine.py` passes. 31 calibrated anchor items in Algebra, Linear Equations, Motion, Optics. Probes downward when foundation is unproven; stops when confidence budget is met.

### Stage 2: Twenty-Category ErrorToken Intelligence
- **Status:** **PARTIALLY WORKING**
- **Code:** `backend/app/services/mistake_dna/` (`classifier.py`, `service.py`, `schemas.py`)
- **API:** `POST /api/mistakes/classify-and-record`, `GET /api/mistakes/summary`, `GET /api/mistakes/patterns`
- **Frontend:** `frontend/src/pages/MistakesPage.tsx` (`/mistakes`)
- **Findings:**
  - Classifies: `CONCEPTUAL`, `PROCEDURAL`, `CALCULATION`, `SIGN_OR_NOTATION`, `FORMULA_RECALL`, `MISREAD_QUESTION`, `UNIT_OR_DIMENSION`, `REASONING`, `MEMORY_RECALL`, `INCOMPLETE_RESPONSE`, `UNKNOWN`.
  - Distinguishes pattern states deterministically: `ISOLATED` (1), `RECURRING` (2–3), `PERSISTENT` (>=4), `REPAIRED` (verified by independent transfer).
  - **Remaining Defect:** Canonical taxonomy requires explicit E01–E20 identifier tokens (e.g. `E01: CONCEPTUAL_MISUNDERSTANDING` through `E20: UNCLASSIFIED_AMBIGUOUS`) to be formally exposed in the schemas, database records, and API responses.

### Stage 3: Prerequisite DAG and Root-Cause Repair
- **Status:** **VERIFIED WORKING**
- **Code:** `backend/app/services/mastery/` (`dag_engine.py`, `service.py`)
- **API:** `GET /api/mastery/graph`, `GET /api/mastery/recommendations`, `GET /api/mastery/repair-path/{skill_id}`
- **Frontend:** `frontend/src/pages/MasteryMapPage.tsx` (`/mastery`, `/mastery-map`)
- **Verification Evidence:** `test_mastery_knowledge_graph.py` passes. DAG topological sorter detects and rejects cycles. Identifies blocked concepts and computes shortest repair path from earliest unresolved prerequisite.

### Stage 4: Minimal Effective Teaching Intervention
- **Status:** **PARTIALLY WORKING**
- **Code:** `backend/app/services/tutor/` (`service.py`), `backend/app/services/notes/`, `backend/app/api/teach.py`
- **API:** `POST /api/tutor/session/start`, `POST /api/tutor/session/turn`, `POST /api/teach/session`
- **Frontend:** `frontend/src/pages/TeachMePage.tsx` (`/teach`), `frontend/src/pages/ChatPage.tsx` (`/chat`)
- **Findings:** Generates 2–5 minute focused interventions with misconception refutation and checkpoints. Socratic tutor implements pedagogical states. Needs explicit multi-modal diagram/simulation coupling when student experiences repeated failures.

### Stage 5: Adaptive Practice and Productive Struggle
- **Status:** **VERIFIED WORKING**
- **Code:** `backend/app/services/practice/` (`service.py`, `policy.py`, `item_bank.py`)
- **API:** `POST /api/practice/start`, `POST /api/practice/{id}/response`, `GET /api/practice/{id}/summary`
- **Frontend:** `frontend/src/pages/PracticePage.tsx` (`/practice`)
- **Verification Evidence:** `test_adaptive_practice_engine.py` passes. Adapts item difficulty to maintain P(Correct) target 0.65–0.78. Progressively dispenses hints (Level 1 directional, Level 2 conceptual, Level 3 step-by-step). Server-authoritative scoring.

### Stage 6: Five-Tier Mastery Verification
- **Status:** **VERIFIED WORKING**
- **Code:** `backend/app/services/mastery/` (`transition_engine.py`), `backend/app/services/transfer/` (`service.py`)
- **API:** `POST /api/transfer/start`, `POST /api/transfer/{id}/response`
- **Frontend:** `frontend/src/pages/TransferCheckPage.tsx` (`/transfer-check`), `MasteryMapPage.tsx`
- **Verification Evidence:** `test_ai_off_transfer_check.py` and `test_mastery_knowledge_graph.py` pass. State transitions:
  - Tier 0 (`NOT_ASSESSED`)
  - Tier 1 (`NEEDS_REPAIR` / diagnosed weakness)
  - Tier 2 (`DEVELOPING` / scaffolded proficiency)
  - Tier 3 (`SECURE` / independent proficiency: >=2 independent items, >=80% accuracy)
  - Tier 4 (Fresh unseen transfer without hints via Transfer Engine)
  - Tier 5 (Delayed retention via Spaced Repetition review)

### Stage 7: Spaced Repetition and Delayed Retention
- **Status:** **VERIFIED WORKING**
- **Code:** `backend/app/services/spaced_repetition/` (`service.py`, `repository.py`, `schemas.py`)
- **API:** `GET /api/spaced-repetition/queue`, `POST /api/spaced-repetition/review`, `GET /api/spaced-repetition/card/{id}`
- **Frontend:** Integrated in `frontend/src/pages/Dashboard.tsx` (`SpacedRepetitionWidget`), `PortalSwitcher.tsx`
- **Verification Evidence:** `test_institutional_portals_and_gamification.py` passes. SuperMemo SM-2 interval calculations ($EF' = \max(1.3, EF + (0.1 - (5 - q) \times (0.08 + (5 - q) \times 0.02)))$). Due reviews scheduled at Day-1, Day-6, and calculated intervals.

### Stage 8: Daily Personalized Roadmap
- **Status:** **PARTIALLY WORKING**
- **Code:** `backend/app/services/mastery/service.py` (`get_learning_recommendations`), `backend/app/services/portals/service.py`
- **Frontend:** `frontend/src/pages/Dashboard.tsx`
- **Findings:** Recommendations prioritize unmastered prerequisites and due reviews.
- **Remaining Defect:** Blueprint specifies explicit 30% spaced error repair / 50% core progression / 20% interleaved transfer weighting with a 3-task choice card.

---

## 5. Six Interconnected Portals Forensic Status

| Portal | Frontend Route | Backend Endpoint | Authorization Guard | Persistence Status | Status | Forensic Defect / Action Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Student** | `/dashboard`, `/practice`, `/diagnostic`, `/mastery-map`, `/mistakes`, `/step-check`, `/transfer-check`, `/chat` | `/api/learner/*`, `/api/diagnostic/*`, `/api/practice/*`, `/api/mastery/*`, `/api/mistakes/*` | `require_student` / authenticated | PostgreSQL (`learner_profiles`, `learner_skill_states`, etc.) | **VERIFIED WORKING** | Onboarding modal auto-trigger on first login; polish 30/50/20 daily plan widget. |
| **2. Parent** | `/parent/dashboard`, `/parent/child/:id` | `GET /api/portals/parent/dashboard`, `GET /api/portals/parent/child/{id}/progress`, `POST /api/portals/parent/link-student` | `require_parent` | PostgreSQL (`parent_student_links`) | **PARTIALLY WORKING** | Remove demo link fallback in repository; implement genuine invite-code verification handshake. |
| **3. Teacher** | `/teacher/dashboard`, `/teacher/classroom/:id`, `/lesson-planner`, `/decks`, `/quizzes`, `/quiz/:id/live` | `GET /api/portals/teacher/dashboard`, `POST /api/portals/teacher/classrooms`, `GET /api/portals/teacher/classroom/{id}/roster` | `require_teacher` | PostgreSQL (`classrooms`, `classroom_enrollments`) | **VERIFIED WORKING** | Classroom management, roster enrollment, aggregated misconception heatmaps active. |
| **4. School Admin** | `/school-admin/dashboard` | `GET /api/portals/school-admin/overview`, `POST /api/portals/school-admin/teachers` | `require_school_admin` | PostgreSQL (`schools`, `school_memberships`) | **VERIFIED WORKING** | Multi-tenant school overview, seat allocations, teacher management active. |
| **5. Content Creator** | `/creator/dashboard` | `GET /api/portals/creator/dashboard`, `POST /api/portals/creator/items` | `require_content_creator` | PostgreSQL (`diagnostic_items`, `practice_items`) | **VERIFIED WORKING** | Question bank management, calibration review workflow active. |
| **6. Super Admin** | `/admin/dashboard` | `GET /api/portals/admin/health`, `GET /api/portals/admin/users`, `POST /api/portals/admin/users/{id}/role` | `require_admin` | PostgreSQL (`user_roles`, `canary_managed_vault`) | **VERIFIED WORKING** | Platform health telemetry, LLM provider latency/cost monitoring, user role promotion. |

---

## 6. Critical Security & Privacy Findings

### SEC-01 [CRITICAL]: Unverified Dev Mock Tokens in Production
- **Location:** `backend/app/core/dependencies.py` (`MOCK_DEV_USERS`)
- **Vulnerability:** `if token in MOCK_DEV_USERS:` is evaluated before any environment check. If `ENVIRONMENT=production`, an attacker sending `Authorization: Bearer dev-admin-token` receives instantaneous `super_admin` access.
- **Remediation:** Strict quarantine: `if token in MOCK_DEV_USERS and settings.ENVIRONMENT in ("development", "test", "local"):`. In production, mock tokens must fail with 401.

### SEC-02 [CRITICAL]: Unverified JWT Signature Fallback
- **Location:** `backend/app/core/dependencies.py` (Line 176: `jwt.decode(token, options={"verify_signature": False})`)
- **Vulnerability:** When Supabase is unreachable and `SUPABASE_JWT_SECRET` is unset, the backend falls back to decoding tokens without verifying cryptographic signatures. Any user can forge a JWT with any `sub` and any `role`.
- **Remediation:** Remove `verify_signature: False` fallback completely. Fail closed: require valid cryptographic signature via Supabase Auth or `SUPABASE_JWT_SECRET` HS256 verification.

### SEC-03 [HIGH]: Parent-Child Demo Link Hard-Coding
- **Location:** `backend/app/services/portals/repository.py` (Line 50: `parent_id == "00000000-0000-0000-0000-000000000077"`)
- **Vulnerability:** Hardcoded demo linking bypasses genuine relationship verification.
- **Remediation:** Replace with an explicit invitation code / consent handshake table and cryptographic token validation.

### SEC-04 [MEDIUM]: DPDP Act, 2023 Child Data Compliance
- **Requirement:** Section 9 of the Digital Personal Data Protection Act, 2023 requires verifiable parental consent before processing personal data of children.
- **Status:** Parental consent flag exists in database schema (`parent_student_links.relationship = 'guardian'`), but explicit consent audit logs and data deletion workflows require documentation in a compliance gap register.

---

## 7. Immediate Engineering Remediation Plan

1. **Phase 1: Security & Persistence Hardening**
   - Patch `backend/app/core/dependencies.py`: Block mock tokens in production, remove unverified JWT decode fallback, enforce fail-closed cryptographic signature verification.
   - Patch `backend/app/services/portals/repository.py`: Remove demo parent-child seeding; implement invite-code verification.
2. **Phase 2: ErrorToken E01–E20 Canonical Alignment**
   - Add explicit canonical `ErrorTokenID` (E01–E20) enum and bi-directional mapper to `backend/app/services/mistake_dna/schemas.py` and `classifier.py`.
   - Update Mistake DNA API and responses to return canonical E01–E20 tokens.
3. **Phase 3: Gamification Ledger Separation & Blueprint Alignment**
   - Formalize the exact prompt XP values (+50 diagnostic, +30 error repair, +40 Tier 3, +60 Tier 4 transfer, +45 Tier 5 delayed review, +25 teach-back).
   - Enforce 10 XP/day cap on repeated easy items.
4. **Phase 4: Daily Personalized Roadmap 30/50/20 Engine**
   - Enhance recommendations service to return a structured 3-task choice card adhering to 30% spaced error repair / 50% core progression / 20% interleaved transfer.
5. **Phase 5: Automated Verification & Documentation**
   - Execute all targeted unit and integration tests.
   - Deliver `LEARN_GENIE_REQUIREMENT_TRACEABILITY.md`, `LEARN_GENIE_LEARNING_ENGINE_SPEC.md`, `LEARN_GENIE_SECURITY_REMEDIATION.md`, `LEARN_GENIE_E2E_TEST_REPORT.md`, `LEARN_GENIE_CONTENT_QUALITY_REPORT.md`.
