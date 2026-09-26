"""
LearnByGenie — Live Quiz VNEXT Synthetic Load Test Harness (§19)
==============================================================
Simulates 100, 500, 1000, 2500, 5000, and 10000 concurrent participants
submitting answers under bounded micro-batching, realtime aggregation,
and live ban propagation checks.
"""
import asyncio
import time
import statistics
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from typing import Dict, Any, List



def _get_process_memory_mb() -> float:
    try:
        import ctypes
        from ctypes import wintypes
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


# Ensure persistence is in-memory for offline/staging benchmark
from app.services.live_quiz import repository as repo
repo.set_persistence_enabled(False)

from app.services.live_quiz.microbatch_writer import BoundedResponseMicroBatchWriter
from app.services.live_quiz.realtime_aggregator import RealtimeAggregator
from app.services.live_quiz.schemas import create_progression_token, verify_progression_token


async def run_tier_load_test(
    num_participants: int,
    batch_window_ms: int = 100,
    max_batch_size: int = 100,
) -> Dict[str, Any]:
    writer = BoundedResponseMicroBatchWriter(
        batch_window_ms=batch_window_ms,
        max_batch_size=max_batch_size,
        max_queue_depth=15000,
    )
    aggregator = RealtimeAggregator(interval_ms=250)

    session_id = f"sess_load_{num_participants}_{int(time.time())}"
    question_id = "q_perf_001"
    deadline_iso = "2026-12-31T23:59:59Z"
    prog_token = create_progression_token(session_id, 0, question_id, deadline_iso)

    # Pre-register participants
    for i in range(num_participants):
        repo.create_participant({
            "id": f"p_{num_participants}_{i}",
            "session_id": session_id,
            "display_name": f"Student_{i}",
            "score": 0,
        })

    latencies: List[float] = []
    errors: int = 0
    retries: int = 0

    async def student_task(student_idx: int):
        nonlocal errors, retries
        pid = f"p_{num_participants}_{student_idx}"
        opt = "A" if student_idx % 2 == 0 else "B"
        t0 = time.perf_counter()

        resp_row = {
            "id": f"r_{num_participants}_{student_idx}",
            "session_id": session_id,
            "participant_id": pid,
            "question_id": question_id,
            "selected_option_id": opt,
            "submitted_at": "2026-09-26T12:00:00Z",
            "response_time_ms": 1200 + (student_idx % 500),
            "is_correct": (opt == "A"),
            "points": 1000 if opt == "A" else 0,
            "attempt_number": 1,
            "idempotency_key": f"idem_{pid}_{question_id}",
        }
        part_delta = {
            "participant_id": pid,
            "fields": {
                "score": 1000 if opt == "A" else 0,
                "answered_count": 1,
                "current_question_index": 1,
            }
        }
        stats_delta = {
            "session_id": session_id,
            "question_id": question_id,
            "is_correct": (opt == "A"),
            "selected_option_id": opt,
            "response_time_ms": 1200,
        }

        try:
            # 1. Progression token validation
            verify_progression_token(prog_token, session_id, 0)

            # 2. Enqueue in microbatch writer
            await writer.enqueue(resp_row, part_delta, stats_delta)

            # 3. Feed realtime aggregator
            await aggregator.record_answer_event(session_id, question_id, opt, 1200)

            dur_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(dur_ms)
        except Exception as e:
            errors += 1

    mem_before_mb = _get_process_memory_mb()

    start_time = time.perf_counter()
    # Stagger slightly to simulate realistic burst
    tasks = [student_task(i) for i in range(num_participants)]
    await asyncio.gather(*tasks)

    # Flush all remaining buffers
    await writer.flush_all()
    await aggregator.flush_all()
    total_elapsed = time.perf_counter() - start_time

    mem_after_mb = _get_process_memory_mb()


    # Calculate metrics
    latencies.sort()
    p50 = statistics.median(latencies) if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0

    throughput_req_sec = round(num_participants / max(0.001, total_elapsed), 1)
    db_transactions = writer.total_batches
    db_tx_per_1000 = round((db_transactions / max(1, num_participants)) * 1000, 1)

    realtime_messages = aggregator.total_broadcasts_emitted
    realtime_msgs_per_1000 = round((realtime_messages / max(1, num_participants)) * 1000, 2)

    # Test ban propagation latency
    ban_target_pid = f"p_{num_participants}_0"
    ban_t0 = time.perf_counter()
    repo.ban_participant(session_id, ban_target_pid, "Cheating detected", "admin_load_test")
    p_banned = repo.get_participant(ban_target_pid)
    is_revoked = bool(p_banned and p_banned.get("is_banned"))
    ban_latency_ms = (time.perf_counter() - ban_t0) * 1000.0

    # Measure admin dashboard latency
    dash_t0 = time.perf_counter()
    repo.list_participants_cursor(session_id, limit=100)
    repo.get_session_monitoring_summary(session_id)
    dash_latency_ms = (time.perf_counter() - dash_t0) * 1000.0

    return {
        "participants": num_participants,
        "elapsed_sec": round(total_elapsed, 3),
        "requests_per_sec": throughput_req_sec,
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "avg_microbatch_size": round(writer.total_committed / max(1, writer.total_batches), 1),
        "db_transactions_total": db_transactions,
        "db_transactions_per_1000": db_tx_per_1000,
        "realtime_broadcasts_total": realtime_messages,
        "realtime_messages_per_1000": realtime_msgs_per_1000,
        "queue_depth_max": writer.get_metrics()["max_queue_depth"],
        "memory_used_mb": round(mem_after_mb - mem_before_mb, 2),
        "error_rate_pct": round((errors / num_participants) * 100, 2),
        "retry_rate_pct": round((retries / num_participants) * 100, 2),
        "dashboard_latency_ms": round(dash_latency_ms, 2),
        "ban_propagation_latency_ms": round(ban_latency_ms, 3),
        "ban_authoritative": is_revoked,
    }


async def main():
    tiers = [100, 500, 1000, 2500, 5000, 10000]
    print("=" * 80)
    print("LEARNBYGENIE LIVE QUIZ VNEXT — SYNTHETIC LOAD BENCHMARK (100 -> 10,000)")
    print("=" * 80)

    results = []
    for tier in tiers:
        print(f"Running synthetic load test for {tier} concurrent participants...")
        res = await run_tier_load_test(tier)
        results.append(res)
        print(f"  -> {tier} participants: {res['requests_per_sec']} req/s | "
              f"p50: {res['latency_p50_ms']}ms | p95: {res['latency_p95_ms']}ms | "
              f"Batch size: {res['avg_microbatch_size']} | "
              f"DB tx/1000: {res['db_transactions_per_1000']} | "
              f"Realtime msgs/1000: {res['realtime_messages_per_1000']} | "
              f"Ban latency: {res['ban_propagation_latency_ms']}ms")

    print("\n" + "=" * 80)
    print("FINAL LOAD TEST SUMMARY TABLE:")
    print("=" * 80)
    print(f"{'Tier':<8} | {'Req/s':<10} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'DB Tx/1k':<10} | {'RT Msg/1k':<10} | {'Mem (MB)':<8}")
    print("-" * 80)
    for r in results:
        print(f"{r['participants']:<8} | {r['requests_per_sec']:<10} | {r['latency_p50_ms']:<9} | {r['latency_p95_ms']:<9} | {r['latency_p99_ms']:<9} | {r['db_transactions_per_1000']:<10} | {r['realtime_messages_per_1000']:<10} | {r['memory_used_mb']:<8}")

if __name__ == "__main__":
    asyncio.run(main())
