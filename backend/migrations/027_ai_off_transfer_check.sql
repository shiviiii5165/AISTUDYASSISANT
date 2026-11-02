-- ============================================================================
-- LearnByGenie — Migration 027: AI-Off Transfer Check Engine
-- ============================================================================
-- Feature 7: Independent Learning Verification Engine
--
-- Establishes:
--   1. transfer_policy_versions: Versioned configuration for independence checks
--   2. transfer_sessions: Durable, server-authoritative independent verification sessions
--   3. transfer_responses: Append-only independent evaluation evidence ledger
--
-- Guarantees:
--   - AI support is disabled during active attempts (assistance_level = INDEPENDENT)
--   - Reuses verified question infrastructure (practice_items)
--   - Database-level uniqueness for idempotent submissions and sequence locking
--   - Strict RLS ensuring cross-user isolation
-- ============================================================================

-- ─── 1. transfer_policy_versions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transfer_policy_versions (
  version TEXT PRIMARY KEY,                       -- e.g. '1.0.0'
  policy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── 2. transfer_sessions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transfer_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  subject TEXT NOT NULL,
  source_trigger TEXT NOT NULL DEFAULT 'PRACTICE_REPAIR', -- 'TUTOR_REPAIR', 'PRACTICE_REPAIR', 'MISTAKE_DNA_REPAIR', 'MASTERY_PROVISIONAL', 'STUDENT_REQUEST', 'MANUAL'
  source_trigger_id TEXT NOT NULL DEFAULT '',
  transfer_level TEXT NOT NULL DEFAULT 'NEAR_TRANSFER',   -- 'NEAR_TRANSFER', 'FAR_TRANSFER'
  policy_version TEXT NOT NULL DEFAULT '1.0.0',
  current_item_id UUID REFERENCES public.practice_items(id) ON DELETE SET NULL,

  status TEXT NOT NULL DEFAULT 'IN_PROGRESS',             -- 'PENDING', 'IN_PROGRESS', 'PASSED', 'NEEDS_MORE_EVIDENCE', 'ABORTED'
  question_index INT NOT NULL DEFAULT 0,
  question_budget INT NOT NULL DEFAULT 1,
  support_lock_active BOOLEAN NOT NULL DEFAULT true,      -- Server-side lock rejecting/invalidating AI support
  abort_reason TEXT DEFAULT NULL,
  trigger_explanation TEXT NOT NULL DEFAULT '',

  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ DEFAULT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_transfer_session_status CHECK (
    status IN ('PENDING', 'IN_PROGRESS', 'PASSED', 'NEEDS_MORE_EVIDENCE', 'ABORTED')
  ),
  CONSTRAINT chk_transfer_level CHECK (
    transfer_level IN ('NEAR_TRANSFER', 'FAR_TRANSFER')
  )
);

CREATE INDEX IF NOT EXISTS idx_transfer_sessions_user ON public.transfer_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_skill ON public.transfer_sessions(skill_id);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_status ON public.transfer_sessions(status);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_trigger ON public.transfer_sessions(source_trigger);

-- ─── 3. transfer_responses ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transfer_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.transfer_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  item_id UUID REFERENCES public.practice_items(id) ON DELETE SET NULL,
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  question_index INT NOT NULL DEFAULT 0,
  student_response JSONB NOT NULL,
  correctness BOOLEAN NOT NULL,
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT',
  attempt_sequence INT NOT NULL DEFAULT 1,
  response_time_ms INT NOT NULL DEFAULT 0,
  validator_result JSONB NOT NULL DEFAULT '{}'::jsonb,
  transfer_outcome TEXT NOT NULL DEFAULT 'PASSED',        -- 'PASSED', 'NEEDS_MORE_EVIDENCE', 'ABORTED'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_transfer_assistance_independent CHECK (
    assistance_level = 'INDEPENDENT'
  ),
  CONSTRAINT chk_transfer_outcome CHECK (
    transfer_outcome IN ('PASSED', 'NEEDS_MORE_EVIDENCE', 'ABORTED')
  ),
  CONSTRAINT uq_transfer_session_q_index UNIQUE (session_id, question_index),
  CONSTRAINT uq_transfer_response_attempt UNIQUE (session_id, item_id, attempt_sequence)
);

CREATE INDEX IF NOT EXISTS idx_transfer_responses_session ON public.transfer_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_transfer_responses_user ON public.transfer_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_transfer_responses_skill ON public.transfer_responses(skill_id);

-- ─── 4. ROW LEVEL SECURITY ────────────────────────────────────────────────────
ALTER TABLE public.transfer_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transfer_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transfer_responses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read transfer policy versions" ON public.transfer_policy_versions;
CREATE POLICY "Authenticated users can read transfer policy versions"
  ON public.transfer_policy_versions
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Students can view their own transfer sessions" ON public.transfer_sessions;
CREATE POLICY "Students can view their own transfer sessions"
  ON public.transfer_sessions
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Students can view their own transfer responses" ON public.transfer_responses;
CREATE POLICY "Students can view their own transfer responses"
  ON public.transfer_responses
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- ─── 5. INITIAL DEFAULT POLICY SEED ───────────────────────────────────────────
INSERT INTO public.transfer_policy_versions (version, policy_config, is_active, description)
VALUES (
  '1.0.0',
  '{
    "version": "1.0.0",
    "required_independence": "INDEPENDENT",
    "question_budget": 1,
    "allow_hints": false,
    "allow_tutor_help": false,
    "allow_answer_reveal": false,
    "cooldown_seconds_after_failure": 300,
    "require_novel_item": true,
    "support_near_transfer": true,
    "support_far_transfer": true,
    "pass_threshold_independent_correct": 1
  }'::jsonb,
  true,
  'Default canonical AI-off transfer verification policy'
)
ON CONFLICT (version) DO UPDATE SET
  policy_config = EXCLUDED.policy_config,
  is_active = EXCLUDED.is_active,
  description = EXCLUDED.description;
