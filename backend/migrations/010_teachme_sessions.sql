-- Migration: TeachMe Sessions
-- Creates persistence for the adaptive interactive teacher sessions.

CREATE TABLE IF NOT EXISTS teach_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  topic TEXT NOT NULL,
  level TEXT NOT NULL,
  mode TEXT NOT NULL,
  depth TEXT NOT NULL,
  plan_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_teach_sessions_user_id ON teach_sessions(user_id);

ALTER TABLE teach_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own teach sessions" ON teach_sessions
  FOR ALL USING (auth.uid() = user_id);
