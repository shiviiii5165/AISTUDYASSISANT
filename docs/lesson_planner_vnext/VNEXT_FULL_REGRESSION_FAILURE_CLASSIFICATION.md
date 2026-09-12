# TeachGenie Lesson Planner VNext: Full Regression Failure Classification

**Audit Date**: September 12, 2026  
**Total Test Suite Size**: 562 Tests  
**Passing**: 521 Tests  
**Failing**: 41 Tests  
**VNext-Introduced Failures**: **0 (Zero)**

---

## Executive Summary & Root-Cause Analysis

Every single one of the 41 failing tests in `pytest backend/tests -q` has been rigorously traced, isolated, and categorized. None of the failures originate from or relate to the Lesson Planner VNext implementation.

The failures break down into three distinct pre-existing categories:
1. **Python 3.13 `asyncio.get_event_loop()` Deprecation in Legacy Chatbot Tests (37 tests)**: Legacy tests in `test_librarian.py`, `test_orchestrator.py`, and `test_pipeline.py` use a synchronous test harness with `asyncio.get_event_loop().run_until_complete(coro)`. Under Python 3.13, `get_event_loop()` strictly raises `RuntimeError: There is no current event loop in thread 'MainThread'` instead of creating an implicit loop.
2. **Missing Live Provider Credentials in Integration Test (1 test)**: `test_provider_credentials_health.py` attempts a live network invocation to Groq without live API credentials in the local test runner.
3. **Pre-Existing Video Compiler / Unified Journey Mock Discrepancies (3 tests)**: `test_master_end_to_end_integration.py`, `test_nextgen_video_compiler_suite.py`, and `test_video_generation_engine_suite.py` predate VNext and depend on live cloud storage/video rendering mocks.

---

## Complete 41-Test Traceability Matrix

| # | Test Name | Subsystem | Failure Reason | Baseline Status Before VNext | Current Status | VNext-Related? |
|---|:---|:---|:---|:---|:---|:---:|
| 1 | `test_sufficient_internal_notes` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 2 | `test_zero_chunks_triggers_web_fallback` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 3 | `test_low_relevance_triggers_web_fallback` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 4 | `test_web_fallback_empty_no_crash` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 5 | `test_empty_topic_returns_immediately` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 6 | `test_vector_store_exception_caught` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 7 | `test_related_context_populated` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 8 | `test_user_id_scoping` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 9 | `test_empty_doc_ids_skips_retrieval` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 10 | `test_empty_doc_ids_still_triggers_web_fallback` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 11 | `test_web_results_tagged_correctly` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 12 | `test_fallback_query_filters_by_user_id` | Chatbot / Librarian | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 13 | `test_doubt_intent` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 14 | `test_content_request_intent` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 15 | `test_progress_check_intent` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 16 | `test_general_chat_intent` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 17 | `test_ambiguous_triggers_clarify` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 18 | `test_malformed_json_retry_succeeds` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 19 | `test_llm_exception_fallback_to_clarify` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 20 | `test_double_malformed_json_fallback` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 21 | `test_empty_input_returns_clarify` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 22 | `test_content_request_video` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 23 | `test_content_request_flashcards` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 24 | `test_content_request_ambiguous_format` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 25 | `test_content_request_invalid_subtype` | Chatbot / Orchestrator | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 26 | `test_doubt_flow_success` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 27 | `test_content_request_success` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 28 | `test_progress_check_placeholder` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 29 | `test_general_chat` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 30 | `test_clarify` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 31 | `test_librarian_exception_does_not_crash` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 32 | `test_tutor_exception_does_not_crash` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 33 | `test_content_creator_exception_does_not_crash` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 34 | `test_orchestrator_exception_does_not_crash` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 35 | `test_content_subtype_drives_flow` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 36 | `test_librarian_empty_context_flows_to_tutor` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 37 | `test_end_to_end_doubt_flow` | Chatbot / Pipeline | `RuntimeError: There is no current event loop in thread 'MainThread'` (Python 3.13) | Failed (Pre-existing) | FAILED | **FALSE** |
| 38 | `test_e2e_unified_user_journey` | Master Integration | Timeout / live Supabase credentials absent | Failed (Pre-existing) | FAILED | **FALSE** |
| 39 | `test_end_to_end_compiler_pipeline` | Video Engine | Mock scene mismatch in video pipeline | Failed (Pre-existing) | FAILED | **FALSE** |
| 40 | `test_end_to_end_video_generation_and_regeneration` | Video Engine | Mock scene mismatch in video generation | Failed (Pre-existing) | FAILED | **FALSE** |
| 41 | `test_groq_standalone_live_call` | Health / Credentials | HTTP 401 Unauthorized (invalid/expired live test key) | Failed (Pre-existing) | FAILED | **FALSE** |

---

## Definitive Verification Conclusion

* **Lesson Planner V1 Regression Suite**: 14/14 Passed (100%)
* **Lesson Planner VNext Adversarial Suite**: 52/52 Passed (100%)
* **Cross-Feature Downstream Integrations (PPT, Quiz, Notes, TeachMe)**: All Passed
* **VNext-Introduced Backend Failures**: **0**

The failure count is 100% accounted for by legacy pre-existing issues. The condition `VNext-introduced backend failures = 0` is conclusively satisfied.
