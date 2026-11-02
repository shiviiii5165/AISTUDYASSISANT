-- ============================================================================
-- LearnByGenie — Migration 022: Adaptive Diagnostic & Actual-Level Detection Engine
-- ============================================================================
-- Feature 2: Subject, Domain, and Skill-Level Educational Readiness Assessment
--
-- Establishes:
--   1. diagnostic_domains: Broad subject domains (e.g. Algebra, Mechanics, Cell Biology)
--   2. diagnostic_skills: Granular skills with prerequisite references
--   3. diagnostic_items: Curated and verified diagnostic probes
--   4. diagnostic_sessions: Durable session state and adaptive progression
--   5. diagnostic_responses: Idempotent student attempt telemetry
--   6. diagnostic_results: Immutable diagnostic reports and operating band
--   7. diagnostic_skill_results: Per-skill evidence, states, and Feature 3 contract
-- ============================================================================

-- ─── 1. diagnostic_domains ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_domains (
  id TEXT PRIMARY KEY,                            -- e.g. 'MATH_ALGEBRA', 'PHY_MECHANICS'
  subject TEXT NOT NULL,                          -- 'Mathematics', 'Physics', etc.
  domain_name TEXT NOT NULL,
  description TEXT DEFAULT '',
  education_stage TEXT NOT NULL DEFAULT 'all',    -- 'primary', 'middle', 'secondary', 'senior_secondary', 'ug', 'all'
  order_index INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ─── 2. diagnostic_skills ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_skills (
  id TEXT PRIMARY KEY,                            -- e.g. 'MATH_LIN_EQ', 'PHY_VECTORS'
  domain_id TEXT REFERENCES diagnostic_domains(id) ON DELETE SET NULL,
  subject TEXT NOT NULL,
  skill_code TEXT NOT NULL UNIQUE,
  skill_name TEXT NOT NULL,
  grade_band TEXT NOT NULL,                       -- 'Class 3-5', 'Class 6-8', 'Class 9-10', 'Class 11-12', 'UG'
  min_grade INT NOT NULL DEFAULT 1,
  max_grade INT NOT NULL DEFAULT 12,
  curriculum_context TEXT NOT NULL DEFAULT 'all', -- 'all', 'cbse', 'icse', 'jee', 'neet', 'ug'
  prerequisite_skill_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  topic TEXT NOT NULL DEFAULT '',
  description TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diag_skills_subject ON diagnostic_skills(subject);
CREATE INDEX IF NOT EXISTS idx_diag_skills_domain  ON diagnostic_skills(domain_id);
CREATE INDEX IF NOT EXISTS idx_diag_skills_grades  ON diagnostic_skills(min_grade, max_grade);

-- ─── 3. diagnostic_items ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  grade_band TEXT NOT NULL,                       -- 'primary', 'middle', 'secondary', 'senior_secondary', 'ug'
  difficulty_band TEXT NOT NULL DEFAULT 'medium', -- 'easy', 'medium', 'hard'
  question_type TEXT NOT NULL DEFAULT 'mcq',      -- 'mcq', 'numeric', 'short_answer'
  prompt TEXT NOT NULL,
  options JSONB NOT NULL DEFAULT '[]'::jsonb,      -- MCQ options
  correct_answer JSONB NOT NULL,                  -- SERVER-ONLY authoritative answer
  explanation TEXT NOT NULL DEFAULT '',           -- Educational explanation
  provenance TEXT NOT NULL DEFAULT 'curated_bank',-- 'curated_bank', 'verified_item', 'teacher_reviewed'
  verification_status TEXT NOT NULL DEFAULT 'verified', -- 'verified', 'pending', 'rejected'
  language TEXT NOT NULL DEFAULT 'english',       -- 'english', 'hindi', 'hinglish', etc.
  discrimination_index NUMERIC(4,2) DEFAULT 0.50, -- item discrimination metadata
  status TEXT NOT NULL DEFAULT 'active',          -- 'active', 'archived'
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diag_items_skill      ON diagnostic_items(skill_id);
CREATE INDEX IF NOT EXISTS idx_diag_items_subject    ON diagnostic_items(subject);
CREATE INDEX IF NOT EXISTS idx_diag_items_grade_diff ON diagnostic_items(grade_band, difficulty_band);
CREATE INDEX IF NOT EXISTS idx_diag_items_status     ON diagnostic_items(status, verification_status);

-- ─── 4. diagnostic_sessions ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  curriculum TEXT NOT NULL DEFAULT 'CBSE',
  exam_track TEXT NOT NULL DEFAULT 'Boards',      -- 'Boards', 'JEE', 'NEET', 'Foundation', 'UG'
  enrolled_grade INT NOT NULL DEFAULT 10,
  starting_level TEXT NOT NULL DEFAULT 'standard',
  preferred_language TEXT NOT NULL DEFAULT 'english',
  
  -- Adaptive state machine: 'INITIALIZED' -> 'ANCHOR' -> 'BRANCH' -> 'CONFIRMATION' -> 'COMPLETED' / 'ABANDONED'
  status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
  current_stage TEXT NOT NULL DEFAULT 'ANCHOR',
  current_item_id UUID REFERENCES diagnostic_items(id) ON DELETE SET NULL,
  
  question_budget INT NOT NULL DEFAULT 10,
  questions_answered INT NOT NULL DEFAULT 0,
  asked_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  active_skill_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  
  engine_version TEXT NOT NULL DEFAULT '2.0.0',
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diag_sessions_user    ON diagnostic_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_diag_sessions_subject ON diagnostic_sessions(user_id, subject);
CREATE INDEX IF NOT EXISTS idx_diag_sessions_status  ON diagnostic_sessions(status);

-- ─── 5. diagnostic_responses ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES diagnostic_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  item_id UUID REFERENCES diagnostic_items(id) ON DELETE CASCADE NOT NULL,
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE SET NULL,
  
  student_response JSONB NOT NULL,
  is_correct BOOLEAN NOT NULL DEFAULT false,
  response_time_ms INT DEFAULT 0,
  attempt_number INT NOT NULL DEFAULT 1,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Idempotency constraint: A student cannot submit a duplicate response for the same item in a session
CREATE UNIQUE INDEX IF NOT EXISTS uq_diag_response_session_item
  ON diagnostic_responses(session_id, item_id);

CREATE INDEX IF NOT EXISTS idx_diag_responses_session ON diagnostic_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_diag_responses_user    ON diagnostic_responses(user_id);

-- ─── 6. diagnostic_results ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES diagnostic_sessions(id) ON DELETE CASCADE NOT NULL UNIQUE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  enrolled_grade INT NOT NULL,
  exam_track TEXT NOT NULL,
  
  overall_readiness TEXT NOT NULL DEFAULT 'ON_TRACK', -- 'READY', 'ON_TRACK', 'PREREQUISITES_NEEDED'
  operating_level_band TEXT NOT NULL,                 -- e.g. 'Class 8 algebra prerequisites'
  summary TEXT NOT NULL DEFAULT '',
  
  total_items_answered INT NOT NULL DEFAULT 0,
  correct_items_count INT NOT NULL DEFAULT 0,
  engine_version TEXT NOT NULL DEFAULT '2.0.0',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diag_results_user    ON diagnostic_results(user_id);
CREATE INDEX IF NOT EXISTS idx_diag_results_subject ON diagnostic_results(user_id, subject);

-- ─── 7. diagnostic_skill_results (Feature 3 Ingestion Contract) ──────────────
CREATE TABLE IF NOT EXISTS diagnostic_skill_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id UUID REFERENCES diagnostic_results(id) ON DELETE CASCADE NOT NULL,
  session_id UUID REFERENCES diagnostic_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subject TEXT NOT NULL,
  skill_id TEXT REFERENCES diagnostic_skills(id) ON DELETE CASCADE NOT NULL,
  
  -- Educational classification states
  diagnostic_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED', -- 'SECURE', 'DEVELOPING', 'NEEDS_REPAIR', 'FRAGILE', 'NOT_ASSESSED'
  evidence_count INT NOT NULL DEFAULT 0,
  correct_count INT NOT NULL DEFAULT 0,
  confidence_class TEXT NOT NULL DEFAULT 'LOW_EVIDENCE',  -- 'LOW_EVIDENCE', 'MODERATE_EVIDENCE', 'HIGH_EVIDENCE'
  
  recommended_action TEXT NOT NULL DEFAULT '',
  is_recommended_start BOOLEAN NOT NULL DEFAULT false,
  prerequisite_depth INT NOT NULL DEFAULT 0,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diag_skill_results_session ON diagnostic_skill_results(session_id);
CREATE INDEX IF NOT EXISTS idx_diag_skill_results_user    ON diagnostic_skill_results(user_id);
CREATE INDEX IF NOT EXISTS idx_diag_skill_results_skill   ON diagnostic_skill_results(skill_id);

-- ─── 8. Row Level Security ───────────────────────────────────────────────────
ALTER TABLE diagnostic_domains       ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_skills        ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_items         ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_sessions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_responses     ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_results       ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_skill_results ENABLE ROW LEVEL SECURITY;

-- Curricular taxonomy: Public read-only
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_domains' AND policyname='Allow public read diagnostic_domains') THEN
    CREATE POLICY "Allow public read diagnostic_domains" ON diagnostic_domains FOR SELECT USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_skills' AND policyname='Allow public read diagnostic_skills') THEN
    CREATE POLICY "Allow public read diagnostic_skills" ON diagnostic_skills FOR SELECT USING (true);
  END IF;
END $$;

-- Diagnostic items: Read active items (without leaking server-only answers via API client projection)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_items' AND policyname='Allow authenticated read active diagnostic_items') THEN
    CREATE POLICY "Allow authenticated read active diagnostic_items" ON diagnostic_items
      FOR SELECT TO authenticated USING (status = 'active' AND verification_status = 'verified');
  END IF;
END $$;

-- Student Session, Response, and Result isolation
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_sessions' AND policyname='Users manage own diagnostic sessions') THEN
    CREATE POLICY "Users manage own diagnostic sessions" ON diagnostic_sessions
      FOR ALL USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_responses' AND policyname='Users manage own diagnostic responses') THEN
    CREATE POLICY "Users manage own diagnostic responses" ON diagnostic_responses
      FOR ALL USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_results' AND policyname='Users see own diagnostic results') THEN
    CREATE POLICY "Users see own diagnostic results" ON diagnostic_results
      FOR ALL USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='diagnostic_skill_results' AND policyname='Users see own diagnostic skill results') THEN
    CREATE POLICY "Users see own diagnostic skill results" ON diagnostic_skill_results
      FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;
