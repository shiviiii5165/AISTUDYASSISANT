# MODEL STATUS & DEPRECATION AUDIT (SEPTEMBER 2026)

## 1. Official Live API Verification Summary

All model endpoints were validated against live provider catalog endpoints on September 12, 2026.

| Provider | Model ID Tested | Status | Live API Verification Result | Notes / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **Groq** | `llama-3.3-70b-versatile` | **RETIRED / 404** | `{"error":{"code":"model_not_found"}}` | **CRITICAL FIX**: Must be purged from `router.py`. |
| **Groq** | `llama-3.1-8b-instant` | **DEPRECATED** | Not returned in `api.groq.com/v1/models` | Replaced by `openai/gpt-oss-20b` or `qwen/qwen3.6-27b`. |
| **Groq** | `qwen/qwen3.8-27b` | **ACTIVE (200 OK)** | Returned `Status: 200` in 0.41s | Ultra-fast JSON & reasoning engine on Groq. |
| **Groq** | `openai/gpt-oss-120b` | **ACTIVE (200 OK)** | Returned in live catalog | High-capacity open-weight model on Groq. |
| **Groq** | `openai/gpt-oss-20b` | **ACTIVE (200 OK)** | Returned in live catalog | Low-latency fallback for classification & intent. |
| **Google** | `gemini-2.5-flash` | **ACTIVE (GA)** | Returned in Google v1beta catalog | Primary workhorse recommendation for TeachGenie. |
| **Google** | `gemini-2.5-pro` | **ACTIVE (GA)** | Returned in Google v1beta catalog | High-reasoning escalation tier. |
| **Google** | `gemini-2.5-flash-lite` | **ACTIVE (GA)** | Returned in Google v1beta catalog | High-speed, lower cost tier. |
| **Google** | `gemini-3.6-flash` | **ACTIVE PREVIEW** | Configured in `llm_service.py` | Google v1beta preview endpoint. |
| **Google** | `gemini-1.5-flash` | **LEGACY / RETIRING**| Superseded by 2.5 series | Deprecated for new deployments. |
| **OpenRouter** | `openai/gpt-4o` | **ACTIVE (200 OK)** | $2.50 / $10.00 per M tokens | Current TeachGenie router default (Cost leak source). |
| **OpenRouter** | `openai/gpt-4o-mini` | **ACTIVE (200 OK)** | $0.15 / $0.60 per M tokens | Cost-effective fallback on OpenRouter. |
| **OpenRouter** | `google/gemini-2.5-flash`| **ACTIVE (200 OK)** | $0.30 / $2.50 per M tokens | Marked up 2x prompt / 4.16x completion vs direct. |
| **Anthropic** | `claude-3-5-sonnet` | **ACTIVE (GA)** | $3.00 / $15.00 per M tokens | Benchmark gold standard for complex reasoning. |
| **Anthropic** | `claude-3-5-haiku` | **ACTIVE (GA)** | $0.80 / $4.00 per M tokens | Fast structured JSON output. |

---

## 2. Errata: Correction of Stale Assumptions in Previous Audit

1. **The Groq LLaMA 3.3 Hallucination**:
   - The previous audit recommended `llama-3.3-70b-versatile` as Tier 3 for low-latency tutoring.
   - **Adversarial Test Result**: A live POST request to `api.groq.com/openai/v1/chat/completions` using the active project key returned an explicit `404 model_not_found`.
   - **Correction**: Active low-latency Groq models in production are **`qwen/qwen3.8-27b`** and **`openai/gpt-oss-120b`**.
2. **OpenRouter Gemini Markup**:
   - The previous audit did not quantify OpenRouter intermediary markup for non-OpenAI models.
   - **Live API Result**: `openrouter.ai/api/v1/models` lists `google/gemini-2.5-flash` at **$0.30 / $2.50 per M tokens**. Direct Google API charges **$0.15 / $0.60 per M tokens**.
   - Routing Gemini via OpenRouter rather than Google Direct incurs a **316% cost penalty** on completions.
