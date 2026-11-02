import { api } from './api';
import type {
  DiagnosticStartRequest,
  AnswerSubmissionRequest,
  DiagnosticStepResponse,
  DiagnosticResult,
} from '../types/diagnostic';

/**
 * Start or resume an adaptive diagnostic session.
 */
export async function startDiagnostic(req: DiagnosticStartRequest): Promise<DiagnosticStepResponse> {
  const response = await api.post<DiagnosticStepResponse>('/api/diagnostic/start', req);
  return response.data;
}

/**
 * Submit an answer to the current diagnostic question.
 */
export async function submitDiagnosticAnswer(
  sessionId: string,
  submission: AnswerSubmissionRequest
): Promise<DiagnosticStepResponse> {
  const response = await api.post<DiagnosticStepResponse>(
    `/api/diagnostic/${sessionId}/answer`,
    submission
  );
  return response.data;
}

/**
 * Get active session state (interruption and resume support).
 */
export async function getDiagnosticSession(sessionId: string): Promise<DiagnosticStepResponse> {
  const response = await api.get<DiagnosticStepResponse>(`/api/diagnostic/${sessionId}`);
  return response.data;
}

/**
 * Get completed diagnostic result.
 */
export async function getDiagnosticResult(sessionId: string): Promise<DiagnosticResult> {
  const response = await api.get<DiagnosticResult>(`/api/diagnostic/${sessionId}/result`);
  return response.data;
}

/**
 * Get student's historical diagnostic reports.
 */
export async function getDiagnosticHistory(): Promise<DiagnosticResult[]> {
  const response = await api.get<DiagnosticResult[]>('/api/diagnostic/history');
  return response.data;
}
