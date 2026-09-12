# TEACHGENIE AUDIT ERRATA & FACTUAL CORRECTIONS

## Executive Summary

To maintain engineering integrity, every discrepancy, invalid assumption, and inaccurate claim from previous audit reports is cataloged and corrected below against the actual repository code and live API executions.

---

## Complete Errata Table

| # | Topic / Area | Previous Report Claim | Verified Production Reality | Severity | Corrective Action |
| :- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Frontend Stack** | "Next.js App Router + TypeScript + Tailwind" | **React 19 + Vite 8 + React Router DOM 7 + Tailwind CSS 3.4.19**. There is no Next.js in the repository. | **HIGH** | Updated all architectural documentation; confirmed SPA client-side routing. |
| **2** | **Test Suite Count** | "237 tests pass in 248 seconds" | Pytest collects **543 items** across `backend/tests/`. 237 was an older or partial test run. | **MEDIUM**| Captured live test execution in `TEST_RUN_RAW.txt`. |
| **3** | **Groq Active Models** | Recommended `llama-3.3-70b-versatile` & `llama-3.1-8b-instant` | Live API test returned **404 Model Not Found** for `llama-3.3-70b-versatile`. Active models are **`qwen/qwen3.8-27b`** and **`openai/gpt-oss-120b`**. | **CRITICAL**| Purged stale LLaMA references; updated candidate pool to active production models. |
| **4** | **Presentation Filepath**| Cited `backend/app/services/deck_generation/` | Path does not exist. Actual path is **`backend/app/services/presentation/`**. | **MEDIUM**| Fixed all file links and symbol references. |
| **5** | **Video Service Filepath**| Cited `backend/app/services/video_service.py` | Path does not exist. Actual path is the **`backend/app/services/video/`** modular package. | **MEDIUM**| Fixed all file links and symbol references. |
| **6** | **Notes Generator Route**| Cited `/api/notes/generate` | Route is **`/api/notes-generator/generate`**. The `/api/notes` route is strictly reserved for handwritten OCR uploads. | **HIGH** | Fixed endpoint mappings; clarified that `/api/notes` is OCR. |
| **7** | **Notes Evidence Claim** | Claimed notes engine has zero access to quiz/tutor evidence | **`resolver.py` explicitly ingests quiz and teach session misconceptions and mastery**, though frontend UI defaults to topic mode unless linked. | **HIGH** | Re-classified Notes from "monolithic" to "evidence-capable engine with prompt-default UI". |
| **8** | **Live Quiz Route** | Cited `/api/live-quiz/` | Router in `main.py` is mounted at **`/api/live-quizzes`** (plural). | **LOW** | Corrected endpoint URLs. |
| **9** | **Mastery Terminology** | Claimed "Bayesian Mastery" ($1 - e^{-0.48N}$) | Purely an **Additive Step Mastery Heuristic with Asymptotic Confidence Curve**. Contains zero Bayesian prior/posterior math. | **HIGH** | Renamed algorithm accurately; specified authentic BKT equations for vNext. |
| **10**| **Video Cost Accounting**| Claimed ~$0.0018 total cost per video | $0.0018 is strictly **Inference-Only API Cost**. Omits FFmpeg CPU time, storage, and egress bandwidth (~$0.0031 total). | **MEDIUM**| Labeled as "Inference-Only API Cost" vs "Total Production Cost". |
| **11**| **Fake Precision Metrics**| Presented 96.7% savings, 30.1x QPC, 91.6/100 quality, 0.74 precision as measured outcomes | These are **TARGETS / PROJECTED ESTIMATES** based on simulation models and canonical rubric specs, NOT production telemetric telemetry. | **HIGH** | Re-labeled all projected figures as **[PROJECTED]** or **[TARGET]**. |
| **12**| **Parallel Racing LLMs** | Highlighted `call_best_llm` as active PPT premium path | `call_best_llm` is defined in `llm_service.py` but **never called anywhere in the entire codebase**. | **MEDIUM**| Marked as dead/orphaned experimental code. |
| **13**| **Reviewer LLM Role** | Claimed Reviewer LLM is needed for layout/overflow bugs | Layout, banned strings, and underfit are **already handled by deterministic pre-checks** in `reviewer_agent.py`; the LLM call was a redundant deck critic. | **HIGH** | Decomposed Reviewer into 3 gated tiers. |
| **14**| **Stage Video Route** | Listed as live feature | `POST /api/lesson-planner/{id}/stages/{id}/video` returns a hardcoded **HTTP 400 Bad Request**. It is decommissioned. | **MEDIUM**| Re-classified as **BROKEN / DORMANT**. |
