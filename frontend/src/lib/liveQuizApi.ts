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

  // VNEXT Live Snapshot fields
  current_question_index?: number;
  average_response_ms?: number;
  last_seen_at?: string;
  connection_state?: 'active' | 'disconnected' | 'reconnecting' | 'idle';
  risk_score?: number;
  risk_level?: 'low' | 'medium' | 'high';
  is_banned?: boolean;
  banned_at?: string;
  ban_reason?: string;
  state_version?: number;
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
    progression_token?: string;
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
    risk_level?: string;
    is_banned?: boolean;
  };
}

export interface MonitoringSummary {
  session_id: string;
  total_participants: number;
  active_count: number;
  answered_count: number;
  waiting_count: number;
  disconnected_count: number;
  banned_count: number;
  flagged_count: number;
  average_progress_pct: number;
  average_speed_ms: number;
}

export interface PaginatedParticipantsResponse {
  items: LiveParticipant[];
  next_cursor: string | null;
  total_count: number;
  has_more: boolean;
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

export async function getMonitoringSummary(sessionId: string): Promise<MonitoringSummary> {
  const response = await api.get(`/api/live-quizzes/${sessionId}/monitoring-summary`);
  return response.data;
}

export async function getPaginatedParticipants(
  sessionId: string,
  params?: {
    cursor?: string;
    limit?: number;
    status?: string;
    risk?: string;
    search?: string;
    banned_only?: boolean;
    sort_by?: string;
    sort_desc?: boolean;
  }
): Promise<PaginatedParticipantsResponse> {
  const response = await api.get(`/api/live-quizzes/${sessionId}/participants`, { params });
  return response.data;
}

export async function getParticipantDetail(sessionId: string, participantId: string) {
  const response = await api.get(`/api/live-quizzes/${sessionId}/participants/${participantId}/detail`);
  return response.data;
}

export async function banParticipant(sessionId: string, participantId: string, reason?: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/participants/${participantId}/ban`, {
    reason: reason || 'Removed by teacher',
  });
  return response.data;
}

export async function unbanParticipant(sessionId: string, participantId: string) {
  const response = await api.post(`/api/live-quizzes/${sessionId}/participants/${participantId}/unban`);
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

export async function recordActivitySignal(
  sessionId: string,
  signalType: string,
  token: string,
  metadata?: Record<string, any>
) {
  try {
    await axios.post(
      `${API_BASE}/api/live-quizzes/${sessionId}/activity`,
      { signal_type: signalType, metadata },
      { headers: { Authorization: `Bearer ${token}` } }
    );
  } catch (err) {
    // Non-blocking telemetry
    console.debug('[ActivityTelemetry] Non-blocking signal dropped', err);
  }
}

export async function submitParticipantResponse(
  sessionId: string,
  questionId: string,
  selectedOptionId: string,
  token: string,
  progressionToken?: string,
  responseTimeMs: number = 0,
  idempotencyKey?: string,
) {
  let attempt = 0;
  const maxAttempts = 3;

  while (attempt < maxAttempts) {
    try {
      const response = await axios.post(
        `${API_BASE}/api/live-quizzes/${sessionId}/response`,
        {
          question_id: questionId,
          selected_option_id: selectedOptionId,
          progression_token: progressionToken,
          response_time_ms: responseTimeMs,
          idempotency_key: idempotencyKey || `${questionId}_${Date.now()}`
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return response.data;
    } catch (err: any) {
      if (err.response?.status === 429) {
        // Backpressure Retry-After
        attempt++;
        const retryAfterSec = parseInt(err.response.headers?.['retry-after'] || '1', 10);
        const backoffMs = retryAfterSec * 1000 + Math.floor(Math.random() * 300);
        await new Promise(res => setTimeout(res, backoffMs));
      } else {
        throw err;
      }
    }
  }
  throw new Error('Server queue busy; answer preserved in local journal.');
}

export async function getMyResult(sessionId: string, token: string) {
  const response = await axios.get(`${API_BASE}/api/live-quizzes/${sessionId}/my-result`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
}
