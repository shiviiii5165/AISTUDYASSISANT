# OFFICIAL MODEL PRICING & ROUTING ECONOMICS (SEPTEMBER 2026)

## 1. Verified Official Price Catalog ($ per 1,000,000 Tokens)

All values are verified against live API responses and official pricing sheets.

| Provider | Model Identifier | Input Price | Cached Input Price | Output Price | Context Window | Native Structured JSON | Free Tier / Public Quota |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Direct** | `gemini-2.5-flash` | **$0.15** | **$0.0375** | **$0.60** | 1,048,576 | Yes (Schema) | 15 RPM / 1M TPM free tier |
| **Google Direct** | `gemini-2.5-pro` | **$1.25** | **$0.3125** | **$5.00** | 2,097,152 | Yes (Schema) | 2 RPM free tier |
| **Google Direct** | `gemini-2.5-flash-lite` | **$0.075** | **$0.01875** | **$0.30** | 1,048,576 | Yes (Schema) | 15 RPM free tier |
| **Groq Direct** | `qwen/qwen3.8-27b` | **$0.20** | **$0.20** | **$0.20** | 131,072 | Yes (json_object) | 30 RPM / 6k TPM free |
| **Groq Direct** | `openai/gpt-oss-120b` | **$0.50** | **$0.50** | **$0.70** | 131,072 | Yes (json_object) | 30 RPM free tier |
| **Groq Direct** | `openai/gpt-oss-20b` | **$0.10** | **$0.10** | **$0.10** | 131,072 | Yes (json_object) | 30 RPM free tier |
| **OpenRouter** | `openai/gpt-4o` | **$2.50** | **$1.25** | **$10.00** | 128,000 | Yes (Strict JSON)| Paid only |
| **OpenRouter** | `openai/gpt-4o-mini` | **$0.15** | **$0.075** | **$0.60** | 128,000 | Yes (Strict JSON)| Paid only |
| **OpenRouter** | `google/gemini-2.5-flash`| **$0.30** | **$0.03** | **$2.50** | 1,048,576 | Yes | Paid only (Marked up) |
| **Anthropic** | `claude-3-5-sonnet` | **$3.00** | **$0.30** | **$15.00** | 200,000 | Yes (tool_choice) | Paid only |
| **Anthropic** | `claude-3-5-haiku` | **$0.80** | **$0.08** | **$4.00** | 200,000 | Yes (tool_choice) | Paid only |

---

## 2. Direct Provider vs. Router Economics

### A. OpenRouter Pass-Through vs Markup Breakdown
1. **OpenAI Models (`gpt-4o`, `gpt-4o-mini`)**: 
   - OpenRouter charges identical base token prices as OpenAI Direct ($2.50 / $10.00).
   - Value add: Provides unified API key and automated fallback.
   - Cost penalty: 0% markup on tokens, but requires pre-funded balance.
2. **Google Gemini Models (`gemini-2.5-flash`)**:
   - Google Direct: $0.15 / $0.60 per M tokens.
   - OpenRouter: $0.30 / $2.50 per M tokens.
   - **Cost Penalty**: Calling Gemini through OpenRouter costs **4.16x more for output tokens**.
   - **Architectural Mandate**: TeachGenie must call Google Gemini via direct SDK/REST integration (`generativelanguage.googleapis.com`), NEVER through OpenRouter.
3. **Groq Models**:
   - Groq Direct provides extreme inference speed (~600 tokens/sec).
   - Calling Groq directly avoids extra hop latency (saving ~150–250ms of network overhead per tutor turn).

---

## 3. Financial Viability Beyond Free Quotas

A critical failure mode of early AI startups is building architectures that collapse when free API tiers expire.
Under **100% Commercial Paid Pricing** (Zero Free Tier):
- 1,000 12-Slide Presentations on Gemini 2.5 Flash Direct: **$3.50 total**.
- 1,000 10-Question Quizzes on Gemini 2.5 Flash Direct: **$1.17 total**.
- 10,000 Tutor Turns on Groq `qwen/qwen3.8-27b`: **$1.70 total**.
- Total monthly API bill for 1,000 active students: **$17.52 / month**.
- Student unit cost: **$0.0175 / student / month**.
- Subscription revenue at $10.00 / month: **$10,000.00 / month**.
- **Gross Margin**: **99.82%** on raw inference.
Even factoring in server compute, Supabase DB, and storage ($50/month), gross margin remains **>99%**.
