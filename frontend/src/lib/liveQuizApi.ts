import { api } from './api';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export interface LiveTimerConfig {
  enabled: boolean;
  seconds: number;
  speed_bonus: boolean;
}

export interface LiveSessionSettings {
  sound_fx: boolean;
  leaderboard_enabled: boolean;
  show_correctness_immediately: boolean;
  question_revealed?: boolean;
}

export interface LiveParticipant {
  id: string;
  session_id: string;
  display_name: string;
  avatar_seed?: string;
  score: number;
  correct_count: number;
  answered_count: number;
  streak: number;
  status: 'active' | 'disconnected' | 'left';
}

export interface LiveQuizSession {
  id: string;
  quiz_id: string;
  host_user_id: string;
  join_code: string;
  status: 'CREATED' | 'LOBBY' | 'LIVE' | 'PAUSED' | 'COMPLETED' | 'ENDED' | 'EXPIRED';
  mode: 'teacher_led' | 'student_paced';
  current_question_index: number;
  current_question_started_at?: string;
  current_question_deadline?: string;
  total_questions: number;
  timer_config: LiveTimerConfig;
  settings: LiveSessionSettings;
  questions_snapshot?: any[];
  question_order?: string[];
  version: number;
  started_at?: string;
  ended_at?: string;
}

export interface ParticipantJoinResponse {
  participant_id: string;
  session_id: string;
  display_name: string;
  avatar_seed: string;
  participant_token: string;
  status: string;
}

export interface StudentRoomState {
  session_id: string;
  status: string;
  mode: string;
  current_question_index: number;
  total_questions: number;
  question?: {
    id: string;
    question_text: string;
    type: string;
    options: string[];
    difficulty?: string;
    correct_answer?: string;
    explanation?: string;
    concept_id?: string;
  } | null;
  is_revealed: boolean;
  remaining_seconds: number;
  has_submitted: boolean;
  selected_option_id?: string | null;
  participant: {
    id: string;
    display_name: string;
    avatar_seed?: string;
    score: number;
    streak: number;
  };
}

export interface ConceptHeatmapItem {
  concept: string;
  concept_id: string;
  accuracy_pct: number;
  total_responses: number;
  status: 'strong' | 'developing' | 'weak';
  color: string;
}

export interface SessionAnalytics {
  session_id: string;
  total_participants: number;
  total_questions: number;
  total_responses: number;
  overall_accuracy: number;
  completion_rate: number;
  average_response_time_ms: number;
  concept_heatmap: ConceptHeatmapItem[];
  most_missed_questions: any[];
  question_stats: any[];
}

export interface InterventionResult {
  type: 'explain' | 'visual' | 'example' | 'followup';
  concept: string;
  content?: string;
  svg?: string;
  comparison?: {
    title: string;
    correct_concept: { heading: string; text: string; reason: string };
    common_misconception: { heading: string; text: string; pitfall: string };
  };
  raw_content?: string;
  token_cost?: number;
}

// ─── Host Endpoints (Teacher JWT Auth) ───────────────────────────────────────

export async function startLiveSession(quizId: string, payload?: Partial<{ mode: string; timer_seconds: number; speed_bonus: boolean }>) {
  const response = await api.post(`/api/live-quizzes/${quizId}/start`, payload || {});
  return response.data;
}

export async function getLiveSessionHostView(sessionId: string) {
  const response = await api.get(`/api/live-quizzes/${sessionId}`);
  return response.data;
}

export async function advanceNextQuestion(sessionId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/next`);
  return response.data;
}

export async function revealCurrentQuestion(sessionId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/reveal`);
  return response.data;
}

export async function pauseLiveSession(sessionId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/pause`);
  return response.data;
}

export async function resumeLiveSession(sessionId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/resume`);
  return response.data;
}

export async function endLiveSession(sessionId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/end`);
  return response.data;
}

export async function getSessionAnalytics(sessionId: string): Promise<SessionAnalytics> {
  const response = await api.get(`/api/live-quizzes/${sessionId}/analytics`);
  return response.data;
}

export async function getSessionReport(sessionId: string) {
  const response = await api.get(`/api/live-quizzes/${sessionId}/report`);
  return response.data;
}

export async function triggerIntervention(sessionId: string, type: string, questionId?: string): Promise<InterventionResult> {
  const response = await api.post(`/api/live-quizzes/${sessionId}/intervention`, { type, question_id: questionId });
  return response.data;
}

// ─── Participant Endpoints (Signed Participant JWT Auth) ─────────────────────

export async function joinLiveSession(joinCode: string, displayName: string, avatarSeed?: string): Promise<ParticipantJoinResponse> {
  const response = await axios.post(`${API_BASE}/api/live-quizzes/join`, {
    join_code: joinCode,
    display_name: displayName,
    avatar_seed: avatarSeed,
  });
  return response.data;
}

export async function getParticipantState(sessionId: string, token: string): Promise<StudentRoomState> {
  const response = await axios.get(`${API_BASE}/api/live-quizzes/${sessionId}/state`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
}

export async function submitParticipantResponse(
  sessionId: string,
  questionId: string,
  selectedOptionId: string,
  token: string,
  idempotencyKey?: string,
) {
  const response = await axios.post(
    `${API_BASE}/api/live-quizzes/${sessionId}/response`,
    {
      question_id: questionId,
      selected_option_id: selectedOptionId,
      idempotency_key: idempotencyKey || `${questionId}_${Date.now()}`
    },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
}

export async function getMyResult(sessionId: string, token: string) {
  const response = await axios.get(`${API_BASE}/api/live-quizzes/${sessionId}/my-result`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
}
