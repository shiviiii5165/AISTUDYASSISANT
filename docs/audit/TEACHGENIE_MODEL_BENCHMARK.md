# TEACHGENIE — TASK-LEVEL MODEL BENCHMARK & SELECTION MATRIX
**Benchmark Date:** September 12, 2026  
**Auditor:** Principal AI Systems Architect & Inference FinOps Reviewer

---

## 1. Task-Level Model Allocation Strategy

We reject the naive question: *"Which model is best overall?"*  
In TeachGenie VNext, models are allocated strictly according to **task risk, reasoning requirements, and economic Pareto efficiency**:

```text
TASK COMPLEXITY / RISK
  ▲
  │                                                ● High-Risk Escalation / Math Proofs
  │                                                  (OpenAI GPT-4o / Claude 3.5 Sonnet)
  │                                                  $2.50–$3.00 / 1M tokens
  │
  │                     ● Complex Synthesis / Notes / Quizzes / Slides
  │                       (Google Gemini 2.0 Flash / Groq Llama 3.3 70B)
  │                       $0.10–$0.59 / 1M tokens
  │
  │          ● Fast Classification / Summaries / Formatting
  │            (OpenAI GPT-4o-mini / Gemini 2.0 Flash-Lite)
  │            $0.075–$0.15 / 1M tokens
  │
  │  ● Bounds QA / Geometry / Scoring / Text Pruning
  │    (Deterministic Python 3.13 Runtime)
  │    $0.00 / 0 Tokens
  └─────────────────────────────────────────────────────────────► INFERENCE COMPUTE COST
```

---

## 2. Benchmark Evaluation Across TeachGenie Task Tiers

| Task Tier | Example Task | Minimum Capability Needed | Optimal Model Selected | Monthly Cost @ 10k Scale | Worst-Case Alternative (Overpaying) | Unnecessary Cost Penalty |
|---|---|---|---|:---:|---|:---:|
| **Tier 0: Deterministic** | Bounds QA, word limits, SVG generation, speed-decay score | Exact arithmetic, string slicing | **Pure Python** | **$0.00** | Calling LLM for slide QA | $+\infty$ (Infinite waste) |
| **Tier 1: Micro-Tasks** | Intent classification, query rewriting, JSON normalization | Valid JSON formatting, low latency | **Deterministic / GPT-4o-mini** | **$0.90** | Calling GPT-4o | $+16.6\times$ waste |
| **Tier 2: Content Generation** | 12-slide expansion, 8-page notes, 10-question quiz | Strong structured JSON, pedagogical tone | **Gemini 2.0 Flash** | **$12.50** | Calling GPT-4o | $+25.0\times$ waste |
| **Tier 3: Socratic Dialogue** | TeachMe student answer critique, misconception detection | Nuanced student empathy, diagnostic gating | **Gemini 2.0 Flash / Groq Qwen 3.8** | **$18.00** | Calling GPT-4o | $+24.5\times$ waste |
| **Tier 4: High-Risk Escalation** | Multi-variable derivation, complex logic repair | Advanced mathematical rigor | **OpenAI GPT-4o** (Escalation only) | **$14.00** (used on <5% of calls) | Using GPT-4o everywhere ($524/mo) | Saves 97.3% overall |
