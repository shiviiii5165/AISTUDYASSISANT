/**
 * LearnByGenie — Feature 7: AI-Off Transfer Check API Client
 * ============================================================
 */
import { api } from './api';
import type {
  TransferSession,
  StudentTransferItemView,
  TransferFeedback,
  TransferSummary,
  TransferEligibilityResult,
  TransferTrigger,
  TransferLevel
} from '../types/transfer';

export interface StartTransferParams {
  skill_id: string;
  subject?: string;
  source_trigger?: TransferTrigger;
  source_trigger_id?: string;
  transfer_level?: TransferLevel;
  excluded_item_ids?: string[];
}

export const transferApi = {
  checkEligibility: async (
    skillId: string,
    trigger: TransferTrigger = 'PRACTICE_REPAIR',
    triggerId: string = ''
  ): Promise<TransferEligibilityResult> => {
    const res = await api.post('/api/transfer/eligibility', {
      skill_id: skillId,
      trigger,
      trigger_id: triggerId
    });
    return res.data;
  },

  startSession: async (params: StartTransferParams): Promise<TransferSession> => {
    const res = await api.post('/api/transfer/start', {
      skill_id: params.skill_id,
      subject: params.subject || 'Mathematics',
      source_trigger: params.source_trigger || 'PRACTICE_REPAIR',
      source_trigger_id: params.source_trigger_id || '',
      transfer_level: params.transfer_level || 'NEAR_TRANSFER',
      excluded_item_ids: params.excluded_item_ids || []
    });
    return res.data;
  },

  getItem: async (sessionId: string): Promise<StudentTransferItemView> => {
    const res = await api.get(`/api/transfer/${sessionId}/item`);
    return res.data;
  },

  submitResponse: async (
    sessionId: string,
    req: {
      item_id: string;
      student_response: any;
      response_time_ms?: number;
      question_index?: number;
    }
  ): Promise<TransferFeedback> => {
    const res = await api.post(`/api/transfer/${sessionId}/submit`, req);
    return res.data;
  },

  abortSession: async (sessionId: string, reason: string = 'STUDENT_EXIT'): Promise<TransferSession> => {
    const res = await api.post(`/api/transfer/${sessionId}/abort`, { reason });
    return res.data;
  },

  getSummary: async (sessionId: string): Promise<TransferSummary> => {
    const res = await api.get(`/api/transfer/${sessionId}/summary`);
    return res.data;
  },

  resumeSession: async (sessionId: string): Promise<{ session: TransferSession; item: StudentTransferItemView | null }> => {
    const res = await api.get(`/api/transfer/${sessionId}/resume`);
    return res.data;
  }
};
