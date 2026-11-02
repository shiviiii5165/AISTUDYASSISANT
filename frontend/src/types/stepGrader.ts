/**
 * LearnByGenie — Feature 8: Step-Grader & Reasoning Diagnostics Types
 */

export type StepType =
  | 'SETUP'
  | 'TRANSFORMATION'
  | 'SUBSTITUTION'
  | 'CALCULATION'
  | 'RULE_APPLICATION'
  | 'INFERENCE'
  | 'CONCLUSION'
  | 'EXPLANATION'
  | 'UNKNOWN';

export type StepValidationStatus =
  | 'VALID_STEP'
  | 'ROOT_ERROR'
  | 'DOWNSTREAM_ERROR'
  | 'INDEPENDENT_ERROR'
  | 'UNCERTAIN';

export type ValidatorType =
  | 'DETERMINISTIC'
  | 'DOMAIN_RULE'
  | 'RUBRIC'
  | 'SEMANTIC_LLM'
  | 'UNCERTAIN';

export type ConfidenceClass = 'HIGH' | 'MODERATE' | 'LOW';

export type OverallOutcome =
  | 'ALL_STEPS_VALID'
  | 'ROOT_ERROR_DETECTED'
  | 'AMBIGUOUS_REASONING'
  | 'UNRESOLVED';

export interface GradedStep {
  id: string;
  step_index: number;
  raw_text: string;
  normalized_expression: string;
  step_type: StepType;
  validation_status: StepValidationStatus;
  validator_type: ValidatorType;
  confidence: ConfidenceClass;
  is_root_error: boolean;
  error_type?: string;
  error_subtype?: string;
  feedback: string;
}

export interface StepGraderResult {
  session_id: string;
  attempt_id: string;
  attempt_sequence: number;
  overall_outcome: OverallOutcome;
  first_wrong_step?: number;
  validated_steps: GradedStep[];
  downstream_steps: number[];
  error_type?: string;
  error_subtype?: string;
  confidence: ConfidenceClass;
  skill_id?: string;
  feedback_summary: string;
  recommended_next_action: string;
  can_review_with_tutor: boolean;
  engine_version: string;
  policy_version: string;
}

export interface TutorHandoffContext {
  session_id: string;
  attempt_id: string;
  skill_id?: string;
  skill_name?: string;
  first_wrong_step_index: number;
  step_raw_text: string;
  error_type: string;
  error_subtype?: string;
  feedback: string;
  related_prerequisite?: string;
  question_text: string;
}

export interface CapabilityMatrixItem {
  subject: string;
  skill_name: string;
  step_types_supported: string[];
  validator_type: ValidatorType;
  deterministic_support: boolean;
  rubric_support: boolean;
  confidence_capability: string;
  notes: string;
}
