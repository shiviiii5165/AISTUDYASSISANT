-- Migration: Topic Decks & Monthly Usage
-- Creates the topic_decks table and usage tracking for the Pro limit

CREATE TABLE IF NOT EXISTS topic_decks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  topic TEXT NOT NULL,
  depth TEXT NOT NULL DEFAULT 'full',
  audience TEXT NOT NULL DEFAULT 'university',
  status TEXT NOT NULL DEFAULT 'processing', -- processing | ready | failed
  storage_path TEXT,
  slide_count INT,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE topic_decks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own decks" ON topic_decks
  FOR ALL USING (auth.uid() = user_id);

-- Cache table for generated decks
CREATE TABLE IF NOT EXISTS deck_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  depth TEXT NOT NULL,
  audience TEXT NOT NULL,
  deck_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(topic, depth, audience)
);

-- Monthly usage tracking for the 15/month Pro limit
CREATE TABLE IF NOT EXISTS monthly_deck_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  usage_month DATE NOT NULL, -- Stored as the first day of the month (e.g. 2026-08-01)
  decks_generated INTEGER NOT NULL DEFAULT 0,
  UNIQUE(user_id, usage_month)
);

ALTER TABLE monthly_deck_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own monthly usage" ON monthly_deck_usage
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own monthly usage" ON monthly_deck_usage
  FOR ALL USING (auth.uid() = user_id);

-- Atomic increment-and-check function for monthly decks
CREATE OR REPLACE FUNCTION increment_monthly_deck_usage(p_user_id UUID, p_limit INT)
RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
  current_count INT;
  current_month DATE := date_trunc('month', CURRENT_DATE)::DATE;
BEGIN
  INSERT INTO monthly_deck_usage (user_id, usage_month, decks_generated)
  VALUES (p_user_id, current_month, 1)
  ON CONFLICT (user_id, usage_month)
  DO UPDATE SET decks_generated = monthly_deck_usage.decks_generated + 1
  RETURNING decks_generated INTO current_count;

  RETURN current_count <= p_limit;
END;
$$;
