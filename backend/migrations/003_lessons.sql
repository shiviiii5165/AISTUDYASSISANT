-- Migration: Video Lessons (GyanVideo AI)
-- Creates the video_lessons table for AI-generated lesson content

CREATE TABLE IF NOT EXISTS video_lessons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  topic TEXT NOT NULL,
  level TEXT NOT NULL DEFAULT 'Class 10',
  duration TEXT NOT NULL DEFAULT '5',
  language TEXT NOT NULL DEFAULT 'hinglish',
  status TEXT NOT NULL DEFAULT 'processing', -- processing | auditing | enhancing | ready | failed
  lesson_json JSONB,
  scene_count INT,
  total_duration_seconds INT,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE video_lessons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own lessons" ON video_lessons
  FOR ALL USING (auth.uid() = user_id);
