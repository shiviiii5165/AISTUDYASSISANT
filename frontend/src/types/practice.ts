/**
 * LearnByGenie — Adaptive Practice Types (Feature 6)
 * ==================================================
 */

export type PracticeMode = 'ADAPTIVE' | 'FOCUSED' | 'REPAIR' | 'EXAM_PRACTICE';

export type DifficultyBand = 'FOUNDATIONAL' | 'STANDARD' | 'ADVANCED';

export type AssistanceLevel = 'INDEPENDENT' | 'PARTIALLY_ASSISTED' | 'HINT_ASSISTED' | 'FULLY_ASSISTED';

export type SelectionCategory =
  | 'PREREQUISITE_REPAIR'
  | 'MISTAKE_DNA_REPAIR'
  | 'DEVELOPING_SKILL'
  | 'READY_NEXT_SKILL'
  | 'SECURE_CONCEPT_CHECK'
  | 'EXPLORATORY_PROBE';

export interface StudentPracticeItemView {
  id: string;
  skill_id: string;
  subject: string;
  grade_band: string;
  difficulty_band: string;
  question_type: string;
  prompt: string;
  options: string[];
  sequence_number: number;
  total_budget: number;
  hints_total: number;
  hints_revealed: string[];
  selection_reason?: string | null;
}

export interface PracticeSession {
  id: string;
  user_id: string;
  subject: string;
  mode: PracticeMode;
  curriculum: string;
  exam_track: string;
  enrolled_grade: number;
  grade_band: string;
  requested_skill_id?: string | null;
  current_skill_id?: string | null;
  current_item_id?: string | null;
  question_index: number;
  question_budget: number;
  current_difficulty: DifficultyBand;
  consecutive_correct: number;
  consecutive_incorrect: number;
  active_hints_used: number;
  policy_version: string;
  status: 'IN_PROGRESS' | 'PAUSED' | 'COMPLETED' | 'ABANDONED';
  asked_item_ids: string[];
  skills_practiced: string[];
  selection_context: Record<string, any>;
  started_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface PracticeFeedback {
  session_id: string;
  item_id: string;
  skill_id: string;
  question_index: number;
  correctness: boolean;
  assistance_level: AssistanceLevel;
  authoritative_explanation: string;
  current_difficulty: DifficultyBand;
  session_completed: boolean;
  next_question_ready: boolean;
  mistake_pattern_detected?: string | null;
  repair_recorded: boolean;
}

export interface PracticeSelectionExplanation {
  item_id: string;
  skill_id: string;
  skill_name: string;
  category: SelectionCategory;
  reason: string;
  prerequisite_skill_id?: string | null;
  mistake_pattern_type?: string | null;
  difficulty: DifficultyBand;
}

export interface PracticeSkillOutcome {
  skill_id: string;
  skill_name: string;
  attempted: number;
  correct: number;
  independent: number;
}

export interface SessionSummary {
  session_id: string;
  user_id: string;
  subject: string;
  mode: PracticeMode;
  total_questions: number;
  correct_count: number;
  independent_correct_count: number;
  skills_practiced: PracticeSkillOutcome[];
  stronger_evidence_concepts: string[];
  developing_concepts: string[];
  mistake_patterns_encountered: string[];
  recommended_next_focus: string;
  duration_seconds: number;
}
