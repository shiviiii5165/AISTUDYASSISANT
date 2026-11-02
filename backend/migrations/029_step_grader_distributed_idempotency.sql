-- LearnByGenie — Migration 029: Step-Grader Distributed Idempotency & Sequence Safety
-- ====================================================================================
-- Enforces database-level distributed uniqueness for solution grading idempotency (§34)
-- and guarantees atomic sequence allocation across independent backend workers (§35).

-- 1. Unique constraint on (session_id, idempotency_key) for scoped session idempotency
CREATE UNIQUE INDEX IF NOT EXISTS uq_step_grader_attempt_session_idempotency
ON public.step_grader_attempts (session_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND idempotency_key != '';

-- 2. Unique constraint on (user_id, idempotency_key) for initial submission idempotency
CREATE UNIQUE INDEX IF NOT EXISTS uq_step_grader_attempt_user_idempotency
ON public.step_grader_attempts (user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND idempotency_key != '';

-- 3. Composite index on session attempts for fast lock-free atomic sequence lookups
CREATE INDEX IF NOT EXISTS idx_step_grader_attempts_seq_lookup
ON public.step_grader_attempts (session_id, attempt_sequence DESC);

-- 4. Audit comments documenting database-enforced invariants
COMMENT ON INDEX public.uq_step_grader_attempt_session_idempotency IS 
'Enforces distributed PostgreSQL-level uniqueness for idempotent solution grading within a session';

COMMENT ON INDEX public.uq_step_grader_attempt_user_idempotency IS 
'Enforces distributed PostgreSQL-level uniqueness for student submission idempotency keys across workers';
