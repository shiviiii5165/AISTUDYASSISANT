-- Add plan columns to existing profiles table
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive',
  ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMPTZ;

-- New table to track daily question usage (needed to enforce the 20/day free limit)
CREATE TABLE IF NOT EXISTS daily_usage (
  id               UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  usage_date       DATE NOT NULL DEFAULT CURRENT_DATE,
  questions_asked  INTEGER NOT NULL DEFAULT 0,
  UNIQUE(user_id, usage_date)
);

ALTER TABLE daily_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own usage" ON daily_usage
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own usage" ON daily_usage
  FOR ALL USING (auth.uid() = user_id);

-- Atomic increment-and-check function — call this before answering any chat question
CREATE OR REPLACE FUNCTION increment_daily_usage(p_user_id UUID, p_limit INT)
RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
  current_count INT;
BEGIN
  INSERT INTO daily_usage (user_id, usage_date, questions_asked)
  VALUES (p_user_id, CURRENT_DATE, 1)
  ON CONFLICT (user_id, usage_date)
  DO UPDATE SET questions_asked = daily_usage.questions_asked + 1
  RETURNING questions_asked INTO current_count;

  RETURN current_count <= p_limit;
END;
$$;
