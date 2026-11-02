/**
 * LearnByGenie — Feature 5: Mistake DNA Types
 * ===========================================
 * Canonical TypeScript interfaces for Mistake DNA Engine.
 * Describes learning errors, NOT student identity, weakness, or shame.
 */

export type ErrorType =
  | 'CONCEPTUAL'
  | 'PROCEDURAL'
  | 'CALCULATION'
  | 'SIGN_OR_NOTATION'
  | 'FORMULA_RECALL'
  | 'MISREAD_QUESTION'
  | 'UNIT_OR_DIMENSION'
  | 'REASONING'
  | 'MEMORY_RECALL'
  | 'INCOMPLETE_RESPONSE'
  | 'UNKNOWN';

export type PatternStatus = 'ISOLATED' | 'RECURRING' | 'PERSISTENT' | 'REPAIRED';

export type RepairStatus = 'OPEN' | 'IN_REPAIR' | 'REPAIRED' | 'REASSESSMENT_NEEDED';

export type ConfidenceClass = 'LOW' | 'MODERATE' | 'HIGH';

export type AssistanceLevel = 'INDEPENDENT' | 'HINT_ASSISTED' | 'PARTIALLY_ASSISTED' | 'FULLY_ASSISTED';

export type MistakeSourceType =
  | 'DIAGNOSTIC'
  | 'TUTOR_CHECK'
  | 'QUIZ'
  | 'PRACTICE'
  | 'TRANSFER_CHECK'
  | 'STEP_GRADER'
  | 'SIMULATION'
  | 'REVISION';

export interface MistakeEvent {
  id: string;
  user_id: string;
  skill_id?: string;
  subject: string;
  source_type: MistakeSourceType;
  source_record_id: string;
  question_reference: string;
  primary_error_type: ErrorType;
  secondary_error_types: ErrorType[];
  error_subtype: string;
  error_summary: string;
  confidence_class: ConfidenceClass;
  assistance_level: AssistanceLevel;
  repair_status: RepairStatus;
  engine_version: string;
  classifier_version: string;
  metadata: Record<string, any>;
  detected_at: string;
  created_at: string;
}

export interface MistakePattern {
  id: string;
  user_id: string;
  skill_id: string;
  subject: string;
  error_type: ErrorType;
  error_subtype: string;
  occurrence_count: number;
  recent_occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  pattern_status: PatternStatus;
  confidence: ConfidenceClass;
  repair_status: RepairStatus;
  recommended_repair_action: string;
  likely_prerequisite_skill?: string;
  prerequisite_signal?: string;
  engine_version: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface RepairEvent {
  id: string;
  pattern_id: string;
  user_id: string;
  skill_id: string;
  repair_action: string;
  evidence_source: MistakeSourceType;
  evidence_record_id: string;
  assistance_level: AssistanceLevel;
  verified_at: string;
  engine_version: string;
  notes: string;
  created_at: string;
}

export interface RepairRecommendation {
  action_type: string;
  skill_id: string;
  skill_name: string;
  recommended_repair_action: string;
  likely_prerequisite_skill?: string;
  prerequisite_signal?: string;
  explanation: string;
  pedagogical_mode: string;
}

export interface PatternDetailResponse {
  pattern: MistakePattern;
  skill_name: string;
  explainability: string;
  recommended_repair: RepairRecommendation;
  repair_history: RepairEvent[];
}

export interface MistakePatternSummary {
  error_type: ErrorType;
  error_subtype: string;
  status: PatternStatus;
  occurrence_count: number;
  skill_id: string;
  last_seen_at: string;
}

export interface CompactMistakeSummary {
  total_patterns: number;
  recurring_patterns: MistakePatternSummary[];
  isolated_patterns: MistakePatternSummary[];
  top_error_types: string[];
}

export interface MistakeDNAAuditReport {
  total_events: number;
  total_patterns: number;
  total_repairs: number;
  orphan_skill_ids: string[];
  invalid_taxonomy_labels: string[];
  duplicate_source_events: number;
  negative_occurrence_counts: number;
  repairs_without_evidence: number;
  unknown_classifications_count: number;
  unknown_heavy_domains: string[];
  cross_user_isolation_passed: boolean;
  audit_passed: boolean;
  timestamp: string;
}
