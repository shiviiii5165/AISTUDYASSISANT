-- ============================================================================
-- LearnByGenie — Migration 026: Adaptive Practice Engine
-- ============================================================================
-- Feature 6: Dynamic Skill-Driven Question Selection & Learning Loop
--
-- Establishes:
--   1. practice_policy_versions: Config-driven, versioned selection & adaptation policies
--   2. practice_items: Verified question bank items with provenance, difficulty, hints & mistake mappings
--   3. practice_sessions: Durable session state, optimistic concurrency sequence locking
--   4. practice_responses: Authoritative student response telemetry with idempotency constraints
--
-- RLS Policy:
--   Students can SELECT only their own practice sessions and responses.
--   Active practice items and policy configurations are readable by authenticated users.
--   All mutations are server-authoritative via verified backend service layer.
-- ============================================================================

-- ─── 1. practice_policy_versions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.practice_policy_versions (
  version TEXT PRIMARY KEY,                       -- e.g. '1.0.0'
  policy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── 2. practice_items ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.practice_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  subject TEXT NOT NULL,
  grade_band TEXT NOT NULL DEFAULT 'secondary',    -- 'primary', 'middle', 'secondary', 'senior_secondary', 'ug'
  difficulty_band TEXT NOT NULL DEFAULT 'STANDARD',-- 'FOUNDATIONAL', 'STANDARD', 'ADVANCED'
  question_type TEXT NOT NULL DEFAULT 'mcq',       -- 'mcq', 'numeric', 'short_answer'
  prompt TEXT NOT NULL,
  options JSONB NOT NULL DEFAULT '[]'::jsonb,      -- MCQ options list
  correct_answer JSONB NOT NULL,                   -- SERVER-ONLY authoritative answer
  explanation TEXT NOT NULL DEFAULT '',            -- SERVER-ONLY educational rationale before submission
  hints JSONB NOT NULL DEFAULT '[]'::jsonb,        -- Structured hint ladder
  provenance TEXT NOT NULL DEFAULT 'CURATED',      -- 'CURATED', 'TEACHER_VERIFIED', 'APPROVED_BANK', 'VERIFIED_GENERATED', 'LICENSED'
  verification_status TEXT NOT NULL DEFAULT 'VERIFIED', -- 'VERIFIED', 'PENDING', 'REJECTED'
  language TEXT NOT NULL DEFAULT 'english',
  target_mistake_types JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g. ['SIGN_OR_NOTATION', 'CALCULATION']
  discrimination_index NUMERIC(4,2) DEFAULT 0.50,
  status TEXT NOT NULL DEFAULT 'active',           -- 'active', 'archived'
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_practice_items_skill ON public.practice_items(skill_id);
CREATE INDEX IF NOT EXISTS idx_practice_items_subject ON public.practice_items(subject);
CREATE INDEX IF NOT EXISTS idx_practice_items_grade_diff ON public.practice_items(grade_band, difficulty_band);
CREATE INDEX IF NOT EXISTS idx_practice_items_status ON public.practice_items(status, verification_status);

-- ─── 3. practice_sessions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.practice_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'ADAPTIVE',           -- 'ADAPTIVE', 'FOCUSED', 'REPAIR', 'EXAM_PRACTICE'
  curriculum TEXT NOT NULL DEFAULT 'CBSE',
  exam_track TEXT NOT NULL DEFAULT 'Boards',       -- 'Boards', 'JEE', 'NEET', 'Foundation', 'UG'
  enrolled_grade INT NOT NULL DEFAULT 10,
  grade_band TEXT NOT NULL DEFAULT 'secondary',
  requested_skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  current_skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  current_item_id UUID REFERENCES public.practice_items(id) ON DELETE SET NULL,
  
  -- Optimistic sequence version for concurrency and multi-tab divergence protection
  question_index INT NOT NULL DEFAULT 0,
  question_budget INT NOT NULL DEFAULT 10,
  current_difficulty TEXT NOT NULL DEFAULT 'STANDARD',
  consecutive_correct INT NOT NULL DEFAULT 0,
  consecutive_incorrect INT NOT NULL DEFAULT 0,
  active_hints_used INT NOT NULL DEFAULT 0,
  policy_version TEXT NOT NULL DEFAULT '1.0.0',

  status TEXT NOT NULL DEFAULT 'IN_PROGRESS',      -- 'IN_PROGRESS', 'PAUSED', 'COMPLETED', 'ABANDONED'
  asked_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  skills_practiced JSONB NOT NULL DEFAULT '[]'::jsonb,
  selection_context JSONB NOT NULL DEFAULT '{}'::jsonb,

  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_practice_sessions_user ON public.practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_status ON public.practice_sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_subject ON public.practice_sessions(user_id, subject);

-- ─── 4. practice_responses ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.practice_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.practice_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  item_id UUID REFERENCES public.practice_items(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT NOT NULL,
  question_index INT NOT NULL,                     -- Sequence index in session (0-indexed)
  student_response JSONB NOT NULL,
  correctness BOOLEAN NOT NULL,
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT', -- 'INDEPENDENT', 'PARTIALLY_ASSISTED', 'HINT_ASSISTED', 'FULLY_ASSISTED'
  difficulty_band TEXT NOT NULL DEFAULT 'STANDARD',
  response_time_ms INT NOT NULL DEFAULT 0,
  attempt_sequence INT NOT NULL DEFAULT 1,
  selection_reason TEXT NOT NULL DEFAULT '',
  selection_category TEXT NOT NULL DEFAULT '',
  hints_requested INT NOT NULL DEFAULT 0,
  provenance TEXT NOT NULL DEFAULT 'CURATED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Strict session sequence idempotency: one logical answer per question index in session
  CONSTRAINT uq_practice_session_q_index UNIQUE (session_id, question_index),
  -- Strict retry idempotency: duplicate network submission cannot double-record
  CONSTRAINT uq_practice_response_attempt UNIQUE (session_id, item_id, attempt_sequence)
);

CREATE INDEX IF NOT EXISTS idx_practice_responses_session ON public.practice_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_practice_responses_user ON public.practice_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_responses_skill ON public.practice_responses(user_id, skill_id);

-- ─── 5. Row Level Security (RLS) ─────────────────────────────────────────────
ALTER TABLE public.practice_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.practice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.practice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.practice_responses ENABLE ROW LEVEL SECURITY;

-- Policy versions: readable by all authenticated users
CREATE POLICY p_policy_read ON public.practice_policy_versions
  FOR SELECT TO authenticated
  USING (is_active = true);

-- Practice items: active items readable by authenticated users
CREATE POLICY p_items_read ON public.practice_items
  FOR SELECT TO authenticated
  USING (status = 'active');

-- Practice sessions: students can only access their own sessions
CREATE POLICY p_sessions_user_read ON public.practice_sessions
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- Practice responses: students can only access their own responses
CREATE POLICY p_responses_user_read ON public.practice_responses
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- Service role full access
CREATE POLICY p_policy_service_all ON public.practice_policy_versions
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY p_items_service_all ON public.practice_items
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY p_sessions_service_all ON public.practice_sessions
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY p_responses_service_all ON public.practice_responses
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);
