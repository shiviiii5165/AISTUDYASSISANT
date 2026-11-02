/**
 * LearnByGenie — Feature 3: Mastery API Client
 * ============================================
 */
import { api } from './api';
import type { SubjectGraphView, LearningRecommendation, SkillNodeView, GraphAuditReport } from '../types/mastery';

export const masteryApi = {
  getSubjectGraph: async (subject: string = 'Mathematics'): Promise<SubjectGraphView> => {
    const res = await api.get('/api/mastery/graph', { params: { subject } });
    return res.data;
  },

  getRecommendations: async (subject: string = 'Mathematics'): Promise<LearningRecommendation[]> => {
    const res = await api.get('/api/mastery/recommendations', { params: { subject } });
    return res.data;
  },

  getBlockedSkills: async (subject: string = 'Mathematics'): Promise<SkillNodeView[]> => {
    const res = await api.get('/api/mastery/blocked', { params: { subject } });
    return res.data;
  },

  getRepairPath: async (skillId: string): Promise<string[]> => {
    const res = await api.get(`/api/mastery/repair-path/${skillId}`);
    return res.data;
  },

  ingestDiagnostic: async (sessionId: string) => {
    const res = await api.post('/api/mastery/ingest-diagnostic', { session_id: sessionId });
    return res.data;
  },

  auditGraph: async (): Promise<GraphAuditReport> => {
    const res = await api.get('/api/mastery/audit');
    return res.data;
  }
};
