# TeachGenie Lesson Planner: System Baseline

**Date**: September 12, 2026  
**Commit/State**: Prior to VNext Evolution (LPV2-00 Baseline)  
**Environment**: Windows, Python 3.13.6, Vite 8.2.2, Pytest 9.1.1, Node.js

---

## 1. Test Suite Verification

### A. Dedicated Lesson Planner Test Suite
Command: `pytest backend/tests/test_lesson_planner.py -v`

| Metric | Recorded Value |
| :--- | :--- |
| **Tests Collected** | 14 |
| **Tests Passed** | 14 (100%) |
| **Tests Failed** | 0 |
| **Duration** | 15.13s |
| **Warnings** | 3 (DeprecationWarning: `datetime.utcnow()` scheduled for removal) |

**Individual Test Breakdown**:
- `test_prerequisite_engine`: PASSED
- `test_lesson_timing`: PASSED
- `test_lesson_health`: PASSED
- `test_adapters`: PASSED
- `test_course_graph_cycle_detection`: PASSED
- `test_stage_operations`: PASSED
- `test_change_impact`: PASSED
- `test_semester_planner`: PASSED
- `test_stage_action_contract`: PASSED
- `test_resource_recommender_no_video_or_notes`: PASSED
- `test_youtube_recommendation_service_live`: PASSED
- `test_extra_learning_materials_service_live`: PASSED
- `test_disabled_feature_flag_override`: PASSED
- `test_study_pack_omits_notes`: PASSED

### B. Extended Planning & Flow Intelligence Test Suite
Command: `pytest backend/tests/test_lesson_planner.py backend/tests/test_learning_flow_intelligence.py -q`

| Metric | Recorded Value |
| :--- | :--- |
| **Tests Collected** | 36 |
| **Tests Passed** | 36 (100%) |
| **Tests Failed** | 0 |
| **Duration** | 24.79s |

---

## 2. Frontend Compilation & Build Status

### A. TypeScript Verification
Command: `npx tsc -b` (in `frontend/`)
- **Status**: PASSED
- **Exit Code**: 0
- **Type Errors**: 0

### B. Production Bundle Build
Command: `npm run build` (`tsc -b && vite build`)
- **Status**: PASSED
- **Exit Code**: 0
- **Build Duration**: 27.18s
- **Transformed Modules**: 2,726
- **Artifacts Generated**:
  - `dist/index.html` (2.59 kB)
  - `dist/assets/index-BfnfJb5Y.css` (93.79 kB)
  - `dist/assets/index-AEpV3CU6.js` (1,433.32 kB)

---

## 3. Operational Performance & Quality Sample

Measurements conducted via real live execution for topic: `DBMS Normalization` (Level: `B.Tech`):

### A. Generation Latency & Compute
- **Prompt Intake & Parsing Latency**: ~0.8s (1 LLM call to `planning` task)
- **Draft Roadmap Compilation Latency**: ~5.2s – 7.0s (1 LLM call producing 3–6 stages)
- **Total Plan Latency**: ~6.0s – 7.8s
- **LLM Calls per Lesson**: 2 calls (1 parse + 1 generate)
- **Estimated Cost per Lesson**: ~$0.015 – $0.025
- **Cache Hit Rate**: 0% (every request runs full generation from scratch)

### B. Live YouTube Recommendation Quality Sample
- **Search Latency**: 0.74s
- **Results Returned**: 3 items
- **Top Result**:
  - *Title*: `Lec-24: Introduction to Normalization | Insertion, Deletion & Updation Anomaly`
  - *URL*: `https://www.youtube.com/watch?v=5GDTIUVlHB8`
  - *Relevance Score*: 0.90 (static placeholder score)
- **Identified Gaps for VNext**:
  - Recommends entire video length without timestamp segments (`start_time` / `end_time`).
  - No /100 score breakdown (missing level fit, transcript analysis, quality score).
  - No diversity constraints (no distinct primary vs alternative vs demo labeling).

### C. Live Extra Learning Materials Quality Sample
- **Search Latency**: 5.37s
- **Category Counts**:
  - Academic References: 2 (e.g., `Database normalization - Wikipedia`)
  - Research Papers: 3 (e.g., `Exploring Database Normalization Effects on SQL Generation` via arXiv)
  - Official Documentation: 1
- **Identified Gaps for VNext**:
  - No peer-reviewed journal quartile (Q1–Q4) or conference ranking (A*, A, B, C) labeling.
  - Naive DDGS string queries occasionally fail with "No results found".
  - Missing safety gates for retractions, expressions of concern, and preprint badges.
  - Missing 6-view sorting tabs (`BEST OVERALL`, `LATEST`, `MOST INFLUENTIAL`, `VENUE QUALITY`, `SEMINAL`, `REVIEWS`).
  - Missing Coding Resource engine (GFG conceptual vs LeetCode problem solving).

---

## 4. Acceptance Gates for VNext Phases

| Phase | Milestone Name | Acceptance Gate Criteria |
| :--- | :--- | :--- |
| **LPV2-00** | Baseline & Forensics | `CURRENT_IMPLEMENTATION_MAP.md` and `BASELINE.md` committed; 100% existing tests pass. |
| **LPV2-01** | Database Schema & Models | Migration `017_lesson_planner_vnext.sql` applied; VNext schemas defined without breaking V1 models. |
| **LPV2-02** | Context Classifiers | Intent (11 canonical), Domain, and Volatility classifiers deterministic with test coverage >=95%. |
| **LPV2-03** | Knowledge Pack & Cache | Knowledge Pack data model, repository, and cache layer functional; cache hits deliver near-zero LLM cost. |
| **LPV2-04** | Curriculum Resolver | Resolves canonical objectives via priority ladder (uploaded -> official -> pack -> LLM). |
| **LPV2-05** | Pedagogy Policy Engine | Maps 7 concept types to stage archetypes with active teacher/student actions. |
| **LPV2-06** | Dynamic Time Budget | Proportional budgeting with 10–20% adaptive reserve; reallocation rules protect mandatory objectives. |
| **LPV2-07** | Lesson Compiler | Assembles complete lesson plan from Knowledge Pack + Pedagogy + Time Budget. |
| **LPV2-08** | Resource Source Registry | Central registry for resource sources with domain routing and visibility rules. |
| **LPV2-09** | YouTube Segment Router | Timestamped segments (`04:32–09:15`), hard filters, 100-point scoring formula, max 3 diverse items. |
| **LPV2-10** | Academic Evidence Engine | Paper types, Q1–Q4 journal venues, A*/A conference rankings, 6 sort tabs, retraction gates. |
| **LPV2-11** | Coding & Docs Engines | Difficulty progression (Beginner -> Advanced), GFG vs LeetCode, official documentation priority. |
| **LPV2-12** | Universal Resource Cards | Complete card schema with transparent /100 score breakdown and accessibility metadata. |
| **LPV2-13** | Adaptive Engine & Recompiler | Diagnostic checkpoints, >20% misconception rule, diff preview (`BEFORE` vs `AFTER`), teacher locks. |
| **LPV2-14** | VNext API & Frontend UI | `/api/lesson-planner/v2/...` endpoints active; Mode selector, Stage cards, and Adaptation alerts in UI. |
