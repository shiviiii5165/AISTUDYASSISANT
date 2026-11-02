-- ============================================================================
-- LearnByGenie — Migration 024: Personalized Socratic Tutor V2 Sessions
-- ============================================================================
-- Feature 4: Durable multi-turn session persistence, pedagogical state machine,
-- and Socratic understanding check ledger.
-- ============================================================================

-- ── 1. socratic_tutor_sessions ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.socratic_tutor_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  session_mode TEXT NOT NULL DEFAULT 'TUTOR', -- 'QUICK_ASK', 'TUTOR'
  target_subject TEXT NOT NULL DEFAULT 'Mathematics',
  target_skill_id TEXT,
  pedagogical_state TEXT NOT NULL DEFAULT 'ORIENT', -- 'ORIENT', 'EXPLAIN', 'CHECK', 'HINT', 'RETEACH', 'APPLY', 'WRAP_UP'
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT', -- 'INDEPENDENT', 'HINT_ASSISTED', 'PARTIALLY_ASSISTED', 'FULLY_ASSISTED'
  hint_level TEXT NOT NULL DEFAULT 'NONE', -- 'NONE', 'HINT_1', 'HINT_2', 'HINT_3', 'HINT_4', 'FULL_EXPLANATION'
  current_check JSONB, -- { "check_id", "question", "expected_answer", "check_type", "skill_id", "status", "idempotency_key" }
  source_references JSONB NOT NULL DEFAULT '[]'::jsonb, -- Bounded document citations / source metadata
  state_metadata JSONB NOT NULL DEFAULT '{}'::jsonb, -- misconceptions, hints_given, prerequisite_repair_active, history
  engine_version TEXT NOT NULL DEFAULT '2.0.0',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tutor_sessions_user ON public.socratic_tutor_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_tutor_sessions_updated ON public.socratic_tutor_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_tutor_sessions_skill ON public.socratic_tutor_sessions(user_id, target_skill_id);

-- Enable Row Level Security
ALTER TABLE public.socratic_tutor_sessions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'socratic_tutor_sessions' AND policyname = 'Students access own tutor sessions'
  ) THEN
    CREATE POLICY "Students access own tutor sessions" ON public.socratic_tutor_sessions
      FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;

-- ── 2. socratic_check_responses (Durable Check Ledger & Idempotency) ──────────
CREATE TABLE IF NOT EXISTS public.socratic_check_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.socratic_tutor_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  check_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  student_response TEXT NOT NULL,
  outcome TEXT NOT NULL, -- 'CORRECT', 'PARTIALLY_CORRECT', 'INCORRECT', 'UNCERTAIN'
  stem_verified BOOLEAN DEFAULT false,
  evidence_ingested BOOLEAN DEFAULT false,
  engine_version TEXT NOT NULL DEFAULT '2.0.0',
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_check_response_idempotency UNIQUE (session_id, check_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_check_responses_session ON public.socratic_check_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_check_responses_user ON public.socratic_check_responses(user_id);

ALTER TABLE public.socratic_check_responses ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'socratic_check_responses' AND policyname = 'Students access own check responses'
  ) THEN
    CREATE POLICY "Students access own check responses" ON public.socratic_check_responses
      FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;

-- Notify PostgREST to reload schema cache immediately
NOTIFY pgrst, 'reload schema';

