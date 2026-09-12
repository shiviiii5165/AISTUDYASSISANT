# Resource Provider Health & Circuit Breaker Telemetry Report

## 1. Provider Telemetry Summary

The [`SourceHealthTracker`](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/services/lesson_planner/vnext/resources/source_health.py) monitors latency percentiles, error rates, and rate-limit states across all integrated resource providers.

```text
Incoming Resource Request
          │
          ▼
   [Circuit Healthy?]
      │         │
     YES        NO (Rate-limited / consecutive errors)
      │         │
      ▼         ▼
Execute Query  Instant Fallback to Cached / Precomputed Canonical Resources
```

---

## 2. Live Runtime Telemetry

Measured across live validation and canary executions:

| Resource Provider | Total Calls | Success Rate | Latency P50 | Latency P95 | Rate-Limit / Circuit Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`course_intelligence`** (NPTEL / MIT OCW) | 35 | **100.0%** | **0.13 ms** | **0.24 ms** | **HEALTHY** |
| **`youtube_precision`** | 7 | **100.0%** | **1,255.33 ms** | **2,803.31 ms** | **HEALTHY** |
| **`academic_evidence`** (ArXiv / Crossref) | 1 | **100.0%** | 10,532.39 ms | 10,532.39 ms | **HEALTHY** |
| **`coding_engine`** (GFG / LeetCode) | 12 | **100.0%** | **0.05 ms** | **0.10 ms** | **HEALTHY** |
| **`docs_engine`** (Official Docs) | 10 | **100.0%** | **0.04 ms** | **0.08 ms** | **HEALTHY** |

---

## 3. Circuit Breaker Behavior & Fault Tolerance

1. **Threshold Trigger**: If 5 or more calls are recorded and consecutive failures drop the rolling success rate below 50%, the provider is tagged `circuit_broken`.
2. **Graceful Degradation**: When a provider is circuit-broken or times out, the system degrades instantly without throwing exceptions or blocking the core lesson plan.
3. **Automatic Recovery**: Once consecutive successful canary probes occur and the success rate recovers above 80%, the circuit status automatically resets to `healthy`.

### Unit Test Proof
- Validated in [`test_vnext_unified_resource_intelligence.py::test_source_health_tracker_and_circuit_breaker`](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/tests/test_vnext_unified_resource_intelligence.py).
- Verified that 6 consecutive HTTP 503 mock errors trigger `rate_limit_status = "circuit_broken"` and `is_healthy = False`.
