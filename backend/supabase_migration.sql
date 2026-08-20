-- Migration: Add fields for Google OAuth and Enhanced Profiling
-- Run this securely in your Supabase SQL Editor

ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS email TEXT,
ADD COLUMN IF NOT EXISTS avatar_url TEXT,
ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'email',
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- If needed, create an index to quickly lookup users by email
CREATE INDEX IF NOT EXISTS profiles_email_idx ON profiles (email);
