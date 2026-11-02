/**
 * LearnByGenie — AI-Off Transfer Check Types (Feature 7)
 * ========================================================
 */

export type TransferTrigger =
  | 'TUTOR_REPAIR'
  | 'PRACTICE_REPAIR'
  | 'MISTAKE_DNA_REPAIR'
  | 'MASTERY_PROVISIONAL'
  | 'STUDENT_REQUEST'
  | 'MANUAL';

export type TransferLevel = 'NEAR_TRANSFER' | 'FAR_TRANSFER';

export type TransferSessionStatus =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'PASSED'
  | 'NEEDS_MORE_EVIDENCE'
  | 'ABORTED';

export type TransferOutcome = 'PASSED' | 'NEEDS_MORE_EVIDENCE' | 'ABORTED';

export interface StudentTransferItemView {
  session_id: string;
  item_id: string;
  skill_id: string;
  subject: string;
  grade_band: string;
  prompt: string;
  options: string[];
  question_type: string;
  transfer_level: TransferLevel;
  transfer_badge_text: string;
  why_explanation: string;
  support_disabled: boolean;
}

export interface TransferSession {
  id: string;
  user_id: string;
  skill_id: string;
  subject: string;
  source_trigger: TransferTrigger;
  source_trigger_id: string;
  transfer_level: TransferLevel;
  policy_version: string;
  current_item_id?: string | null;
  status: TransferSessionStatus;
  question_index: number;
  question_budget: number;
  support_lock_active: boolean;
  abort_reason?: string | null;
  trigger_explanation: string;
  started_at: string;
  completed_at?: string | null;
}

export interface TransferFeedback {
  session_id: string;
  item_id: string;
  skill_id: string;
  correctness: boolean;
  outcome: TransferOutcome;
  feedback_headline: string;
  educational_explanation: string;
  recommended_next_action: string;
  is_session_complete: boolean;
}

export interface TransferSummary {
  session_id: string;
  user_id: string;
  skill_id: string;
  subject: string;
  source_trigger: TransferTrigger;
  transfer_level: TransferLevel;
  outcome: TransferOutcome;
  status: TransferSessionStatus;
  duration_seconds: number;
  headline: string;
  explanation: string;
  next_step: string;
}

export interface TransferEligibilityResult {
  is_eligible: boolean;
  skill_id: string;
  trigger: TransferTrigger;
  reason: string;
  cooldown_remaining_seconds: number;
  available_items_count: number;
}
