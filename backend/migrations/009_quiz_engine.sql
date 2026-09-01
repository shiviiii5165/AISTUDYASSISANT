-- ============================================================================
-- TeachGenie — Quiz Engine (V1)
-- Run this ONCE in your Supabase SQL Editor (supabase.com → SQL Editor)
-- ============================================================================
-- Implements the canonical Quiz data model per the Quiz Engine Product
-- Decisions doc (§6, §7, §10, §23–§26, §41, §49, §53, §63).
--
-- Design notes:
--   * ONE canonical quiz concept (§1). `mode` ('teacher'|'student') and the
--     nullable owner/context columns distinguish teacher vs. student quizzes —
--     there is no second engine or second table family.
--   * This does NOT replace the existing `quiz_scores` table (006). That table
--     is the lightweight per-answer topic tracker written directly from the
--     frontend (scoreTracker.ts) and feeding weak-topic analysis. The new
--     `quiz_attempts` table is the authoritative, server-scored attempt record
--     for the Quiz Engine. They coexist; we do not migrate or drop quiz_scores.
--   * Class/cohort support (§5, §9) is intentionally NOT built for V1, but the
--     nullable organization_id / course_id columns leave room to add it later
--     without a breaking migration.
--   * RLS is defined for defense-in-depth and for any direct frontend Supabase
--     access (lib/supabase.ts), even though the backend uses the service-role
--     key. Ownership is ALSO enforced in application code — RLS is not the only
--     line of defense (see security.md Coverage Notes).
-- ============================================================================

-- ─── quizzes ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  mode TEXT NOT NULL DEFAULT 'student',          -- 'teacher' | 'student'
  title TEXT NOT NULL DEFAULT 'Untitled Quiz',

  -- Optional context / lineage (all nullable — a topic-only quiz has none).
  organization_id UUID,                           -- reserved for V2 class/cohort
  course_id TEXT,
  lesson_id TEXT,
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE SET NULL,
  stage_id UUID REFERENCES roadmap_stages(id) ON DELETE SET NULL,
  teach_session_id TEXT,                           -- Teach Me → Test Me lineage

  -- Source provenance. `source_type` mirrors knowledge.SourceType; `source_ids`
  -- holds the pdf/ppt/doc ids the quiz was generated from (empty for topic-only).
  source_type TEXT NOT NULL DEFAULT 'topic',
  source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  topic TEXT,

  -- Lifecycle (§23). Teacher: draft|reviewed|published|archived.
  -- Student:  ready|attempted|completed.  One column, values disjoint by mode.
  status TEXT NOT NULL DEFAULT 'draft',
  version INT NOT NULL DEFAULT 1,                  -- §24 content version

  -- Generation config (§49): question_count, difficulty, types[], language,
  -- shuffle, timer_seconds, adaptive, etc. Stored whole so the cache key (§36)
  -- and regeneration can reconstruct exact intent.
  config JSONB NOT NULL DEFAULT '{}'::jsonb,

  -- Cache/lineage bookkeeping (§36). NULL for personalized/adaptive quizzes,
  -- which must never be shared across users.
  cache_key TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ─── quiz_questions ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE NOT NULL,

  question_text TEXT NOT NULL,
  type TEXT NOT NULL,                              -- mcq|tf|fill_blank|short_answer
  options JSONB NOT NULL DEFAULT '[]'::jsonb,      -- [] for tf/fill_blank/short_answer

  -- correct_answer is SERVER-ONLY authority (§10, §38). It is never trusted
  -- from the client and never shipped in the student-facing question payload.
  correct_answer JSONB NOT NULL,
  explanation TEXT DEFAULT '',

  difficulty TEXT NOT NULL DEFAULT 'medium',       -- easy|medium|hard
  bloom_level TEXT,                                -- nullable (schemas.BloomLevel)

  -- Pedagogy linkage (nullable — only set when generated from a plan/roadmap).
  objective_id TEXT,
  concept_id TEXT,
  misconception_id TEXT,

  -- Citation back to the source location (§18): page/slide/timestamp.
  source_ref JSONB,

  order_index INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ─── quiz_attempts ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

  status TEXT NOT NULL DEFAULT 'in_progress',      -- in_progress|submitted|expired

  started_at TIMESTAMPTZ DEFAULT now(),
  submitted_at TIMESTAMPTZ,
  -- Server-enforced deadline (§43). Grading past this is rejected/void.
  expires_at TIMESTAMPTZ,

  -- Scores are computed SERVER-SIDE only (§10, §38). A client-submitted score
  -- is never written here.
  score NUMERIC(5,2),                              -- 0.00–100.00
  correct_count INT,
  total_questions INT,
  time_spent_seconds INT,

  -- Per-question grading detail + per-concept rollup (fed to mastery, §30).
  per_question_results JSONB NOT NULL DEFAULT '[]'::jsonb,
  concept_performance JSONB NOT NULL DEFAULT '{}'::jsonb,

  -- Shuffle reconstruction (§41, §63): the seeds let the server reproduce the
  -- EXACT question/option order shown, so grading and review line up with what
  -- the student saw. Stored, not re-rolled.
  question_order_seed BIGINT NOT NULL DEFAULT 0,
  option_order_seed BIGINT NOT NULL DEFAULT 0,

  -- Idempotency (§55, §56): a repeated submit with the same key must not
  -- double-score. Unique per (quiz, user, key).
  idempotency_key TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ─── Indexes (query patterns from the Phase 2 API list) ──────────────────────
CREATE INDEX IF NOT EXISTS idx_quizzes_owner          ON quizzes(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_roadmap        ON quizzes(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_stage          ON quizzes(stage_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_cache_key      ON quizzes(cache_key);
CREATE INDEX IF NOT EXISTS idx_questions_quiz         ON quiz_questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_questions_quiz_order   ON quiz_questions(quiz_id, order_index);
CREATE INDEX IF NOT EXISTS idx_attempts_quiz          ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user          ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_quiz_user     ON quiz_attempts(quiz_id, user_id);

-- Idempotent submission guard (§55): at most one attempt per key per quiz+user.
CREATE UNIQUE INDEX IF NOT EXISTS uq_attempts_idempotency
  ON quiz_attempts(quiz_id, user_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE quizzes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts  ENABLE ROW LEVEL SECURITY;

-- Owner fully manages their own quizzes. (Student "assigned to take a quiz"
-- read access is handled server-side in V1; broadening this policy is a V2
-- concern once the class/cohort model lands.)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='quizzes' AND policyname='Owners manage their own quizzes') THEN
    CREATE POLICY "Owners manage their own quizzes" ON quizzes
      FOR ALL USING (auth.uid() = owner_user_id);
  END IF;
END $$;

-- Questions inherit ownership from their quiz.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='quiz_questions' AND policyname='Owners manage questions of their quizzes') THEN
    CREATE POLICY "Owners manage questions of their quizzes" ON quiz_questions
      FOR ALL USING (
        quiz_id IN (SELECT id FROM quizzes WHERE owner_user_id = auth.uid())
      );
  END IF;
END $$;

-- A user only ever sees/writes their OWN attempts.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='quiz_attempts' AND policyname='Users manage their own attempts') THEN
    CREATE POLICY "Users manage their own attempts" ON quiz_attempts
      FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;

-- ─── Done! ───────────────────────────────────────────────────────────────────
