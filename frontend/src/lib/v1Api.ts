import { api, saveMfaToken } from './api';

export { saveMfaToken };

export interface PublicItem {
  item_id: string;
  concept_id: string;
  prompt: string;
  unit: string;
  start_equation: string;
}

export interface Concept {
  concept_id: string;
  title: string;
  subject: string;
  class_level: number;
  prerequisites: string[];
  simulation: string;
}

export type NextStep =
  | { action: 'item'; item: PublicItem; source: string; in_zpd: boolean }
  | { action: 'simulation'; activity: string; reason: string }
  | { action: 'exhausted' };

export interface Attribution {
  succeeded: string;
  fix: string;
  bad_step?: number;
}

export interface SubmitResult {
  correct: boolean;
  error_token: { token: string; rule: string } | null;
  entrenched_misconception: boolean;
  attribution: Attribution | null;
  remediation_path: string[];
  p_mastery: number;
  tier: number;
  tier_changed: boolean;
  tokens_resolved: number;
  xp_awarded: { rule_id: string; ledger: string; amount: number; badge: string | null }[];
  correct_answer: string | null;
  next: NextStep;
}

export type TutorMode =
  | '01_explain' | '02_hint' | '03_step_by_step' | '04_socratic' | '05_mistake_repair'
  | '06_quiz' | '07_teach_back' | '08_revision' | '09_exam_simulation' | '10_challenge_transfer';

export interface TutorReply {
  mode: TutorMode | null;
  outcome: 'answered' | 'blocked' | 'fallback' | 'support';
  text: string;
  citations: string[];
  gates: Record<string, unknown>;
  payload: Record<string, any>;
  fallback_card: Record<string, any> | null;
}

export type Confidence = 'Sure' | 'Unsure' | 'Guess';

async function post<T>(url: string, body?: unknown): Promise<T> {
  return (await api.post(url, body)).data;
}

async function get<T>(url: string): Promise<T> {
  return (await api.get(url)).data;
}

export const v1 = {
  concepts: () => get<Concept[]>('/api/v1/curriculum/concepts'),
  verifyStep: (previous: string, current: string) =>
    post<{ verdict: 'verified' | 'refuted' | 'unverifiable' }>('/api/v1/math/verify-step', { previous, current }),
  startDiagnostic: (subject: string) => post<any>('/api/v1/diagnostics/start', { subject }),
  answerDiagnostic: (sessionId: string, itemId: string, response: string) =>
    post<any>(`/api/v1/diagnostics/${sessionId}/answer`, { item_id: itemId, response }),
  startPractice: (conceptId: string, kind = 'practice') =>
    post<{ session_id: string; tier: number; next: NextStep; prescription: any }>('/api/v1/practice/start', {
      concept_id: conceptId, kind,
    }),
  submitPractice: (
    sessionId: string,
    body: { item_id: string; response: string; steps?: string[]; confidence?: Confidence; hints_used?: number },
  ) => post<SubmitResult>(`/api/v1/practice/${sessionId}/submit`, { ...body, idempotency_key: crypto.randomUUID() }),
  interventionComplete: (sessionId: string) =>
    post<{ tier: number; next: NextStep; next_example: any }>(`/api/v1/practice/${sessionId}/intervention-complete`),
  ask: (body: Record<string, unknown>) => post<TutorReply>('/api/v1/tutor/ask', body),
  startBoss: (conceptIds: string[]) => post<any>('/api/v1/quests/boss/start', { concept_ids: conceptIds }),
  submitBoss: (questId: string, answers: Record<string, string>) =>
    post<any>(`/api/v1/quests/boss/${questId}/submit`, { answers }),
  studentDashboard: () => get<any>('/api/v1/dashboard/student'),
  setIntention: (when: string, action: string) => post<any>('/api/v1/dashboard/student/intention', { when, action }),
  consentStatus: () => get<Record<string, boolean>>('/api/v1/consent/status'),
  requestOtp: (guardianContact: string, purpose: string) =>
    post<{ request_id: string; dev_otp?: string }>('/api/v1/consent/request-otp', { guardian_contact: guardianContact, purpose }),
  verifyOtp: (requestId: string, otp: string) => post<any>('/api/v1/consent/verify-otp', { request_id: requestId, otp }),
  withdrawConsent: (purpose: string) => post<any>('/api/v1/consent/withdraw', { purpose }),
  exportData: async (format: 'json' | 'pdf') => (await api.get(`/api/v1/privacy/export?format=${format}`, { responseType: 'blob' })).data as Blob,
  eraseData: async () => (await api.delete('/api/v1/privacy/erase', { data: { confirm: 'ERASE' } })).data,
  enrollMfa: () => post<{ secret: string; otpauth_uri: string }>('/api/v1/auth/mfa/enroll'),
  verifyMfa: (code: string) => post<{ mfa_token: string }>('/api/v1/auth/mfa/verify', { code }),
};
