/**
 * LearnByGenie — Feature 3: Mastery & Prerequisite Knowledge Graph Types
 * ======================================================================
 * Educational learning-state contracts.
 * Strictly labels concepts, not student intelligence or traits.
 */

export type MasteryState =
  | 'NOT_ASSESSED'
  | 'NEEDS_REPAIR'
  | 'DEVELOPING'
  | 'FRAGILE'
  | 'SECURE';

export type ReadinessState =
  | 'READY'
  | 'PARTIALLY_READY'
  | 'BLOCKED_BY_PREREQUISITE'
  | 'NOT_ENOUGH_EVIDENCE';

export type ReviewStatus =
  | 'FRESH'
  | 'REVIEW_SOON'
  | 'REASSESSMENT_DUE';

export type ConfidenceClass =
  | 'LOW_EVIDENCE'
  | 'MODERATE_EVIDENCE'
  | 'HIGH_EVIDENCE';

export interface SkillNodeView {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  subject: string;
  domain_id?: string;
  grade_band: string;
  topic: string;
  description: string;
  mastery_state: MasteryState;
  readiness_state: ReadinessState;
  confidence_class: ConfidenceClass;
  review_status: ReviewStatus;
  prerequisites: string[];
  dependents: string[];
  blocking_prerequisites: string[];
  why: string;
  next_action: string;
}

export interface LearningRecommendation {
  skill_id: string;
  skill_name: string;
  subject: string;
  recommendation_type: 'REPAIR_PREREQUISITE' | 'NEXT_CONCEPT';
  priority: number;
  reason: string;
  unblocks_skills: string[];
}

export interface DomainGroup {
  id: string;
  name: string;
  stage: string;
}

export interface SubjectGraphView {
  subject: string;
  user_id: string;
  domains: DomainGroup[];
  nodes: SkillNodeView[];
  blocked_skills: SkillNodeView[];
  repair_paths: Record<string, string[]>;
  recommendations: LearningRecommendation[];
}

export interface GraphAuditReport {
  total_skills: number;
  total_edges: number;
  is_dag: boolean;
  cycles: string[][];
  orphan_skills: string[];
  self_edges: string[];
  duplicate_edges: string[];
  inactive_edges: string[];
  is_healthy: boolean;
}
