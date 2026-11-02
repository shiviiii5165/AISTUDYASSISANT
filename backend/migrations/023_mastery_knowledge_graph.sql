-- ============================================================================
-- LearnByGenie — Migration 023: Mastery + Prerequisite Knowledge Graph
-- ============================================================================
-- Feature 3: Persistent, Explainable Student Knowledge Graph & Prerequisite DAG
--
-- Establishes:
--   1. skill_prerequisites: Database-driven Directed Acyclic Graph (DAG) edges
--   2. learner_skill_states: Per-student, per-skill persistent mastery & readiness state
--   3. learner_skill_evidence: Immutable, append-oriented learner evidence ledger
--   4. skill_curriculum_mappings: Cross-curriculum/grade mapping metadata
-- ============================================================================

-- ─── 1. skill_prerequisites ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skill_prerequisites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prerequisite_skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  dependent_skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  relationship_type TEXT NOT NULL DEFAULT 'STRICT_PREREQUISITE', -- 'STRICT_PREREQUISITE', 'ADVISORY_PREREQUISITE'
  is_active BOOLEAN NOT NULL DEFAULT true,
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- Prevent duplicate prerequisite edges
  CONSTRAINT uq_skill_prereq_edge UNIQUE (prerequisite_skill_id, dependent_skill_id),
  -- Self-dependency protection
  CONSTRAINT ck_no_self_prereq CHECK (prerequisite_skill_id <> dependent_skill_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_prereq_dependent ON skill_prerequisites(dependent_skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_prereq_prereq    ON skill_prerequisites(prerequisite_skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_prereq_active    ON skill_prerequisites(is_active);

-- ─── 2. learner_skill_states ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS learner_skill_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,

  -- Educational mastery states
  mastery_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED', -- 'NOT_ASSESSED', 'NEEDS_REPAIR', 'DEVELOPING', 'FRAGILE', 'SECURE'
  -- Separate prerequisite readiness state
  readiness_state TEXT NOT NULL DEFAULT 'NOT_ENOUGH_EVIDENCE', -- 'READY', 'PARTIALLY_READY', 'BLOCKED_BY_PREREQUISITE', 'NOT_ENOUGH_EVIDENCE'
  confidence_class TEXT NOT NULL DEFAULT 'LOW_EVIDENCE', -- 'LOW_EVIDENCE', 'MODERATE_EVIDENCE', 'HIGH_EVIDENCE'

  total_evidence_count INT NOT NULL DEFAULT 0,
  independent_evidence_count INT NOT NULL DEFAULT 0,
  correct_count INT NOT NULL DEFAULT 0,

  last_evidence_at TIMESTAMPTZ,
  last_independent_evidence_at TIMESTAMPTZ,
  review_status TEXT NOT NULL DEFAULT 'FRESH', -- 'FRESH', 'REVIEW_SOON', 'REASSESSMENT_DUE'

  state_version INT NOT NULL DEFAULT 1,
  engine_version TEXT NOT NULL DEFAULT '3.0.0',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- A learner has exactly one canonical state per skill
  CONSTRAINT uq_learner_skill_state UNIQUE (user_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_learner_skill_user_subj ON learner_skill_states(user_id, subject);
CREATE INDEX IF NOT EXISTS idx_learner_skill_mastery   ON learner_skill_states(user_id, mastery_state);
CREATE INDEX IF NOT EXISTS idx_learner_skill_readiness ON learner_skill_states(user_id, readiness_state);

-- ─── 3. learner_skill_evidence (Immutable Evidence Ledger) ───────────────────
CREATE TABLE IF NOT EXISTS learner_skill_evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  source_type TEXT NOT NULL, -- 'DIAGNOSTIC', 'PRACTICE', 'QUIZ', 'TUTOR_CHECK', 'REVISION', 'TRANSFER_CHECK', 'STEP_GRADER', 'SIMULATION'
  source_record_id TEXT NOT NULL, -- Stable source identity (e.g. diagnostic session ID or attempt ID)
  correctness BOOLEAN NOT NULL DEFAULT false,
  evidence_strength NUMERIC(3,2) NOT NULL DEFAULT 1.0,
  independence_level TEXT NOT NULL DEFAULT 'INDEPENDENT', -- 'INDEPENDENT', 'HINT_ASSISTED', 'PARTIALLY_ASSISTED', 'FULLY_ASSISTED'
  confidence_class TEXT NOT NULL DEFAULT 'MODERATE_EVIDENCE',
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  engine_version TEXT NOT NULL DEFAULT '3.0.0',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),

  -- Idempotency constraint: Same source record cannot submit evidence for the same skill multiple times
  CONSTRAINT uq_learner_evidence_source UNIQUE (user_id, source_type, source_record_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_learner_evidence_user_skill ON learner_skill_evidence(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_learner_evidence_occurred   ON learner_skill_evidence(user_id, occurred_at);

-- ─── 4. skill_curriculum_mappings ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skill_curriculum_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  curriculum TEXT NOT NULL DEFAULT 'CBSE', -- 'CBSE', 'ICSE', 'JEE', 'NEET', 'UG'
  grade_level INT NOT NULL DEFAULT 10,
  exam_relevance JSONB NOT NULL DEFAULT '[]'::jsonb,
  depth_level TEXT NOT NULL DEFAULT 'core',
  created_at TIMESTAMPTZ DEFAULT now(),

  CONSTRAINT uq_skill_curriculum UNIQUE (skill_id, curriculum, grade_level)
);

CREATE INDEX IF NOT EXISTS idx_skill_curriculum_skill ON skill_curriculum_mappings(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_curriculum_grade ON skill_curriculum_mappings(curriculum, grade_level);

-- ─── 5. Row Level Security ───────────────────────────────────────────────────
ALTER TABLE skill_prerequisites        ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_skill_states       ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_skill_evidence     ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_curriculum_mappings  ENABLE ROW LEVEL SECURITY;

-- Public / Authenticated Read for Taxonomy Graphs
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='skill_prerequisites' AND policyname='Allow public read skill_prerequisites') THEN
    CREATE POLICY "Allow public read skill_prerequisites" ON skill_prerequisites FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='skill_curriculum_mappings' AND policyname='Allow public read skill_curriculum_mappings') THEN
    CREATE POLICY "Allow public read skill_curriculum_mappings" ON skill_curriculum_mappings FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='learner_skill_states' AND policyname='Students view own skill states') THEN
    CREATE POLICY "Students view own skill states" ON learner_skill_states FOR SELECT USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='learner_skill_evidence' AND policyname='Students view own skill evidence') THEN
    CREATE POLICY "Students view own skill evidence" ON learner_skill_evidence FOR SELECT USING (auth.uid() = user_id);
  END IF;
END $$;


-- ─── 6. Seed Canonical Prerequisite Edges ────────────────────────────────────
INSERT INTO skill_prerequisites (prerequisite_skill_id, dependent_skill_id, relationship_type)
VALUES
  -- Mathematics Chain
  ('MATH_NUM_OPS',     'MATH_FRAC_DEC',     'STRICT_PREREQUISITE'),
  ('MATH_FRAC_DEC',    'MATH_RATIO_PROP',   'STRICT_PREREQUISITE'),
  ('MATH_NUM_OPS',     'MATH_ALG_EXP',      'STRICT_PREREQUISITE'),
  ('MATH_ALG_EXP',     'MATH_LIN_EQ',       'STRICT_PREREQUISITE'),
  ('MATH_LIN_EQ',      'MATH_QUAD_EQ',      'STRICT_PREREQUISITE'),
  ('MATH_ALG_EXP',     'MATH_QUAD_EQ',      'STRICT_PREREQUISITE'),
  ('MATH_QUAD_EQ',     'MATH_CALC_LIMITS',  'STRICT_PREREQUISITE'),
  ('MATH_CALC_LIMITS', 'MATH_DIFF_CALC',    'STRICT_PREREQUISITE'),

  -- Physics Chain
  ('PHY_MOTION_BASIC', 'PHY_NEWTON_LAWS',   'STRICT_PREREQUISITE'),
  ('PHY_VECTORS',      'PHY_ELECTROSTATICS','STRICT_PREREQUISITE'),
  ('PHY_NEWTON_LAWS',  'PHY_ELECTROSTATICS','STRICT_PREREQUISITE'),

  -- Chemistry Chain
  ('CHEM_ATOMIC_STRUCT','CHEM_BONDING',     'STRICT_PREREQUISITE'),

  -- Biology Chain
  ('BIO_CELL_UNIT',    'BIO_GENETICS',      'STRICT_PREREQUISITE'),

  -- Computer Science / UG Chain
  ('CS_BASIC_LOGIC',   'CS_DATA_STRUCT',    'STRICT_PREREQUISITE')
ON CONFLICT (prerequisite_skill_id, dependent_skill_id) DO NOTHING;
