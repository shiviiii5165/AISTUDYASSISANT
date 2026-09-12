-- Migration: 001_video_teacher_mastery_and_pilot.sql (also 019)
-- Purpose: Durable database persistence for TeachGenie AI Video Teacher
-- Tables: learner_mastery, pilot_sessions, doubt_sessions

-- 1. LEARNER MASTERY TABLE
CREATE TABLE IF NOT EXISTS learner_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_active_timestamp DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_learner_mastery_user_lesson UNIQUE (user_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_learner_mastery_lookup ON learner_mastery (user_id, lesson_id);
CREATE INDEX IF NOT EXISTS idx_learner_mastery_updated ON learner_mastery (updated_at DESC);

-- 2. PILOT SESSIONS TABLE
CREATE TABLE IF NOT EXISTS pilot_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    participant_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT 'REAL_LEARNER_EVALUATION',
    pre_score DOUBLE PRECISION,
    post_score DOUBLE PRECISION,
    delayed_score DOUBLE PRECISION,
    learning_gain DOUBLE PRECISION,
    normalized_gain DOUBLE PRECISION,
    session_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pilot_sessions_session_id ON pilot_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_pilot_sessions_participant ON pilot_sessions (participant_id);
CREATE INDEX IF NOT EXISTS idx_pilot_sessions_topic ON pilot_sessions (topic);
CREATE INDEX IF NOT EXISTS idx_pilot_sessions_provenance ON pilot_sessions (provenance);

-- 3. DOUBT SESSIONS TABLE
CREATE TABLE IF NOT EXISTS doubt_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doubt_session_id TEXT NOT NULL UNIQUE,
    lesson_id TEXT NOT NULL,
    current_focus_concept TEXT,
    unresolved_confusion TEXT,
    session_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doubt_sessions_sid ON doubt_sessions (doubt_session_id);
CREATE INDEX IF NOT EXISTS idx_doubt_sessions_lesson ON doubt_sessions (lesson_id);

-- 4. ROW LEVEL SECURITY (RLS)
ALTER TABLE learner_mastery ENABLE ROW LEVEL SECURITY;
ALTER TABLE pilot_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE doubt_sessions ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'learner_mastery' AND policyname = 'Allow service_role full access to learner_mastery'
    ) THEN
        CREATE POLICY "Allow service_role full access to learner_mastery" ON learner_mastery
            FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated' OR auth.role() = 'anon');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'pilot_sessions' AND policyname = 'Allow service_role full access to pilot_sessions'
    ) THEN
        CREATE POLICY "Allow service_role full access to pilot_sessions" ON pilot_sessions
            FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated' OR auth.role() = 'anon');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'doubt_sessions' AND policyname = 'Allow service_role full access to doubt_sessions'
    ) THEN
        CREATE POLICY "Allow service_role full access to doubt_sessions" ON doubt_sessions
            FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated' OR auth.role() = 'anon');
    END IF;
END $$;
