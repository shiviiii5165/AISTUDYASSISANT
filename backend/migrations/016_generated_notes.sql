-- Migration 016: AI Notes Generation (V1)
-- Independent top-level Notes Generation feature for Class 3–12 learners.
-- Stores structured notes generated from topics or pedagogical lesson/tutoring contexts.

CREATE TABLE IF NOT EXISTS generated_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  
  title TEXT NOT NULL,
  topic TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT 'General',
  class_level TEXT NOT NULL DEFAULT 'Class 10',
  curriculum TEXT NOT NULL DEFAULT 'CBSE',
  language TEXT NOT NULL DEFAULT 'english',
  
  -- Mode: 'topic' | 'lesson_context'
  mode TEXT NOT NULL DEFAULT 'topic',
  
  -- Lineage / Context references (all nullable for independent topic notes)
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE SET NULL,
  stage_id TEXT,
  teach_session_id UUID REFERENCES teach_sessions(id) ON DELETE SET NULL,
  quiz_id UUID REFERENCES quizzes(id) ON DELETE SET NULL,
  deck_id UUID REFERENCES topic_decks(id) ON DELETE SET NULL,
  source_document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  
  -- Selected pedagogical structures (e.g. ["learning_notes", "flowchart", "remedial_notes"])
  selected_formats JSONB NOT NULL DEFAULT '["learning_notes"]'::jsonb,
  depth TEXT NOT NULL DEFAULT 'standard',
  difficulty TEXT NOT NULL DEFAULT 'standard',
  
  -- Canonical structured document payload (sections, visual specs, callouts)
  content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  -- Quality validation score & audit breakdown
  quality_score NUMERIC(5,2) DEFAULT 100.00,
  quality_report JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  -- Status: 'processing' | 'ready' | 'failed'
  status TEXT NOT NULL DEFAULT 'ready',
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Query optimization indexes
CREATE INDEX IF NOT EXISTS idx_generated_notes_user_id ON generated_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_notes_roadmap ON generated_notes(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_generated_notes_teach_session ON generated_notes(teach_session_id);
CREATE INDEX IF NOT EXISTS idx_generated_notes_quiz ON generated_notes(quiz_id);
CREATE INDEX IF NOT EXISTS idx_generated_notes_created_at ON generated_notes(created_at DESC);

-- Row-Level Security: Users can only view, insert, update, and delete their own notes
ALTER TABLE generated_notes ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'generated_notes' AND policyname = 'Users manage their own generated notes'
  ) THEN
    CREATE POLICY "Users manage their own generated notes" ON generated_notes
      FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;
