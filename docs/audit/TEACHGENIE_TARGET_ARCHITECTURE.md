# TEACHGENIE VNEXT — TARGET SYSTEM ARCHITECTURE
**Architecture Version:** 2.0.0  
**Status:** APPROVED TARGET ARCHITECTURE  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer

---

## 1. High-Level Target Architecture Diagram

```text
                                  USER (Teacher / Student)
                                             │
                                             ▼
                                    API GATEWAY / FASTAPI
                          (Auth, Rate Limiting, Schema Validation)
                                             │
                                             ▼
                                  UNIFIED CONTEXT RESOLVER
                     (Resolves Topic, Syllabus Grade, User History)
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             TEACHGENIE KNOWLEDGE PACK                   STUDENT LEARNING GRAPH
         (Cached Multi-Feature Topic Model)           (Persistent Mastery & Misconceptions)
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             ▼
                                      PEDAGOGY ENGINE
                     (Selects LearningMode, Scaffolding, Bloom Targets)
                                             │
                                             ▼
                                QUALITY-PER-COMPUTE ROUTER
                                             │
           ┌───────────────┬─────────────────┼─────────────────┬───────────────┐
           ▼               ▼                 ▼                 ▼               ▼
      DETERMINISTIC      CACHE           RETRIEVAL        FAST MODEL      STRONG MODEL
          CODE        (KnowledgePack,    (pgvector       (Gemini Flash    (OpenAI GPT-4o,
      (Bounds QA,     Presentation,       Hybrid,        Groq Llama 70B,   Escalation
      SVG, HTML,        Audio WAV,       Document        GPT-4o-mini)      Only < 5%)
       Scoring)       Embeddings)         Chunks)        $0.10 / 1M        $2.50 / 1M
           │               │                 │                 │               │
           └───────────────┴─────────────────┼─────────────────┴───────────────┘
                                             │
                                             ▼
                                  ARTIFACT COMPILERS LAYER
        ┌───────────────────┬───────────────────┬───────────────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼                   ▼
    PRESENTATION          STUDY               QUIZ                LIVE                VIDEO
     COMPILER             NOTES              ENGINE             CLASSROOM            STUDIO
   (python-pptx)       (Typesetter &       (Diagnostic         (Realtime SVG        (edge-tts &
                        Playwright)        Distractors)        Interventions)         FFmpeg)
        │                   │                   │                   │                   │
        └───────────────────┴───────────────────┼───────────────────┴───────────────────┘
                                                │
                                                ▼
                                    DETERMINISTIC QA GATING
                               (Bounds, LaTeX, Overflow, Dead Chunks)
                                                │
                                    PASSED QUALITY THRESHOLD?
                                           /         \
                                        YES           NO
                                         │             │
                                         │             ▼
                                         │    COMPONENT-LEVEL REPAIR
                                         │    (Targeted single-element
                                         │     re-generation, zero
                                         │     full-artifact re-runs)
                                         │             │
                                         └──────┬──────┘
                                                │
                                                ▼
                                      OUTPUT DELIVERED TO UI
                                                │
                                                ▼
                                     ASSESSMENT / INTERACTION
                                                │
                                                ▼
                                  UPDATE STUDENT LEARNING GRAPH
                               (Updates mastery, clears misconceptions)
```

---

## 2. Current vs. Target Feature Comparison Matrix

| Dimension | Current Architecture | Target VNext Architecture |
|---|---|---|
| **AI Router** | Dual-stack (`llm_service.py` vs `router.py`) with `gpt-4o` default | Unified Quality-Per-Compute Router (`gemini-2.0-flash` default, $0.10/M) |
| **Topic Intelligence** | Separately generated 6 times per topic across features | Synthesized once into a 30-day cached `KnowledgePack` |
| **Student Memory** | Fragmented across individual tables; generations are stateless | Central relational `student_mastery_states` with provenance |
| **Presentation Engine** | 4 sequential LLM calls; Reviewer rereads whole deck; stock photos | 1 batched LLM intent call; deterministic python-pptx geometry; Understanding Compiler |
| **Study Notes** | Monolithic prompt synthesis | Gap-Repair Notes: base content + student-specific misconception debunking |
| **Quiz Engine** | 10 arbitrary recall questions | Adaptive distractor mapping (every wrong option identifies a specific misconception) |
| **Live Classroom Quiz** | Host leaderboard + manual intervention clicks | Live Teaching Control System: automatic wrong-answer clustering + zero-cost SVG cards |
| **Tutor (TeachMe)** | 2 LLM calls per student turn ($0.096/session on GPT-4o) | Misconception-first Socratic engine; deterministic checkpoint verification ($0.003/session) |
| **Video Studio** | Disconnected from Lesson Planner | Zero-LLM TeachMe video export + $O(1)$ single-scene regeneration via FFmpeg |
| **Lesson Planner** | Static roadmap | Self-Correcting Roadmap that recalculates based on live quiz evidence |
| **Repair Granularity** | Full artifact regeneration on failure | Component-level repair (single slide, single section, single question, single scene) |
| **Monthly Bill (10k scale)** | ~$5,240.00 / month | ~$175.00 / month (96.7% inference reduction) |
