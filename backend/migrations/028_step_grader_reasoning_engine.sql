-- ============================================================================
-- LearnByGenie — Migration 028: Step-Grader & Reasoning Diagnostics Engine
-- ============================================================================
-- Feature 8: First-Wrong-Step Detection + Explainable Solution Feedback
--
-- Establishes:
--   1. step_grader_policy_versions: Versioned configuration for step grading & evidence
--   2. step_grader_sessions: Durable, server-authoritative step grading sessions
--   3. step_grader_attempts: Versioned solution attempts with parent-child lineages
--   4. step_grader_steps: Canonical step-level validation records & error cascade ledger
--
-- Guarantees:
--   - First wrong step detection separating ROOT_ERROR from DOWNSTREAM_ERROR
--   - Exactly one canonical Mistake DNA event per root mistake (zero double counting)
--   - Server-authoritative validation (no client-side forged correctness)
--   - Strict RLS ensuring complete cross-user isolation
-- ============================================================================

-- ─── 1. step_grader_policy_versions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.step_grader_policy_versions (
  version TEXT PRIMARY KEY,                       -- e.g. '1.0.0'
  policy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed policy version 1.0.0
INSERT INTO public.step_grader_policy_versions (version, policy_config, is_active, description)
VALUES (
  '1.0.0',
  '{
    "min_confidence_for_mastery": "MODERATE",
    "require_all_steps_valid_for_positive_mastery": true,
    "root_error_submits_negative_mastery": true,
    "downstream_error_emits_mistake_event": false,
    "allow_unassisted_transfer_claim": false,
    "default_assistance_level": "INDEPENDENT"
  }'::jsonb,
  true,
  'Canonical Step-Grader policy v1.0.0: strict first-wrong-step, zero downstream double counting, assistance-aware evidence'
)
ON CONFLICT (version) DO UPDATE
SET policy_config = EXCLUDED.policy_config,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description;

-- ─── 2. step_grader_sessions ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.step_grader_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  source_type TEXT NOT NULL DEFAULT 'STUDENT_DIRECT', -- 'STUDENT_DIRECT', 'PRACTICE', 'TUTOR', 'ASSIGNMENT'
  source_record_id TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'ACTIVE',              -- 'ACTIVE', 'COMPLETED', 'ABORTED'
  total_attempts INT NOT NULL DEFAULT 1,
  policy_version TEXT NOT NULL DEFAULT '1.0.0',
  grader_version TEXT NOT NULL DEFAULT '8.0.0',

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_step_grader_session_status CHECK (
    status IN ('ACTIVE', 'COMPLETED', 'ABORTED')
  )
);

CREATE INDEX IF NOT EXISTS idx_step_grader_sessions_user ON public.step_grader_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_sessions_skill ON public.step_grader_sessions(skill_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_sessions_status ON public.step_grader_sessions(status);

-- ─── 3. step_grader_attempts ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.step_grader_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.step_grader_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  attempt_sequence INT NOT NULL DEFAULT 1,
  parent_attempt_id UUID REFERENCES public.step_grader_attempts(id) ON DELETE SET NULL,
  question_text TEXT NOT NULL DEFAULT '',
  raw_input TEXT NOT NULL,
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT',
  overall_outcome TEXT NOT NULL DEFAULT 'NEEDS_REVISION', -- 'ALL_STEPS_VALID', 'ROOT_ERROR_DETECTED', 'AMBIGUOUS_REASONING', 'UNRESOLVED'
  first_wrong_step_index INT DEFAULT NULL,
  validated_step_count INT NOT NULL DEFAULT 0,
  root_error_type TEXT DEFAULT NULL,
  root_error_subtype TEXT DEFAULT NULL,
  confidence_class TEXT NOT NULL DEFAULT 'HIGH',          -- 'HIGH', 'MODERATE', 'LOW'
  repair_recommendation TEXT NOT NULL DEFAULT '',
  idempotency_key TEXT NOT NULL DEFAULT '',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_step_grader_attempt_assistance CHECK (
    assistance_level IN ('INDEPENDENT', 'HINT_ASSISTED', 'PARTIALLY_ASSISTED', 'FULLY_ASSISTED')
  ),
  CONSTRAINT chk_step_grader_attempt_outcome CHECK (
    overall_outcome IN ('ALL_STEPS_VALID', 'ROOT_ERROR_DETECTED', 'AMBIGUOUS_REASONING', 'UNRESOLVED')
  ),
  CONSTRAINT chk_step_grader_confidence CHECK (
    confidence_class IN ('HIGH', 'MODERATE', 'LOW')
  ),
  CONSTRAINT uq_step_grader_attempt_sequence UNIQUE (session_id, attempt_sequence)
);

CREATE INDEX IF NOT EXISTS idx_step_grader_attempts_session ON public.step_grader_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_attempts_user ON public.step_grader_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_attempts_parent ON public.step_grader_attempts(parent_attempt_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_attempts_idempotency ON public.step_grader_attempts(user_id, idempotency_key);

-- ─── 4. step_grader_steps ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.step_grader_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID REFERENCES public.step_grader_attempts(id) ON DELETE CASCADE NOT NULL,
  session_id UUID REFERENCES public.step_grader_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  step_index INT NOT NULL,                               -- 1-based step order
  raw_text TEXT NOT NULL,
  normalized_expression TEXT NOT NULL DEFAULT '',
  step_type TEXT NOT NULL DEFAULT 'TRANSFORMATION',      -- 'SETUP', 'TRANSFORMATION', 'SUBSTITUTION', 'CALCULATION', 'RULE_APPLICATION', 'INFERENCE', 'CONCLUSION', 'EXPLANATION', 'UNKNOWN'
  validation_status TEXT NOT NULL DEFAULT 'VALID_STEP',  -- 'VALID_STEP', 'ROOT_ERROR', 'DOWNSTREAM_ERROR', 'INDEPENDENT_ERROR', 'UNCERTAIN'
  validator_type TEXT NOT NULL DEFAULT 'DETERMINISTIC',  -- 'DETERMINISTIC', 'DOMAIN_RULE', 'RUBRIC', 'SEMANTIC_LLM', 'UNCERTAIN'
  confidence TEXT NOT NULL DEFAULT 'HIGH',               -- 'HIGH', 'MODERATE', 'LOW'
  is_root_error BOOLEAN NOT NULL DEFAULT false,
  error_type TEXT DEFAULT NULL,                          -- Canonical Mistake DNA ErrorType
  error_subtype TEXT DEFAULT NULL,
  parent_step_index INT DEFAULT NULL,
  student_explanation TEXT DEFAULT NULL,
  feedback TEXT NOT NULL DEFAULT '',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_step_grader_step_type CHECK (
    step_type IN ('SETUP', 'TRANSFORMATION', 'SUBSTITUTION', 'CALCULATION', 'RULE_APPLICATION', 'INFERENCE', 'CONCLUSION', 'EXPLANATION', 'UNKNOWN')
  ),
  CONSTRAINT chk_step_grader_validation_status CHECK (
    validation_status IN ('VALID_STEP', 'ROOT_ERROR', 'DOWNSTREAM_ERROR', 'INDEPENDENT_ERROR', 'UNCERTAIN')
  ),
  CONSTRAINT chk_step_grader_validator_type CHECK (
    validator_type IN ('DETERMINISTIC', 'DOMAIN_RULE', 'RUBRIC', 'SEMANTIC_LLM', 'UNCERTAIN')
  ),
  CONSTRAINT uq_step_grader_attempt_step UNIQUE (attempt_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_step_grader_steps_attempt ON public.step_grader_steps(attempt_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_steps_session ON public.step_grader_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_steps_user ON public.step_grader_steps(user_id);
CREATE INDEX IF NOT EXISTS idx_step_grader_steps_status ON public.step_grader_steps(validation_status);
CREATE INDEX IF NOT EXISTS idx_step_grader_steps_root ON public.step_grader_steps(is_root_error);

-- ─── 5. ROW LEVEL SECURITY ────────────────────────────────────────────────────
ALTER TABLE public.step_grader_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.step_grader_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.step_grader_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.step_grader_steps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read step grader policy versions" ON public.step_grader_policy_versions;
CREATE POLICY "Authenticated users can read step grader policy versions"
  ON public.step_grader_policy_versions FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Students can read own step grader sessions" ON public.step_grader_sessions;
CREATE POLICY "Students can read own step grader sessions"
  ON public.step_grader_sessions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Students can read own step grader attempts" ON public.step_grader_attempts;
CREATE POLICY "Students can read own step grader attempts"
  ON public.step_grader_attempts FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Students can read own step grader steps" ON public.step_grader_steps;
CREATE POLICY "Students can read own step grader steps"
  ON public.step_grader_steps FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);
