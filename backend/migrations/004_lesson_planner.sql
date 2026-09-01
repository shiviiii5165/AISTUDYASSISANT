-- Migration: Lesson Planner 2.0 (Adaptive Learning Roadmap + Course Intelligence)
-- Creates the core tables for the course-to-classroom intelligence engine.

CREATE TABLE IF NOT EXISTS course_graphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  title TEXT NOT NULL,
  code TEXT,
  graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_roadmaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  course_id TEXT DEFAULT 'default_course',
  topic TEXT NOT NULL,
  title TEXT,
  description TEXT,
  level TEXT NOT NULL DEFAULT 'B.Tech',
  language TEXT NOT NULL DEFAULT 'hinglish',
  class_type TEXT NOT NULL DEFAULT 'Interactive Lecture',
  target_duration_minutes INT NOT NULL DEFAULT 60,
  status TEXT NOT NULL DEFAULT 'draft',
  next_best_action TEXT NOT NULL DEFAULT 'teach',
  overall_progress INT NOT NULL DEFAULT 0,
  health_score INT NOT NULL DEFAULT 100,
  course_coverage JSONB DEFAULT '{}'::jsonb,
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roadmap_stages (
  id TEXT PRIMARY KEY,
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  concept_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  duration_minutes INT NOT NULL DEFAULT 15,
  status TEXT NOT NULL DEFAULT 'locked',
  readiness TEXT NOT NULL DEFAULT 'blocked',
  mastery INT NOT NULL DEFAULT 0,
  confidence INT NOT NULL DEFAULT 0,
  stage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  order_index INT NOT NULL DEFAULT 0,
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roadmap_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  stage_id TEXT,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roadmap_resources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  stage_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'optional',
  usefulness_score NUMERIC(3,2) DEFAULT 0.5,
  resource_url TEXT,
  lineage_version INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast roadmap retrieval and stage operations
CREATE INDEX IF NOT EXISTS idx_roadmaps_user_id ON learning_roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_stages_roadmap_id ON roadmap_stages(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_events_roadmap_id ON roadmap_events(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_resources_stage_id ON roadmap_resources(stage_id);

-- Enable RLS
ALTER TABLE course_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_resources ENABLE ROW LEVEL SECURITY;

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

CREATE POLICY "Users manage their own roadmap events" ON roadmap_events
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage their own roadmap resources" ON roadmap_resources
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );
