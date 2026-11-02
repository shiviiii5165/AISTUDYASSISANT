/**
 * LearnByGenie — Feature 8: Step-Grader API Client
 */
import { api } from './api';
import type {
  StepGraderResult,
  TutorHandoffContext,
  CapabilityMatrixItem
} from '../types/stepGrader';

export interface GradeSolutionParams {
  question_text: string;
  raw_input: string;
  subject?: string;
  skill_id?: string;
  assistance_level?: string;
  idempotency_key?: string;
  audience_level?: 'young' | 'standard' | 'advanced';
}

export interface ResubmitSolutionParams {
  session_id: string;
  updated_raw_input: string;
  assistance_level?: string;
  audience_level?: 'young' | 'standard' | 'advanced';
}

export const stepGraderApi = {
  gradeSolution: async (params: GradeSolutionParams): Promise<StepGraderResult> => {
    const res = await api.post('/api/step-grader/grade', {
      question_text: params.question_text,
      raw_input: params.raw_input,
      subject: params.subject || 'Mathematics',
      skill_id: params.skill_id,
      assistance_level: params.assistance_level || 'INDEPENDENT',
      idempotency_key: params.idempotency_key,
      audience_level: params.audience_level || 'standard'
    });
    return res.data;
  },

  resubmitSolution: async (params: ResubmitSolutionParams): Promise<StepGraderResult> => {
    const res = await api.post('/api/step-grader/resubmit', {
      session_id: params.session_id,
      updated_raw_input: params.updated_raw_input,
      assistance_level: params.assistance_level || 'INDEPENDENT',
      audience_level: params.audience_level || 'standard'
    });
    return res.data;
  },

  getTutorContext: async (attemptId: string): Promise<TutorHandoffContext> => {
    const res = await api.get(`/api/step-grader/tutor-context/${attemptId}`);
    return res.data;
  },

  getCapabilityMatrix: async (): Promise<CapabilityMatrixItem[]> => {
    const res = await api.get('/api/step-grader/capability-matrix');
    return res.data;
  }
};


// Convenience functional exports
export const gradeMathSteps = async (params: GradeSolutionParams): Promise<StepGraderResult> => {
  return stepGraderApi.gradeSolution(params);
};

export const getGradeLevelCapabilities = async (subject?: string): Promise<CapabilityMatrixItem[]> => {
  return stepGraderApi.getCapabilityMatrix();
};

export const requestStepTutorContext = async (
  attemptId: string,
  firstWrongStep?: number
): Promise<TutorHandoffContext> => {
  return stepGraderApi.getTutorContext(attemptId);
};
