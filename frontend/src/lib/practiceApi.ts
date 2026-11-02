/**
 * LearnByGenie — Feature 6: Adaptive Practice API Client
 * ========================================================
 */
import { api } from './api';
import type {
  PracticeMode,
  PracticeSession,
  StudentPracticeItemView,
  PracticeFeedback,
  PracticeSelectionExplanation,
  SessionSummary
} from '../types/practice';

export interface StartPracticeParams {
  subject: string;
  mode?: PracticeMode;
  requested_skill_id?: string;
  question_budget?: number | string;
  curriculum?: string;
  exam_track?: string;
  enrolled_grade?: number;
  grade_band?: string;
}

export interface PracticeStartResponse {
  session: PracticeSession;
  current_item: StudentPracticeItemView | null;
}

export interface HintResponse {
  hint: string;
  hints_revealed: number;
  total_hints: number;
}

export const practiceApi = {
  startSession: async (params: StartPracticeParams): Promise<PracticeStartResponse> => {
    const res = await api.post('/api/practice/start', params);
    return res.data;
  },

  getNextItem: async (sessionId: string): Promise<StudentPracticeItemView | null> => {
    const res = await api.get(`/api/practice/${sessionId}/next`);
    return res.data;
  },

  submitResponse: async (
    sessionId: string,
    req: {
      item_id: string;
      question_index: number;
      student_response: any;
      response_time_ms?: number;
      attempt_sequence?: number;
    }
  ): Promise<PracticeFeedback> => {
    const res = await api.post(`/api/practice/${sessionId}/response`, req);
    return res.data;
  },

  requestHint: async (sessionId: string, itemId: string): Promise<HintResponse> => {
    const res = await api.post(`/api/practice/${sessionId}/hint`, { item_id: itemId });
    return res.data;
  },

  getSession: async (sessionId: string): Promise<PracticeSession> => {
    const res = await api.get(`/api/practice/${sessionId}`);
    return res.data;
  },

  resumeSession: async (sessionId: string): Promise<PracticeStartResponse> => {
    const res = await api.post(`/api/practice/${sessionId}/resume`);
    return res.data;
  },

  explainSelection: async (sessionId: string): Promise<PracticeSelectionExplanation> => {
    const res = await api.get(`/api/practice/${sessionId}/explain`);
    return res.data;
  },

  getSessionSummary: async (sessionId: string): Promise<SessionSummary> => {
    const res = await api.get(`/api/practice/${sessionId}/summary`);
    return res.data;
  },

  getContentAudit: async () => {
    const res = await api.get('/api/practice/content/audit');
    return res.data;
  }
};
