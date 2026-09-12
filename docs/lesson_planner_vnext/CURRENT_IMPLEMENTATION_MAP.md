# TeachGenie Lesson Planner: Current Implementation Map

**Date**: September 12, 2026  
**Audience**: Engineering & Product  
**Objective**: Comprehensive forensic inventory of existing Lesson Planner assets and classification for VNext evolution.

---

## 1. Architectural Principles

This is an **evolutionary upgrade**, NOT a greenfield rewrite:
1. **Zero Breaking Changes**: Lesson Planner V1 APIs, data models, and tests remain 100% operational.
2. **Reuse First**: Extensible components are preserved and enhanced rather than duplicated.
3. **Deterministic Superiority**: Replace LLM guesswork with rule engines, registries, and cached knowledge artifacts.
4. **Explainability**: Every stage, time budget shift, and adaptation diff must have a structured, explainable reason.

---

## 2. Component Forensic Classification

| Existing Component Path | Current Responsibility | Classification | VNext Target Architecture & Rationale |
| :--- | :--- | :--- | :--- |
| `backend/app/services/lesson_planner/schemas.py` | Core Pydantic data models for roadmaps, stages, objectives, activities, differentiation, and resources. | **EXTEND** | **Preserve all existing models** for V1 compatibility. Add VNext models: `ProductMode`, `Domain`, `Intent`, `TopicVolatility`, `KnowledgePack`, `StageArchetype`, `UniversalResourceCard`, `LearningEvidence`, `TeacherLock`, `PlanVersionDiff`. |
| `backend/app/services/lesson_planner/engine.py` (`TimeBudgetEngine`) | Arithmetic checks for stage durations and total lesson budget. | **EXTEND** | Extend with **Dynamic Time Budget Engine** (10–20% adaptive buffer reserve) and **Time Reallocation Rules** (protect mandatory curriculum & prerequisites; compress optional/recaps first on adaptation). |
| `backend/app/services/lesson_planner/engine.py` (`PrerequisiteEngine`) | Evaluates prerequisite stage IDs based on stage status (TAUGHT, MASTERED). | **EXTEND** | Evolve to **Learner-Aware Prerequisite DAG** supporting 5 node states (`MASTERED`, `LIKELY_MASTERED`, `UNKNOWN`, `WEAK`, `BLOCKING`) with 1–3 question **micro-diagnostics** for UNKNOWN states. |
| `backend/app/services/lesson_planner/engine.py` (`StateMachineEngine`) | Stage transition validation and Next Best Action computation. | **KEEP / EXTEND** | Existing transition rules are solid. Extend to handle new adaptive states (`DIAGNOSTIC_PENDING`, `REMEDIATION_IN_PROGRESS`). |
| `backend/app/services/lesson_planner/engine.py` (`ResourceRecommenderEngine`) | Static heuristic resource recommendation flags (PPT, Quiz, TeachMe, YouTube, Materials). | **REFACTOR** | Refactor into **Resource Need Detector** + **Resource Visibility Policy**. YouTube/Coding/Papers/Docs are only shown when pedagogically justified by concept type and learner level. |
| `backend/app/services/lesson_planner/engine.py` (`LessonHealthValidator`) | Deterministic 0–100 lesson health scoring engine. | **KEEP / EXTEND** | Keep core scoring rubric; extend with checks for Knowledge Pack alignment, reserve buffer validity, and prerequisite DAG integrity. |
| `backend/app/services/lesson_planner/engine.py` (`RemedialEngine`) | Generates static remedial stages inserted before failed stages. | **EXTEND** | Upgrade to **Adaptive Interventions Engine**: classifies failure causes (misconception, prerequisite gap, insufficient practice) and generates targeted remediation archetypes. |
| `backend/app/services/lesson_planner/engine.py` (`StageOperationsEngine`) | Reorder, merge, and split stage operations. | **KEEP** | Logic is fully deterministic, robust, and verified by regression test suite. |
| `backend/app/services/lesson_planner/engine.py` (`ChangeImpactEngine`) | Analyzes changed fields and marks dependent resources STALE. | **KEEP / EXTEND** | Preserve stale invalidation logic; integrate with Plan Versioning and teacher lock protections. |
| `backend/app/services/lesson_planner/generator.py` (`RoadmapGenerator`) | Prompt parser and LLM stage generator. | **REFACTOR** | Split into **Input Normalizer + Intent/Domain/Volatility Classifiers** and **Lesson Compiler**. Drive stage compilation from reusable **Knowledge Pack** rather than prompt-to-plan one-shot generation. |
| `backend/app/services/lesson_planner/youtube_recommendation.py` | Keyword video search via YouTube API v3 or DuckDuckGo Videos. | **EXTEND / REFACTOR** | Upgrade to **YouTube Learning Segment Router**: segment extraction with exact timestamps (`04:32–09:15`), hard filters, 100-point scoring formula, and diversity selection (1 Primary, 1 Alternate, 1 Demo). |
| `backend/app/services/lesson_planner/learning_materials.py` | Live hub for arXiv papers, academic refs, and documentation via DDGS. | **EXTEND / REFACTOR** | Refactor into dedicated engines: **Academic Evidence Engine** (paper types, Q1–Q4 journals, A*/A conferences, 6 sort tabs, safety gates), **Coding Resource Engine** (GFG vs LeetCode), and **Official Docs Engine**. |
| `backend/app/services/lesson_planner/adapters.py` | Adapters for PPT, Quiz, TeachMe, Notes, Video. | **EXTEND** | Connect active adapters (PPT, Quiz, TeachMe) directly to the **Knowledge Pack** so downstream tools do not independently reinvent topic structure. Enforce lazy generation. |
| `backend/app/services/lesson_planner/course_intelligence.py` | Concept graph building, cycle detection, semester planning. | **KEEP** | Well-architected graph cycle breaker and semester scheduler. Keep as-is. |
| `backend/app/api/lesson_planner.py` | FastAPI router with V1 endpoints (`/generate`, `/{id}`, `/stages/...`). | **KEEP** | Maintain 100% operational for existing frontend and client consumers until V2 reaches production parity. |
| `backend/app/api/lesson_planner_v2.py` | VNext API router for Evidence-Adaptive Teaching OS. | **NEW** | Mounts `/api/lesson-planner/v2/...` endpoints (`/plan`, `/stages`, `/resources`, `/evidence`, `/recompile`, `/locks`, `/why`). |
| `backend/migrations/004_lesson_planner.sql` | Supabase tables: `learning_roadmaps`, `roadmap_stages`, `roadmap_events`, `roadmap_resources`. | **KEEP** | Production schema intact. |
| `backend/migrations/017_lesson_planner_vnext.sql` | VNext relational tables for Knowledge Packs, evidence, misconceptions, locks, versions. | **NEW** | Introduces `knowledge_packs`, `curriculum_objectives`, `resource_sources`, `learning_evidence`, `misconception_catalog`, `student_misconceptions`, `lesson_adaptations`, `teacher_locks`, `lesson_plan_versions`. |
| `backend/app/core/config.py` | Application settings and feature flags. | **EXTEND** | Add `LESSON_PLANNER_VNEXT_ENABLED: bool = True` and feature toggles for adaptive engine and scholarly discovery. |
| `frontend/src/pages/LessonPlannerPage.tsx` | Main UI for lesson planning, stage editing, and resource viewing. | **EXTEND** | Add Product Mode selector, VNext Stage Cards ("Why now?", pedagogy, checkpoints, locks), Adaptation Alert Banner (>20% misconception diff), and Universal Resource Cards. |

---

## 3. Subsystem Duplication Guardrails

To adhere to Non-Negotiable Principle #2 ("Do not rewrite working logic without proving that replacement is necessary"):
1. **Do NOT build a duplicate state machine**: Extend `StateMachineEngine` and `StageStatus`.
2. **Do NOT build duplicate timing logic**: Extend `TimeBudgetEngine` with the adaptive reserve buffer.
3. **Do NOT build duplicate stage manipulation**: Reuse `StageOperationsEngine` for split, merge, and reorder.
4. **Do NOT bypass existing ModelRouter**: Route all semantic operations through `app.services.ai.router`.
5. **Do NOT invent fake scholarly data**: Enforce verified venue extraction and reject simulated papers.
