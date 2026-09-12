-- Migration: Lesson Planner VNext Hardening (Production-Engineering Foundations)
-- Adds schemas for persistent student_concept_state, dual evidence idempotency,
-- canonical concepts catalog, and atomic compare-and-swap adaptation transaction.

-- 1. Persistent Student Concept State Layer
CREATE TABLE IF NOT EXISTS student_concept_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT NOT NULL,
  canonical_concept_id TEXT NOT NULL,
  curriculum_scope TEXT NOT NULL DEFAULT 'standard',
  curriculum_version TEXT NOT NULL DEFAULT '1.0',
  mastery_state TEXT NOT NULL DEFAULT 'unknown', -- mastered, likely_mastered, unknown, weak, blocking
  confidence NUMERIC(3,2) NOT NULL DEFAULT 0.50,
  evidence_count INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  last_evaluated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(student_id, canonical_concept_id, curriculum_scope, curriculum_version)
);

CREATE INDEX IF NOT EXISTS idx_student_concept_state_lookup
  ON student_concept_state(student_id, canonical_concept_id);
CREATE INDEX IF NOT EXISTS idx_student_concept_state_scope
  ON student_concept_state(curriculum_scope, curriculum_version);

-- 2. Dual Evidence Idempotency & Canonical Concept Columns on learning_evidence
ALTER TABLE learning_evidence
  ADD COLUMN IF NOT EXISTS event_id TEXT,
  ADD COLUMN IF NOT EXISTS question_id TEXT,
  ADD COLUMN IF NOT EXISTS canonical_concept_id TEXT,
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- Preferred unique constraint: stable event_id when provided
CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_evidence_event_id
  ON learning_evidence(event_id) WHERE event_id IS NOT NULL;

-- Deterministic fallback unique constraint: composite SHA-256 idempotency_key
CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_evidence_idempotency_key
  ON learning_evidence(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 3. Canonical Concepts Registry Catalog
CREATE TABLE IF NOT EXISTS canonical_concepts (
  canonical_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  domain TEXT NOT NULL,
  domain_family TEXT NOT NULL DEFAULT 'engineering',
  specialization TEXT,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  namespace TEXT NOT NULL DEFAULT 'core',
  version TEXT NOT NULL DEFAULT '1.0',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canonical_concepts_domain ON canonical_concepts(domain);

-- Seed canonical concepts baseline
INSERT INTO canonical_concepts (canonical_id, display_name, domain, domain_family, specialization, aliases, namespace)
VALUES
  ('cs.algo.dp.memoization', 'Dynamic Programming Memoization', 'computer_science', 'engineering', 'algorithms', '["dp memoization", "memoization table", "top-down dp", "recursive memoization"]'::jsonb, 'core'),
  ('cs.algo.dp.tabulation', 'Dynamic Programming Tabulation', 'computer_science', 'engineering', 'algorithms', '["dp tabulation", "bottom-up dp", "iterative dp"]'::jsonb, 'core'),
  ('cs.algo.graph.bfs', 'Breadth-First Search', 'computer_science', 'engineering', 'algorithms', '["bfs", "level order traversal", "breadth first search"]'::jsonb, 'core'),
  ('cs.algo.graph.dfs', 'Depth-First Search', 'computer_science', 'engineering', 'algorithms', '["dfs", "depth first search"]'::jsonb, 'core'),
  ('se.react.hooks', 'React Hooks and Component Lifecycle', 'software_engineering', 'engineering', 'web_frameworks', '["react hooks", "useeffect", "usestate", "custom hooks"]'::jsonb, 'core'),
  ('ece.comm.massive_mimo', 'Massive MIMO Beamforming', 'ece', 'engineering', 'communications', '["massive mimo", "multi-user mimo", "beamforming", "spatial multiplexing"]'::jsonb, 'core'),
  ('math.algebra.quadratic', 'Quadratic Equations & Roots', 'mathematics', 'sciences', 'algebra', '["quadratic equations", "quadratic formula", "roots of quadratic"]'::jsonb, 'core'),
  ('bio.botany.photosynthesis', 'Photosynthesis Light & Dark Reactions', 'biology', 'sciences', 'botany', '["photosynthesis", "calvin cycle", "light reactions"]'::jsonb, 'core')
ON CONFLICT (canonical_id) DO NOTHING;

-- 4. Extend learning_roadmaps with current_version column
ALTER TABLE learning_roadmaps
  ADD COLUMN IF NOT EXISTS current_version INT DEFAULT 1;

-- 5. Canonical Adaptations View
CREATE OR REPLACE VIEW lesson_adaptations AS
  SELECT id, roadmap_id, version, change_reason, trigger_source, diff_summary, approved_by_teacher, created_at
  FROM lesson_plan_versions;

-- 6. Atomic Plan-Version CAS + Snapshot + Adaptation Transaction RPC
CREATE OR REPLACE FUNCTION apply_lesson_adaptation_atomic(
  p_roadmap_id UUID,
  p_expected_version INT,
  p_change_reason TEXT,
  p_trigger_source TEXT,
  p_trigger_evidence JSONB,
  p_diff_summary JSONB,
  p_roadmap_snapshot JSONB,
  p_approved BOOLEAN DEFAULT true
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
  v_new_version INT;
BEGIN
  -- 1. Atomic Compare-And-Swap on learning_roadmaps
  UPDATE learning_roadmaps
  SET current_version = current_version + 1,
      updated_at = now()
  WHERE id = p_roadmap_id
    AND current_version = p_expected_version
  RETURNING current_version INTO v_new_version;

  -- If CAS failed (version mismatch or deleted roadmap), raise conflict
  IF v_new_version IS NULL THEN
    RAISE EXCEPTION 'VERSION_CONFLICT: Expected version % does not match current plan version.', p_expected_version;
  END IF;

  -- 2. Persist version snapshot and adaptation audit record in same transaction
  INSERT INTO lesson_plan_versions (
    roadmap_id,
    version,
    change_reason,
    trigger_source,
    trigger_evidence_summary,
    diff_summary,
    roadmap_snapshot,
    approved_by_teacher
  ) VALUES (
    p_roadmap_id,
    v_new_version,
    p_change_reason,
    p_trigger_source,
    p_trigger_evidence,
    p_diff_summary,
    p_roadmap_snapshot,
    p_approved
  );

  RETURN v_new_version;
END;
$$;

-- 7. Row Level Security for student_concept_state & canonical_concepts
ALTER TABLE student_concept_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_concepts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read on canonical_concepts" ON canonical_concepts FOR SELECT USING (true);
CREATE POLICY "Users access own student concept state" ON student_concept_state
  FOR ALL USING (
    student_id = auth.uid()::text OR auth.role() = 'service_role'
  );
