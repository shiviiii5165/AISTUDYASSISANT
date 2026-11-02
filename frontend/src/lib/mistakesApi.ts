/**
 * LearnByGenie — Feature 5: Mistake DNA API Client
 * ================================================
 */
import { api } from './api';
import type {
  MistakePattern,
  MistakeEvent,
  RepairRecommendation,
  PatternDetailResponse,
  CompactMistakeSummary,
  MistakeDNAAuditReport
} from '../types/mistakes';

export const mistakesApi = {
  getPatterns: async (params?: { skill_id?: string; subject?: string }): Promise<MistakePattern[]> => {
    const res = await api.get('/api/mistakes/patterns', { params });
    return res.data;
  },

  getRecentMistakes: async (limit: number = 50): Promise<MistakeEvent[]> => {
    const res = await api.get('/api/mistakes/recent', { params: { limit } });
    return res.data;
  },

  getPatternDetail: async (patternId: string): Promise<PatternDetailResponse> => {
    const res = await api.get(`/api/mistakes/detail/${patternId}`);
    return res.data;
  },

  getRepairs: async (): Promise<RepairRecommendation[]> => {
    const res = await api.get('/api/mistakes/repairs');
    return res.data;
  },

  getSummary: async (subject?: string): Promise<CompactMistakeSummary> => {
    const res = await api.get('/api/mistakes/summary', { params: { subject } });
    return res.data;
  },

  runAudit: async (): Promise<MistakeDNAAuditReport> => {
    const res = await api.post('/api/mistakes/audit');
    return res.data;
  }
};
