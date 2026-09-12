# TEACHGENIE — DUPLICATE REASONING & COMPUTE WASTE MATRIX
**Audit Date:** September 12, 2026  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer

---

## 1. Cross-Feature Reasoning Duplication Matrix

When a user explores a single topic (e.g. *"Photosynthesis"* or *"Newton's Laws"*) across different TeachGenie features, **how much semantic reasoning is redundantly regenerated from scratch?**

| Conceptual Target | Lesson Planner | Presentation (PPT) | AI Study Notes | Quiz Generator | Teach Me (Tutor) | Video Studio | Duplication Verdict & Redundant Cost Impact |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Learning Objectives Extraction** | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **100% REDUNDANT.** 6 separate LLM calls synthesize the identical syllabus objectives for the same topic. |
| **Core Concept Decomposition** | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **100% REDUNDANT.** Decomposes topics into identical stages, slides, sections, questions, and scenes. |
| **Misconception Discovery** | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | Not extracted | **83% REDUNDANT.** 5 features separately ask models: *"What do students commonly misunderstand about this topic?"* |
| **Prerequisite Dependencies** | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | Evaluated (Rules) | Not evaluated | **RE-DERIVED** (LLM) | Not evaluated | **60% REDUNDANT.** Lesson Planner, PPT Ontology, and Tutor independently prompt for prerequisite concepts. |
| **Concrete Real-World Analogies** | Not extracted | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | Not extracted | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | **66% REDUNDANT.** PPT, Notes, Tutor, and Video separately invent explanatory analogies. |
| **Visual / Diagram Opportunities** | Not extracted | **RE-DERIVED** (LLM) | **RE-DERIVED** (LLM) | Not extracted | Not extracted | **RE-DERIVED** (LLM) | **50% REDUNDANT.** Deciding whether a process requires a flowchart or hierarchy tree is re-queried 3 times. |
| **Bloom Difficulty Calibration** | Assigned (LLM) | Not extracted | Tagged (Validator) | Assigned (LLM) | Assigned (Rules) | Not extracted | **FRAGMENTED.** Assigned independently with zero cross-feature calibration. |

---

## 2. Quantifying the Redundant Reasoning Waste

### Scenario: A Student Studies "Photosynthesis" (Class 10 CBSE)
Suppose a student generates a **Lesson Plan**, creates **Study Notes**, generates a **Quiz**, has a **TeachMe Session**, and reviews a **Topic Deck**.

```text
Current Workflow (Stateless Siloed Generations):
├── 1. Lesson Planner: LLM Call 1 derives concepts + objectives + misconceptions ──> 1,500 in / 1,800 out ($0.0218)
├── 2. Topic Deck: LLM Call 1 re-derives ontology + misconceptions ───────────────> 600 in / 450 out ($0.0060)
│                 LLM Call 2 re-plans slide concepts ───────────────────────────> 1,200 in / 900 out ($0.0120)
├── 3. Study Notes: LLM Call 1 re-derives sections + debunking structure ─────────> 1,800 in / 2,800 out ($0.0325)
├── 4. Quiz Generator: LLM Call 1 re-derives distractors + concept targets ───────> 1,400 in / 1,600 out ($0.0195)
└── 5. TeachMe Tutor: LLM Call 1 re-derives 4 concepts + checkpoints ─────────────> 1,100 in / 350 out ($0.0063)
TOTAL TOKEN EXPENDITURE: 7,600 Input Tokens / 7,900 Output Tokens across 6 LLM Calls
TOTAL INFERENCE COST: $0.0981 (on GPT-4o) / $0.0039 (on Gemini Flash)
```

```text
Target Workflow with Reusable Knowledge Pack:
├── 1. Initial Topic Request: Generate structured TEACHGENIE KNOWLEDGE PACK ────> 1,200 in / 1,500 out ($0.0162)
│      (Persisted in Supabase knowledge_packs with 30-day TTL)
├── 2. Lesson Planner ──> Pure deterministic graph compilation from Knowledge Pack -> 0 LLM Calls ($0.0000)
├── 3. Topic Deck ──────> Planner consumes Knowledge Pack -> 0 Ontology calls (Saves 1 LLM call)
├── 4. Study Notes ─────> Step 3 Generation consumes Knowledge Pack directly (0 prompt hallucination)
├── 5. Quiz Generator ──> Distractors and targets pulled directly from Knowledge Pack
└── 6. TeachMe Tutor ───> Concepts and checkpoints pre-structured from Knowledge Pack
TOTAL REDUNDANT LLM CALLS ELIMINATED: 3 out of 6 calls (50.0% reduction)
TOTAL TOKEN SAVINGS: ~4,200 Input Tokens / ~3,500 Output Tokens per multi-feature topic journey!
```

---

## 3. High-Leverage Architecture Solution

By creating a **single topic-level intelligence artifact (`KnowledgePack`)**, all six generation services transition from **raw conceptual synthesis** to **specialized formatting and rendering**:
1. **PPT Engine** focuses strictly on visual storytelling and layout constraints.
2. **Notes Engine** focuses strictly on pedagogical scaffolding and Bloom distribution.
3. **Quiz Engine** focuses strictly on distractor discrimination.
4. **Tutor Engine** focuses strictly on Socratic turn dynamics and student empathy.
