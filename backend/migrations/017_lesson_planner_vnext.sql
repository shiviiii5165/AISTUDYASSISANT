-- Migration: Lesson Planner VNext (Evidence-Adaptive Teaching Operating System)
-- Adds schemas for Knowledge Packs, Curriculum Objectives, Resource Registry,
-- Learning Evidence, Misconception Catalog, Teacher Locks, and Plan Versioning.

-- 1. Knowledge Packs Table
CREATE TABLE IF NOT EXISTS knowledge_packs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT 'General',
  grade TEXT NOT NULL DEFAULT 'B.Tech',
  curriculum TEXT DEFAULT 'Standard',
  curriculum_version TEXT DEFAULT '1.0',
  language TEXT NOT NULL DEFAULT 'english',
  difficulty TEXT NOT NULL DEFAULT 'intermediate',
  source_hash TEXT,
  schema_version TEXT NOT NULL DEFAULT '2.0',
  pack_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_packs_topic ON knowledge_packs(topic);
CREATE INDEX IF NOT EXISTS idx_knowledge_packs_lookup ON knowledge_packs(topic, grade, curriculum, language);

-- 2. Curriculum Objectives Table
CREATE TABLE IF NOT EXISTS curriculum_objectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  curriculum_id TEXT NOT NULL,
  curriculum_version TEXT NOT NULL DEFAULT '1.0',
  board TEXT NOT NULL DEFAULT 'Standard',
  grade_level TEXT NOT NULL DEFAULT 'B.Tech',
  subject TEXT NOT NULL,
  topic TEXT NOT NULL,
  objective_code TEXT,
  objective_text TEXT NOT NULL,
  bloom_level TEXT NOT NULL DEFAULT 'understand',
  is_mandatory BOOLEAN NOT NULL DEFAULT true,
  prerequisite_codes JSONB DEFAULT '[]'::jsonb,
  depth_requirement TEXT DEFAULT 'standard',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curriculum_lookup ON curriculum_objectives(subject, topic, grade_level);

-- 3. Resource Sources Registry
CREATE TABLE IF NOT EXISTS resource_sources (
  source_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  authority_level INT NOT NULL DEFAULT 80,
  api_endpoint TEXT,
  ranking_method TEXT NOT NULL DEFAULT 'composite',
  freshness_requirement TEXT NOT NULL DEFAULT 'standard',
  requires_subscription BOOLEAN NOT NULL DEFAULT false,
  enabled BOOLEAN NOT NULL DEFAULT true,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed baseline sources
INSERT INTO resource_sources (source_id, domain, resource_type, authority_level, ranking_method, freshness_requirement, requires_subscription, enabled)
VALUES
  ('youtube_edu', 'all', 'video_segment', 85, 'segment_scoring', 'standard', false, true),
  ('arxiv_org', 'computer_science,physics,mathematics', 'research_paper', 92, 'citation_age_normalized', 'high', false, true),
  ('crossref_academic', 'all', 'journal_article', 95, 'quartile_indexed', 'standard', false, true),
  ('geeksforgeeks', 'computer_science,software_engineering', 'coding_reference', 88, 'concept_coverage', 'standard', false, true),
  ('leetcode', 'computer_science,software_engineering', 'coding_practice', 90, 'difficulty_progression', 'standard', false, true),
  ('official_docs', 'software_engineering,ece', 'official_docs', 98, 'version_freshness', 'strict', false, true),
  ('open_oer', 'all', 'textbook_reference', 85, 'pedagogical_alignment', 'standard', false, true)
ON CONFLICT (source_id) DO NOTHING;

-- 4. Learning Evidence Table
CREATE TABLE IF NOT EXISTS learning_evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT NOT NULL DEFAULT 'anonymous',
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE,
  stage_id TEXT,
  concept_id TEXT NOT NULL,
  objective_id TEXT,
  source_type TEXT NOT NULL, -- quiz, live_quiz, teach_me, checkpoint, observation
  source_id TEXT,
  correctness BOOLEAN NOT NULL,
  confidence NUMERIC(3,2) DEFAULT 0.80,
  attempt_number INT NOT NULL DEFAULT 1,
  response_time_seconds NUMERIC(5,2),
  misconception_candidate TEXT,
  raw_payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_learning_evidence_roadmap ON learning_evidence(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_learning_evidence_concept ON learning_evidence(concept_id);
CREATE INDEX IF NOT EXISTS idx_learning_evidence_student ON learning_evidence(student_id);

-- 5. Misconception Catalog Table
CREATE TABLE IF NOT EXISTS misconception_catalog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  concept_id TEXT NOT NULL,
  misconception_title TEXT NOT NULL,
  description TEXT NOT NULL,
  root_cause TEXT,
  recommended_pedagogy TEXT DEFAULT 'visualization',
  diagnostic_questions JSONB DEFAULT '[]'::jsonb,
  remediation_templates JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_misconception_concept ON misconception_catalog(concept_id);

-- 6. Student Misconceptions Tracking Table
CREATE TABLE IF NOT EXISTS student_misconceptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT NOT NULL,
  misconception_id UUID REFERENCES misconception_catalog(id) ON DELETE CASCADE,
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE,
  concept_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'suspected', -- suspected, confirmed, remediated, resolved
  confidence NUMERIC(3,2) DEFAULT 0.50,
  evidence_ids JSONB DEFAULT '[]'::jsonb,
  detected_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_student_misconceptions ON student_misconceptions(student_id, concept_id);

-- 7. Teacher Locks Table
CREATE TABLE IF NOT EXISTS teacher_locks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  stage_id TEXT,
  lock_type TEXT NOT NULL, -- objective, stage, duration, resource, assessment, activity
  target_identifier TEXT NOT NULL,
  is_locked BOOLEAN NOT NULL DEFAULT true,
  notes TEXT,
  locked_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_teacher_locks_roadmap ON teacher_locks(roadmap_id);

-- 8. Lesson Plan Versions & Recompile Audit Trail
CREATE TABLE IF NOT EXISTS lesson_plan_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roadmap_id UUID REFERENCES learning_roadmaps(id) ON DELETE CASCADE NOT NULL,
  version INT NOT NULL DEFAULT 1,
  change_reason TEXT NOT NULL DEFAULT 'Initial plan compilation',
  trigger_source TEXT NOT NULL DEFAULT 'user_request', -- user_request, diagnostic_check, live_quiz, teacher_edit
  trigger_evidence_summary JSONB DEFAULT '{}'::jsonb,
  diff_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  roadmap_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  approved_by_teacher BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plan_versions_roadmap ON lesson_plan_versions(roadmap_id, version);

-- 9. Extend learning_roadmaps with VNext metadata columns
ALTER TABLE learning_roadmaps
  ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'teacher_classroom',
  ADD COLUMN IF NOT EXISTS domain TEXT DEFAULT 'general_academic',
  ADD COLUMN IF NOT EXISTS intent TEXT DEFAULT 'teach',
  ADD COLUMN IF NOT EXISTS volatility TEXT DEFAULT 'low',
  ADD COLUMN IF NOT EXISTS knowledge_pack_id UUID REFERENCES knowledge_packs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS adaptive_reserve_minutes INT DEFAULT 0;

-- 10. Row Level Security (RLS)
ALTER TABLE knowledge_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE curriculum_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE misconception_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_misconceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE teacher_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_plan_versions ENABLE ROW LEVEL SECURITY;

-- Read policies for public/reference tables
CREATE POLICY "Public read on knowledge_packs" ON knowledge_packs FOR SELECT USING (true);
CREATE POLICY "Public read on curriculum_objectives" ON curriculum_objectives FOR SELECT USING (true);
CREATE POLICY "Public read on resource_sources" ON resource_sources FOR SELECT USING (true);
CREATE POLICY "Public read on misconception_catalog" ON misconception_catalog FOR SELECT USING (true);

-- User-scoped policies for workspace learning roadmaps
CREATE POLICY "Users access own learning evidence" ON learning_evidence
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users access own student misconceptions" ON student_misconceptions
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users manage own teacher locks" ON teacher_locks
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users access own lesson plan versions" ON lesson_plan_versions
  FOR ALL USING (
    roadmap_id IN (
      SELECT id FROM learning_roadmaps WHERE user_id = auth.uid()
    )
  );
