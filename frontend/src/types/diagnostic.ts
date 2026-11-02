/**
 * LearnByGenie — Adaptive Diagnostic & Actual-Level Detection Types (Feature 2)
 */

export type DiagnosticStage =
  | 'INITIALIZED'
  | 'ANCHOR'
  | 'BRANCH'
  | 'CONFIRMATION'
  | 'COMPLETED'
  | 'ABANDONED';

export type DiagnosticState =
  | 'NOT_ASSESSED'
  | 'NEEDS_REPAIR'
  | 'DEVELOPING'
  | 'SECURE'
  | 'FRAGILE';

export type ConfidenceClass =
  | 'LOW_EVIDENCE'
  | 'MODERATE_EVIDENCE'
  | 'HIGH_EVIDENCE';

export type OverallReadiness =
  | 'READY'
  | 'ON_TRACK'
  | 'PREREQUISITES_NEEDED';

export interface StudentItemView {
  id: string;
  skill_id: string;
  subject: string;
  grade_band: string;
  difficulty_band: string;
  question_type: string;
  prompt: string;
  options: string[];
  language: string;
  sequence_number: number;
  total_budget: number;
}

export interface DiagnosticSession {
  id: string;
  user_id: string;
  subject: string;
  curriculum: string;
  exam_track: string;
  enrolled_grade: number;
  starting_level: string;
  preferred_language: string;
  status: string;
  current_stage: DiagnosticStage;
  current_item_id: string | null;
  question_budget: number;
  questions_answered: number;
  asked_item_ids: string[];
  active_skill_ids: string[];
  engine_version: string;
  started_at?: string;
  completed_at?: string;
}

export interface Feature3SkillEvidence {
  skill_id: string;
  diagnostic_state: string;
  evidence_count: number;
  correct_count: number;
  confidence: string;
  source: string;
  diagnostic_session_id: string;
  timestamp: string;
  recommended_action: string;
}

export interface DiagnosticSkillResult {
  id?: string;
  result_id?: string;
  session_id: string;
  user_id: string;
  subject: string;
  skill_id: string;
  skill_code: string;
  skill_name: string;
  diagnostic_state: DiagnosticState;
  evidence_count: number;
  correct_count: number;
  confidence_class: ConfidenceClass;
  recommended_action: string;
  is_recommended_start: boolean;
  prerequisite_depth: number;
}

export interface DiagnosticResult {
  id: string;
  session_id: string;
  user_id: string;
  subject: string;
  enrolled_grade: number;
  exam_track: string;
  overall_readiness: OverallReadiness;
  operating_level_band: string;
  summary: string;
  total_items_answered: number;
  correct_items_count: number;
  skill_results: DiagnosticSkillResult[];
  prerequisite_gaps: string[];
  feature3_contract_payload: Feature3SkillEvidence[];
  engine_version: string;
  created_at?: string;
}

export interface DiagnosticStartRequest {
  subject: string;
  retake?: boolean;
}

export interface AnswerSubmissionRequest {
  item_id: string;
  student_response: any;
  response_time_ms?: number;
}

export interface DiagnosticStepResponse {
  session: DiagnosticSession;
  current_question?: StudentItemView | null;
  is_completed: boolean;
  result?: DiagnosticResult | null;
}
