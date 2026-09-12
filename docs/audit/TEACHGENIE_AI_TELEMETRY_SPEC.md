# TEACHGENIE AI TELEMETRY SPECIFICATION (vNext)

## 1. Executive Summary & Privacy Mandate

TeachGenie vNext requires unified, non-invasive telemetry across all AI inferences, tool invocations, and deterministic validations. 
**Student Privacy Mandate (FERPA / COPPA / GDPR compliant)**:
- **Raw prompts and student inputs containing PII MUST NEVER be stored in telemetry logs.**
- Prompts are tokenized or hashed (`prompt_sha256 = sha256(canonical_prompt)[:16]`) for cache-keying and anomaly tracking.
- System metrics record token counts, latency, cost, and routing decisions without logging student-identifiable freeform text.

---

## 2. Core Telemetry Schema

Every LLM inference, embedding generation, or multi-modal API call emits an immutable `AiTelemetryRecord`.

### SQL Table Schema (PostgreSQL)

```sql
CREATE TABLE IF NOT EXISTS ai_telemetry_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Execution Context
    request_id VARCHAR(64) NOT NULL,
    workflow_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64),
    user_id_hash VARCHAR(64), -- SHA-256 hashed user ID to prevent PII exposure
    
    -- Task Categorization
    feature VARCHAR(32) NOT NULL, -- e.g., 'presentation', 'tutor', 'quiz', 'notes'
    operation VARCHAR(64) NOT NULL, -- e.g., 'generate_ontology', 'checkpoint_eval', 'distractor_gen'
    task_type VARCHAR(32) NOT NULL, -- 'tiny', 'moderate', 'reasoning', 'high_risk'
    
    -- Provider & Model Details
    provider VARCHAR(32) NOT NULL, -- 'google', 'groq', 'openrouter', 'mistral'
    model VARCHAR(64) NOT NULL, -- e.g., 'gemini-2.5-flash', 'llama-3.3-70b-versatile'
    routed_tier VARCHAR(32) NOT NULL, -- 'deterministic', 'tiny', 'standard', 'escalation'
    
    -- Token & Compute Accounting
    input_tokens INT NOT NULL DEFAULT 0,
    cached_input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    reasoning_tokens INT NOT NULL DEFAULT 0,
    
    -- Performance Metrics
    latency_ms INT NOT NULL,
    time_to_first_token_ms INT,
    
    -- Reliability & Resiliency
    retry_count INT NOT NULL DEFAULT 0,
    fallback_count INT NOT NULL DEFAULT 0,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    cache_layer VARCHAR(16), -- 'L0_exact', 'L1_normalized', 'L2_knowledge_pack', 'L5_semantic'
    circuit_breaker_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Ancillary Tool Calls
    external_search_calls INT NOT NULL DEFAULT 0,
    embedding_calls INT NOT NULL DEFAULT 0,
    image_calls INT NOT NULL DEFAULT 0,
    
    -- Financial Accounting
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    
    -- Quality & Downstream Acceptance
    deterministic_pass BOOLEAN NOT NULL DEFAULT TRUE,
    repair_required BOOLEAN NOT NULL DEFAULT FALSE,
    repair_type VARCHAR(32), -- 'overflow', 'malformed_json', 'bad_distractor'
    quality_score NUMERIC(4, 3), -- Optional evaluation score (0.000 to 1.000)
    accepted BOOLEAN -- User action: slide kept, notes downloaded, tutor continued
);

CREATE INDEX idx_telemetry_workflow ON ai_telemetry_records(workflow_id);
CREATE INDEX idx_telemetry_feature_op ON ai_telemetry_records(feature, operation);
CREATE INDEX idx_telemetry_timestamp ON ai_telemetry_records(timestamp);
CREATE INDEX idx_telemetry_cost ON ai_telemetry_records(estimated_cost_usd);
```

---

## 3. Pydantic Event Model

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class AiTelemetryEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    request_id: str
    workflow_id: str
    session_id: Optional[str] = None
    user_id_hash: Optional[str] = None
    
    feature: str
    operation: str
    task_type: str
    
    provider: str
    model: str
    routed_tier: str
    
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    
    latency_ms: int
    time_to_first_token_ms: Optional[int] = None
    
    retry_count: int = 0
    fallback_count: int = 0
    cache_hit: bool = False
    cache_layer: Optional[str] = None
    circuit_breaker_triggered: bool = False
    
    external_search_calls: int = 0
    embedding_calls: int = 0
    image_calls: int = 0
    
    estimated_cost_usd: float = 0.0
    
    deterministic_pass: bool = True
    repair_required: bool = False
    repair_type: Optional[str] = None
    quality_score: Optional[float] = None
    accepted: Optional[bool] = None
```

---

## 4. Model Price Registry for Real-Time Cost Calculation

Telemetry calculates `estimated_cost_usd` dynamically at invocation completion based on current rates:

```python
PRICING_TABLE_PER_MILLION = {
    "gemini-2.5-flash": {
        "input": 0.15,
        "cached_input": 0.0375,
        "output": 0.60
    },
    "gemini-2.5-pro": {
        "input": 1.25,
        "cached_input": 0.3125,
        "output": 5.00
    },
    "llama-3.3-70b-versatile": { # Groq
        "input": 0.59,
        "cached_input": 0.59,
        "output": 0.79
    },
    "llama-3.1-8b-instant": { # Groq
        "input": 0.05,
        "cached_input": 0.05,
        "output": 0.08
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.80,
        "cached_input": 0.08,
        "output": 4.00
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,
        "cached_input": 0.30,
        "output": 15.00
    },
    "openai/gpt-4o": { # OpenRouter
        "input": 2.50,
        "cached_input": 1.25,
        "output": 10.00
    },
    "openai/gpt-4o-mini": {
        "input": 0.15,
        "cached_input": 0.075,
        "output": 0.60
    }
}

def calculate_inference_cost(
    model: str, 
    input_tokens: int, 
    cached_input_tokens: int, 
    output_tokens: int
) -> float:
    rates = PRICING_TABLE_PER_MILLION.get(model, {"input": 1.0, "cached_input": 0.5, "output": 2.0})
    uncached_inputs = max(0, input_tokens - cached_input_tokens)
    
    cost = (
        (uncached_inputs / 1_000_000.0) * rates["input"] +
        (cached_input_tokens / 1_000_000.0) * rates["cached_input"] +
        (output_tokens / 1_000_000.0) * rates["output"]
    )
    return round(cost, 6)
```

---

## 5. Non-Invasive Instrumentation Hook Architecture

The instrumentation wraps the unified `QualityPerComputeRouter` via an async context manager:

```python
import time
from contextlib import asynccontextmanager

class TelemetryCollector:
    _buffer = []

    @classmethod
    @asynccontextmanager
    async def track(cls, request_id: str, workflow_id: str, feature: str, operation: str):
        record = {
            "request_id": request_id,
            "workflow_id": workflow_id,
            "feature": feature,
            "operation": operation,
            "start_time": time.perf_counter(),
            "retry_count": 0,
            "fallback_count": 0,
            "cache_hit": False,
            "repair_required": False
        }
        try:
            yield record
        finally:
            latency_ms = int((time.perf_counter() - record["start_time"]) * 1000)
            cost = calculate_inference_cost(
                record.get("model", "unknown"),
                record.get("input_tokens", 0),
                record.get("cached_input_tokens", 0),
                record.get("output_tokens", 0)
            )
            event = AiTelemetryEvent(
                request_id=request_id,
                workflow_id=workflow_id,
                feature=feature,
                operation=operation,
                task_type=record.get("task_type", "standard"),
                provider=record.get("provider", "unknown"),
                model=record.get("model", "unknown"),
                routed_tier=record.get("routed_tier", "standard"),
                input_tokens=record.get("input_tokens", 0),
                cached_input_tokens=record.get("cached_input_tokens", 0),
                output_tokens=record.get("output_tokens", 0),
                latency_ms=latency_ms,
                retry_count=record.get("retry_count", 0),
                fallback_count=record.get("fallback_count", 0),
                cache_hit=record.get("cache_hit", False),
                cache_layer=record.get("cache_layer"),
                estimated_cost_usd=cost,
                repair_required=record.get("repair_required", False)
            )
            # Emit asynchronously to background queue / database
            await cls._emit(event)

    @classmethod
    async def _emit(cls, event: AiTelemetryEvent):
        # Non-blocking async dispatch to telemetry queue / DB writer
        pass
```

---

## 6. Real-Time Alerting & Anomaly Triggers

The telemetry collector connects to Prometheus/Grafana or CloudWatch alerts for:
1. **Cost Spike Alert**: `SUM(estimated_cost_usd) > $10.00 / 10min`
2. **Quality Failure Spike**: `COUNT(repair_required == True) / COUNT(*) > 0.15` (over 15% repair rate)
3. **Cache Miss Degeneration**: `L2_knowledge_pack hit_rate < 0.40` on repeated curriculum topics
4. **Model Escalation Leak**: `routed_tier == 'escalation'` exceeding 5% of total requests
5. **Latency Degradation**: `latency_ms p95 > 8000ms` on interactive tutor turns.
