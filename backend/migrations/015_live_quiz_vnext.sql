-- ============================================================================
-- TeachGenie — Live Quiz VNEXT Scale, Monitoring & Security (015_live_quiz_vnext.sql)
-- ============================================================================
-- Additive migration for high-concurrency scale, participant snapshot tracking,
-- compact question stats, and immutable administrator action audit logging.
-- ============================================================================

-- ─── 1. Extend live_quiz_participants with Live State Snapshot ───────────────
ALTER TABLE live_quiz_participants
  ADD COLUMN IF NOT EXISTS current_question_index INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS answered_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS average_response_ms INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS connection_state TEXT DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS risk_score INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS risk_level TEXT DEFAULT 'low',
  ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS banned_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ban_reason TEXT,
  ADD COLUMN IF NOT EXISTS state_version INT DEFAULT 1;

-- Indexes for rapid participant filtering on host monitoring dashboard
CREATE INDEX IF NOT EXISTS idx_live_participants_banned
  ON live_quiz_participants(session_id, is_banned);
CREATE INDEX IF NOT EXISTS idx_live_participants_risk
  ON live_quiz_participants(session_id, risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_live_participants_conn
  ON live_quiz_participants(session_id, connection_state);

-- ─── 2. Compact Per-Question Aggregate Stats ─────────────────────────────────
-- Avoids expensive GROUP BY over raw responses table during host dashboard polls.
CREATE TABLE IF NOT EXISTS live_quiz_question_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES live_quiz_sessions(id) ON DELETE CASCADE NOT NULL,
  question_id TEXT NOT NULL,
  answered_count INT DEFAULT 0,
  correct_count INT DEFAULT 0,
  option_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
  average_response_ms INT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now(),

  CONSTRAINT uq_session_question_stats UNIQUE (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_live_qstats_session ON live_quiz_question_stats(session_id);

-- ─── 3. Immutable Administrator Action Audit Log ─────────────────────────────
-- All privileged moderation actions (BAN, UNBAN, PAUSE, REVEAL, etc.) are recorded.
CREATE TABLE IF NOT EXISTS live_quiz_admin_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  session_id UUID REFERENCES live_quiz_sessions(id) ON DELETE CASCADE NOT NULL,
  participant_id UUID REFERENCES live_quiz_participants(id) ON DELETE SET NULL,
  action TEXT NOT NULL,                         -- 'BAN' | 'UNBAN' | 'PAUSE' | 'RESUME' | 'REVEAL' | 'SKIP' | 'END'
  reason TEXT,
  previous_state JSONB NOT NULL DEFAULT '{}'::jsonb,
  new_state JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_actions_session ON live_quiz_admin_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_admin   ON live_quiz_admin_actions(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_part    ON live_quiz_admin_actions(participant_id);

-- ─── 4. Row Level Security for New Tables ────────────────────────────────────
ALTER TABLE live_quiz_question_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_quiz_admin_actions  ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_question_stats' AND policyname='Hosts view question stats of their sessions') THEN
    CREATE POLICY "Hosts view question stats of their sessions" ON live_quiz_question_stats
      FOR ALL USING (
        session_id IN (SELECT id FROM live_quiz_sessions WHERE host_user_id = auth.uid())
      );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_admin_actions' AND policyname='Hosts manage admin actions of their sessions') THEN
    CREATE POLICY "Hosts manage admin actions of their sessions" ON live_quiz_admin_actions
      FOR ALL USING (
        session_id IN (SELECT id FROM live_quiz_sessions WHERE host_user_id = auth.uid())
      );
  END IF;
END $$;
