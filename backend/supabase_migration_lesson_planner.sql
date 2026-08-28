-- Migration: Lesson Planner 2.0 (Adaptive Learning Roadmap)
-- Creates the core tables for the course-to-classroom intelligence engine.

CREATE TABLE IF NOT EXISTS course_graphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  title TEXT NOT NULL,
  graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_roadmaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  course_id UUID REFERENCES course_graphs(id),
  topic TEXT NOT NULL,
  level TEXT NOT NULL,
  language TEXT NOT NULL,
  class_type TEXT NOT NULL,
  target_duration_minutes INT NOT NULL,
  next_best_action TEXT NOT NULL DEFAULT 'teach',
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roadmap_stages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  concept_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  duration_minutes INT NOT NULL,
  status TEXT NOT NULL DEFAULT 'locked',
  mastery INT NOT NULL DEFAULT 0,
  confidence INT NOT NULL DEFAULT 0,
  readiness BOOLEAN NOT NULL DEFAULT false,
  stage_json JSONB NOT NULL DEFAULT '{}'::jsonb, -- stores activities, prereqs, resources, etc.
  order_index INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policies
ALTER TABLE course_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_stages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own course graphs" ON course_graphs
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage their own learning roadmaps" ON learning_roadmaps
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage their own roadmap stages" ON roadmap_stages
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );
