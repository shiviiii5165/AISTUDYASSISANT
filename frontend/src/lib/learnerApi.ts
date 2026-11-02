import { api } from './api';
import type {
  AcademicConfig,
  LearnerProfile,
  LearnerProfileUpdate,
  LearnerContext
} from '../types/learner';

/**
 * Fetch database/config-driven canonical academic configuration.
 * Contains classes 3-12 + UG, boards, streams, exam tracks, subjects, goals, languages.
 */
export async function fetchAcademicConfig(): Promise<AcademicConfig> {
  const response = await api.get<AcademicConfig>('/api/learner/academic-config');
  return response.data;
}

/**
 * Fetch current authenticated user's canonical learner profile.
 * Falls back safely if the user has not yet completed onboarding.
 */
export async function fetchLearnerProfile(): Promise<LearnerProfile> {
  const response = await api.get<LearnerProfile>('/api/learner/profile');
  return response.data;
}

/**
 * Update authenticated user's learner profile fields.
 * Increments profile_version. Historical evidence is strictly preserved.
 */
export async function updateLearnerProfile(updates: LearnerProfileUpdate): Promise<LearnerProfile> {
  const response = await api.patch<LearnerProfile>('/api/learner/profile', updates);
  return response.data;
}

/**
 * Fetch unified learner context consumed by AI engines and dashboard.
 */
export async function fetchLearnerContext(): Promise<LearnerContext> {
  const response = await api.get<LearnerContext>('/api/learner/context');
  return response.data;
}
