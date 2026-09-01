-- backend/migrations/011_database_integrity_fix.sql

-- 1. ADD MISSING ON DELETE CASCADE TO FOREIGN KEYS
-- We must first drop the existing constraints to alter them.

-- course_graphs
ALTER TABLE course_graphs DROP CONSTRAINT IF EXISTS course_graphs_user_id_fkey;
ALTER TABLE course_graphs ADD CONSTRAINT course_graphs_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- learning_roadmaps
ALTER TABLE learning_roadmaps DROP CONSTRAINT IF EXISTS learning_roadmaps_user_id_fkey;
ALTER TABLE learning_roadmaps ADD CONSTRAINT learning_roadmaps_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


-- video_lessons
ALTER TABLE video_lessons DROP CONSTRAINT IF EXISTS video_lessons_user_id_fkey;
ALTER TABLE video_lessons ADD CONSTRAINT video_lessons_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- topic_decks
ALTER TABLE topic_decks DROP CONSTRAINT IF EXISTS topic_decks_user_id_fkey;
ALTER TABLE topic_decks ADD CONSTRAINT topic_decks_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- teach_sessions
ALTER TABLE teach_sessions DROP CONSTRAINT IF EXISTS teach_sessions_user_id_fkey;
ALTER TABLE teach_sessions ADD CONSTRAINT teach_sessions_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- quizzes (Update SET NULL to CASCADE for roadmaps)
ALTER TABLE quizzes DROP CONSTRAINT IF EXISTS quizzes_roadmap_id_fkey;
ALTER TABLE quizzes ADD CONSTRAINT quizzes_roadmap_id_fkey 
  FOREIGN KEY (roadmap_id) REFERENCES learning_roadmaps(id) ON DELETE CASCADE;

ALTER TABLE quizzes DROP CONSTRAINT IF EXISTS quizzes_stage_id_fkey;
ALTER TABLE quizzes ADD CONSTRAINT quizzes_stage_id_fkey 
  FOREIGN KEY (stage_id) REFERENCES roadmap_stages(id) ON DELETE CASCADE;


-- 2. ENFORCE STRICT ROW LEVEL SECURITY (RLS) POLICIES
-- Ensuring all user-owned tables strictly enforce tenant isolation.

CREATE POLICY "Strict user isolation for topic_decks" ON topic_decks
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Strict user isolation for video_lessons" ON video_lessons
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Strict user isolation for learning_roadmaps" ON learning_roadmaps
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Strict user isolation for course_graphs" ON course_graphs
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Strict user isolation for teach_sessions" ON teach_sessions
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Enforce inheritance for child tables (roadmap_stages inherits user_id via learning_roadmaps)
CREATE POLICY "Strict inheritance isolation for roadmap_stages" ON roadmap_stages
  FOR ALL USING (
    roadmap_id IN (SELECT id FROM learning_roadmaps WHERE user_id = auth.uid())
  );

CREATE POLICY "Strict inheritance isolation for quiz_questions" ON quiz_questions
  FOR ALL USING (
    quiz_id IN (SELECT id FROM quizzes WHERE owner_user_id = auth.uid())
  );


-- 3. QUERY OPTIMIZATION: B-TREE INDEXES FOR FKs & TENANT FILTERING
-- Critical for RLS performance and rapid API responses.

CREATE INDEX IF NOT EXISTS idx_topic_decks_user_id ON topic_decks(user_id);
CREATE INDEX IF NOT EXISTS idx_video_lessons_user_id ON video_lessons(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_roadmaps_user_id ON learning_roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_stages_roadmap_id ON roadmap_stages(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_course_graphs_user_id ON course_graphs(user_id);
CREATE INDEX IF NOT EXISTS idx_teach_sessions_user_id ON teach_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_owner_user_id ON quizzes(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_roadmap_id ON quizzes(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz_id ON quiz_attempts(quiz_id);
