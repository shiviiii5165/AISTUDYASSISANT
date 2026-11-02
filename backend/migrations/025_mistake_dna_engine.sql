-- ============================================================================
-- LearnByGenie — Migration 025: Mistake DNA Engine
-- ============================================================================
-- Feature 5: Persistent Error Intelligence & Repair Memory
--
-- Establishes:
--   1. mistake_events: Immutable ledger of detected student learning errors
--   2. mistake_patterns: Aggregated error patterns (ISOLATED, RECURRING, PERSISTENT, REPAIRED)
--   3. mistake_repair_events: Verifiable educational repair evidence ledger
--
-- RLS Policy:
--   Students can SELECT only their own Mistake DNA records.
--   Direct client writes/mutations are prohibited.
--   All mutations are performed server-side via backend intelligence services.
-- ============================================================================

-- ─── 1. mistake_events (Immutable Error Occurrence Ledger) ───────────────────
CREATE TABLE IF NOT EXISTS public.mistake_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE SET NULL,
  subject TEXT NOT NULL DEFAULT 'Mathematics',

  -- Source identification
  source_type TEXT NOT NULL, -- 'DIAGNOSTIC', 'TUTOR_CHECK', 'QUIZ', 'PRACTICE', 'TRANSFER_CHECK', 'STEP_GRADER', 'SIMULATION', 'REVISION'
  source_record_id TEXT NOT NULL,
  question_reference TEXT NOT NULL DEFAULT '',

  -- Canonical taxonomy classification
  primary_error_type TEXT NOT NULL, -- 'CONCEPTUAL', 'PROCEDURAL', 'CALCULATION', 'SIGN_OR_NOTATION', 'FORMULA_RECALL', 'MISREAD_QUESTION', 'UNIT_OR_DIMENSION', 'REASONING', 'MEMORY_RECALL', 'INCOMPLETE_RESPONSE', 'UNKNOWN'
  secondary_error_types JSONB NOT NULL DEFAULT '[]'::jsonb,
  error_subtype TEXT NOT NULL DEFAULT '',
  error_summary TEXT NOT NULL DEFAULT '',

  -- Pedagogical confidence & assistance context
  confidence_class TEXT NOT NULL DEFAULT 'MODERATE', -- 'LOW', 'MODERATE', 'HIGH'
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT', -- 'INDEPENDENT', 'HINT_ASSISTED', 'PARTIALLY_ASSISTED', 'FULLY_ASSISTED'

  -- Repair state tracking
  repair_status TEXT NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'IN_REPAIR', 'REPAIRED', 'REASSESSMENT_NEEDED'

  -- Engine & Classifier provenance
  engine_version TEXT NOT NULL DEFAULT '5.0.0',
  classifier_version TEXT NOT NULL DEFAULT '5.0.0',

  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Strict Idempotency: Same source record cannot create duplicate mistake events for the same skill
  CONSTRAINT uq_mistake_event_source UNIQUE (user_id, source_type, source_record_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_mistake_events_user ON public.mistake_events(user_id);
CREATE INDEX IF NOT EXISTS idx_mistake_events_skill ON public.mistake_events(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_mistake_events_type ON public.mistake_events(user_id, primary_error_type);
CREATE INDEX IF NOT EXISTS idx_mistake_events_detected ON public.mistake_events(user_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_mistake_events_repair_status ON public.mistake_events(user_id, repair_status);

-- ─── 2. mistake_patterns (Aggregated Error Patterns) ─────────────────────────
CREATE TABLE IF NOT EXISTS public.mistake_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES public.diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL DEFAULT 'Mathematics',

  -- Pattern categorization
  error_type TEXT NOT NULL, -- Canonical primary error type
  error_subtype TEXT NOT NULL DEFAULT '', -- Domain-specific subtype (e.g. 'sign_transposition')

  -- Progression telemetry
  occurrence_count INT NOT NULL DEFAULT 1 CHECK (occurrence_count >= 1),
  recent_occurrence_count INT NOT NULL DEFAULT 1 CHECK (recent_occurrence_count >= 0),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Pattern state machine: 'ISOLATED' -> 'RECURRING' -> 'PERSISTENT' -> 'REPAIRED'
  pattern_status TEXT NOT NULL DEFAULT 'ISOLATED',
  confidence TEXT NOT NULL DEFAULT 'MODERATE', -- 'LOW', 'MODERATE', 'HIGH'

  -- Repair tracking
  repair_status TEXT NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'IN_REPAIR', 'REPAIRED', 'REASSESSMENT_NEEDED'
  recommended_repair_action TEXT NOT NULL DEFAULT '',

  -- Prerequisite correlation
  likely_prerequisite_skill TEXT,
  prerequisite_signal TEXT,

  engine_version TEXT NOT NULL DEFAULT '5.0.0',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Unique Pattern Identity per user, skill, error type, and subtype
  CONSTRAINT uq_mistake_pattern UNIQUE (user_id, skill_id, error_type, error_subtype)
);

CREATE INDEX IF NOT EXISTS idx_mistake_patterns_user ON public.mistake_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_mistake_patterns_skill ON public.mistake_patterns(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_mistake_patterns_status ON public.mistake_patterns(user_id, pattern_status);
CREATE INDEX IF NOT EXISTS idx_mistake_patterns_repair ON public.mistake_patterns(user_id, repair_status);
CREATE INDEX IF NOT EXISTS idx_mistake_patterns_updated ON public.mistake_patterns(user_id, updated_at DESC);

-- ─── 3. mistake_repair_events (Educational Repair Evidence Ledger) ───────────
CREATE TABLE IF NOT EXISTS public.mistake_repair_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_id UUID REFERENCES public.mistake_patterns(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT NOT NULL,

  repair_action TEXT NOT NULL,
  evidence_source TEXT NOT NULL, -- 'DIAGNOSTIC', 'TUTOR_CHECK', 'PRACTICE', 'TRANSFER_CHECK', etc.
  evidence_record_id TEXT NOT NULL,
  assistance_level TEXT NOT NULL DEFAULT 'INDEPENDENT', -- Must be 'INDEPENDENT' to mark REPAIRED

  verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  engine_version TEXT NOT NULL DEFAULT '5.0.0',
  notes TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Idempotency: Same evidence record cannot repair the same pattern twice
  CONSTRAINT uq_mistake_repair_evidence UNIQUE (pattern_id, evidence_source, evidence_record_id)
);

CREATE INDEX IF NOT EXISTS idx_mistake_repairs_pattern ON public.mistake_repair_events(pattern_id);
CREATE INDEX IF NOT EXISTS idx_mistake_repairs_user ON public.mistake_repair_events(user_id);
CREATE INDEX IF NOT EXISTS idx_mistake_repairs_verified ON public.mistake_repair_events(user_id, verified_at DESC);

-- ─── 4. Row Level Security (RLS) ─────────────────────────────────────────────
ALTER TABLE public.mistake_events        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mistake_patterns      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mistake_repair_events ENABLE ROW LEVEL SECURITY;

-- Students can read only their own records
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'mistake_events' AND policyname = 'Students view own mistake events'
  ) THEN
    CREATE POLICY "Students view own mistake events" ON public.mistake_events
      FOR SELECT USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'mistake_patterns' AND policyname = 'Students view own mistake patterns'
  ) THEN
    CREATE POLICY "Students view own mistake patterns" ON public.mistake_patterns
      FOR SELECT USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'mistake_repair_events' AND policyname = 'Students view own mistake repairs'
  ) THEN
    CREATE POLICY "Students view own mistake repairs" ON public.mistake_repair_events
      FOR SELECT USING (auth.uid() = user_id);
  END IF;
END $$;

-- Prohibit direct student client writes: Mutations owned by backend intelligence services
-- Service role bypasses RLS and handles authoritative writes.

-- Notify PostgREST to reload schema cache immediately
NOTIFY pgrst, 'reload schema';
