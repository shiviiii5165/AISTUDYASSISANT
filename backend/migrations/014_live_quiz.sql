-- ============================================================================
-- TeachGenie — Live Classroom Quiz Experience (014_live_quiz.sql)
-- ============================================================================
-- Additive tables for real-time live multiplayer quiz rooms.
-- Enforces:
--   * Partial unique index for join_code recycling (active rooms only)
--   * Zero-leakage RLS: host-only SELECT on live_quiz_sessions
--   * Strict participant response deduplication (session_id, participant_id, question_id)
--   * Audit event log with cascading delete from parent session
-- ============================================================================

-- ─── 1. live_quiz_sessions ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_quiz_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE NOT NULL,
  host_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  organization_id UUID,

  -- 6-digit numeric join code, unique among currently active sessions
  join_code TEXT NOT NULL,

  -- Lifecycle: CREATED -> LOBBY -> LIVE <-> PAUSED -> COMPLETED / ENDED / EXPIRED
  status TEXT NOT NULL DEFAULT 'CREATED',
  mode TEXT NOT NULL DEFAULT 'teacher_led',        -- 'teacher_led' | 'student_paced'

  current_question_index INT NOT NULL DEFAULT 0,
  current_question_started_at TIMESTAMPTZ,
  current_question_deadline TIMESTAMPTZ,
  total_questions INT NOT NULL DEFAULT 0,

  timer_config JSONB NOT NULL DEFAULT '{"enabled": true, "seconds": 30, "speed_bonus": false}'::jsonb,
  settings JSONB NOT NULL DEFAULT '{"sound_fx": true, "leaderboard_enabled": true, "show_correctness_immediately": true}'::jsonb,

  -- Frozen snapshot of all questions at launch (includes correct_answer for grading & audit)
  -- Strictly protected by Host-Only RLS. Students never receive raw rows.
  questions_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
  question_order JSONB NOT NULL DEFAULT '[]'::jsonb,

  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  version INT NOT NULL DEFAULT 1,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Partial unique index for recycling 6-digit join codes once rooms terminate
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_join_codes
  ON live_quiz_sessions (join_code)
  WHERE status IN ('CREATED', 'LOBBY', 'LIVE', 'PAUSED');

-- ─── 2. live_quiz_participants ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_quiz_participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES live_quiz_sessions(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- nullable for guest students

  display_name TEXT NOT NULL,
  avatar_seed TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active',          -- 'active' | 'disconnected' | 'left'

  joined_at TIMESTAMPTZ DEFAULT now(),
  connected_at TIMESTAMPTZ DEFAULT now(),
  disconnected_at TIMESTAMPTZ,

  score INT NOT NULL DEFAULT 0,
  correct_count INT NOT NULL DEFAULT 0,
  answered_count INT NOT NULL DEFAULT 0,
  streak INT NOT NULL DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ─── 3. live_quiz_responses ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_quiz_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES live_quiz_sessions(id) ON DELETE CASCADE NOT NULL,
  participant_id UUID REFERENCES live_quiz_participants(id) ON DELETE CASCADE NOT NULL,
  question_id TEXT NOT NULL,

  selected_option_id TEXT,
  submitted_at TIMESTAMPTZ DEFAULT now(),
  response_time_ms INT DEFAULT 0,

  is_correct BOOLEAN,
  points INT NOT NULL DEFAULT 0,
  attempt_number INT NOT NULL DEFAULT 1,

  concept_id TEXT,
  objective_id TEXT,
  idempotency_key TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),

  -- Guard against duplicate submission: at most one response per question per participant
  CONSTRAINT uq_participant_question_response UNIQUE (session_id, participant_id, question_id)
);

-- ─── 4. live_quiz_events ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_quiz_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES live_quiz_sessions(id) ON DELETE CASCADE NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_live_sessions_host         ON live_quiz_sessions(host_user_id);
CREATE INDEX IF NOT EXISTS idx_live_sessions_quiz         ON live_quiz_sessions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_live_sessions_status       ON live_quiz_sessions(status);
CREATE INDEX IF NOT EXISTS idx_live_participants_session  ON live_quiz_participants(session_id);
CREATE INDEX IF NOT EXISTS idx_live_participants_user     ON live_quiz_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_live_responses_session     ON live_quiz_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_live_responses_part        ON live_quiz_responses(participant_id);
CREATE INDEX IF NOT EXISTS idx_live_events_session        ON live_quiz_events(session_id);

-- ─── Row Level Security ──────────────────────────────────────────────────────
ALTER TABLE live_quiz_sessions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_quiz_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_quiz_responses    ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_quiz_events       ENABLE ROW LEVEL SECURITY;

-- Host-Only access to live_quiz_sessions (Answer Key Zero-Leakage Invariant)
-- Students NEVER query live_quiz_sessions directly; their state is served sanitized via FastAPI.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_sessions' AND policyname='Hosts manage their live sessions') THEN
    CREATE POLICY "Hosts manage their live sessions" ON live_quiz_sessions
      FOR ALL USING (auth.uid() = host_user_id);
  END IF;
END $$;

-- Host can view/manage participants of their sessions
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_participants' AND policyname='Hosts view participants of their sessions') THEN
    CREATE POLICY "Hosts view participants of their sessions" ON live_quiz_participants
      FOR ALL USING (
        session_id IN (SELECT id FROM live_quiz_sessions WHERE host_user_id = auth.uid())
      );
  END IF;
END $$;

-- Host can view responses in their sessions
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_responses' AND policyname='Hosts view responses of their sessions') THEN
    CREATE POLICY "Hosts view responses of their sessions" ON live_quiz_responses
      FOR ALL USING (
        session_id IN (SELECT id FROM live_quiz_sessions WHERE host_user_id = auth.uid())
      );
  END IF;
END $$;

-- Host can view audit events of their sessions
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='live_quiz_events' AND policyname='Hosts view events of their sessions') THEN
    CREATE POLICY "Hosts view events of their sessions" ON live_quiz_events
      FOR ALL USING (
        session_id IN (SELECT id FROM live_quiz_sessions WHERE host_user_id = auth.uid())
      );
  END IF;
END $$;
