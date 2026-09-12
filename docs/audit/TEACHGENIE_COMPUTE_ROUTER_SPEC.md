# TEACHGENIE — QUALITY-PER-COMPUTE ROUTER SPECIFICATION
**Specification Version:** 2.0.0  
**Status:** UNIFIED AI STACK SPECIFICATION FOR VNEXT  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer

---

## 1. Unified Architecture Objective

Replace the existing fragmented dual-stack (`app/services/llm_service.py` and `app/services/ai/router.py`) with a single **Quality-Per-Compute (QPC) Semantic Router**.

```text
                                TASK REQUEST
                                     │
                                     ▼
                   [STAGE 1: CAN DETERMINISTIC CODE SOLVE IT?]
                   ├── Bounds QA, SVG Diagrams, HTML Assembly,
                   │   Time Budgeting, Scoring, Distractor Pruning
                   └── YES ──────────> EXECUTE PYTHON (0 Tokens, 0 Cost)
                        │ NO
                        ▼
                   [STAGE 2: IS REUSABLE INTELLIGENCE CACHED?]
                   ├── Topic KnowledgePack (30d TTL), SHA256 Presentation Cache,
                   │   TTS Audio Hash (.wav), Embedding Vector Cache
                   └── YES ──────────> RETURN CACHE (0 Tokens, 0 Cost)
                        │ NO
                        ▼
                   [STAGE 3: CAN A LOW-COST FAST MODEL SOLVE IT?]
                   ├── Classification, Tagging, JSON Extraction,
                   │   Notes Generation, Quiz Items, Storyboard, Tutoring
                   └── YES ──────────> DISPATCH TO TIER 1 FAST MODEL
                        │              (Gemini 2.0 Flash / Groq Llama 3.3 70B / GPT-4o-mini)
                        │              Cost: $0.10–$0.59 / 1M tokens
                        │
                        ▼ [EVALUATE RESULT WITH DETERMINISTIC VALIDATOR]
                        ├── PASSED QUALITY GATE ──> ACCEPT & PERSIST
                        └── FAILED VALIDATION / LOW CONFIDENCE
                             │
                             ▼
                   [STAGE 4: ESCALATE TO STRONG REASONING MODEL]
                   ├── Complex Mathematical Derivation, Edge-case Remediation,
                   │   Final Multi-turn Socratic Repair
                   └── DISPATCH TO TIER 2 REASONING MODEL (GPT-4o / Claude 3.5 Sonnet)
                       Cost: $2.50–$3.00 / 1M tokens (Reserved for < 5% of requests)
```

---

## 2. Model Task Routing Matrix

| Task Category | Primary Model | Fallback Model 1 | Fallback Model 2 | Expected Token Cost / 1M (In/Out) | Max Output Tokens | Timeout |
|---|---|---|---|---|---|---|
| `classification` | Deterministic Regex | `gemini-2.0-flash` | `gpt-4o-mini` | $0.00 / $0.10 | 128 | 5s |
| `knowledge_pack` | `gemini-2.0-flash` | `gpt-4o-mini` | `llama-3.3-70b-versatile` | $0.10 / $0.40 | 3,000 | 45s |
| `content_generation` | `gemini-2.0-flash` | `llama-3.3-70b-versatile` | `gpt-4o-mini` | $0.10 / $0.40 | 4,096 | 60s |
| `socratic_tutor` | `gemini-2.0-flash` | `qwen/qwen3.8-27b` | `gpt-4o-mini` | $0.10 / $0.40 | 800 | 25s |
| `assessment_diagnostic` | Deterministic Match | `gemini-2.0-flash` | `gpt-4o-mini` | $0.00 / $0.10 | 400 | 15s |
| `reasoning_escalation` | `openai/gpt-4o` | `claude-3-5-sonnet` | `gemini-2.0-flash` | $2.50 / $10.00 | 2,048 | 45s |
| `embeddings` | `gemini-embedding-001` | `text-embedding-3-small` | None | $0.02 / $0.00 | N/A | 15s |

---

## 3. Migration Plan: File-by-File Consolidation

| Existing File / Caller | Current Implementation | Migration Action | Target Implementation |
|---|---|---|---|
| `backend/app/services/llm_service.py` | Direct Gemini REST `call_gemini()` | **DEPRECATE & REPLACE** | Replaced entirely by `app/services/ai/router.py`. |
| `backend/app/agents/orchestrator.py` | Calls `call_gemini()` | **UPDATE CALLER** | Call `ai_router.generate_json(task="classification")`. |
| `backend/app/agents/tutor.py` | Calls `call_gemini()` | **UPDATE CALLER** | Call `ai_router.generate_text(task="socratic_tutor")`. |
| `backend/app/services/rag_service.py` | Calls `call_gemini()` | **UPDATE CALLER** | Call `ai_router.generate_text(task="content_generation")`. |
| `backend/app/api/predict.py` | Calls `call_gemini()` | **UPDATE CALLER** | Call `ai_router.generate_json(task="content_generation")`. |
| `backend/app/services/ai/router.py` | OpenRouter `gpt-4o` as primary default | **RE-CALIBRATE POLICIES** | Re-order policies to make `gemini-2.0-flash` and local rules primary; `gpt-4o` strictly on escalation. |

---

## 4. Telemetry Schema

Every invocation through the unified router records an entry in `ai_telemetry_logs`:
```sql
CREATE TABLE IF NOT EXISTS ai_telemetry_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    feature TEXT NOT NULL,
    task_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_ms NUMERIC(7,2) NOT NULL,
    estimated_cost_usd NUMERIC(8,6) NOT NULL,
    retry_count INTEGER DEFAULT 0,
    was_cache_hit BOOLEAN DEFAULT FALSE,
    was_escalated BOOLEAN DEFAULT FALSE
);
```
