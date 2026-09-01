import { api } from './api';

export interface QuizConfig {
  question_count: number;
  difficulty: string;
  types: string[];
  language: string;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  timer_seconds?: number;
  adaptive: boolean;
}

export interface GenerateQuizRequest {
  mode: string;
  title?: string;
  source_type: string;
  source_ids: string[];
  topic?: string;
  roadmap_id?: string;
  stage_id?: string;
  lesson_id?: string;
  teach_session_id?: string;
  config: QuizConfig;
  idempotency_key?: string;
}

export interface QuestionEditModel {
  question_text?: string;
  type?: string;
  options?: string[];
  correct_answer?: string | string[];
  explanation?: string;
  difficulty?: string;
}

export interface StartAttemptRequest {
  quiz_id: string;
}

export interface SubmitAnswerModel {
  question_id: string;
  answer?: string | string[] | null;
}

export interface SubmitAttemptRequest {
  attempt_id: string;
  answers: SubmitAnswerModel[];
  idempotency_key?: string;
}

export interface UpdateQuizStatusRequest {
  status: string;
}

export async function generateQuiz(payload: GenerateQuizRequest) {
  const response = await api.post('/api/quiz/quizzes', payload);
  return response.data;
}

export async function listMyQuizzes() {
  const response = await api.get('/api/quiz/quizzes');
  return response.data;
}

export async function getQuiz(quizId: string) {
  const response = await api.get(`/api/quiz/quizzes/${quizId}`);
  return response.data;
}

export async function updateQuizStatus(quizId: string, payload: UpdateQuizStatusRequest) {
  const response = await api.patch(`/api/quiz/quizzes/${quizId}/status`, payload);
  return response.data;
}

export async function removeQuiz(quizId: string) {
  const response = await api.delete(`/api/quiz/quizzes/${quizId}`);
  return response.data;
}

export async function editQuestion(questionId: string, payload: QuestionEditModel) {
  const response = await api.patch(`/api/quiz/questions/${questionId}`, payload);
  return response.data;
}

export async function deleteQuestion(questionId: string) {
  const response = await api.delete(`/api/quiz/questions/${questionId}`);
  return response.data;
}

export async function reorderQuestions(quizId: string, ordered_question_ids: string[]) {
  const response = await api.post(`/api/quiz/quizzes/${quizId}/reorder`, { ordered_question_ids });
  return response.data;
}

export async function regenerateQuestion(questionId: string, instruction?: string, idempotencyKey?: string) {
  const payload: any = {};
  if (instruction) payload.instruction = instruction;
  if (idempotencyKey) payload.idempotency_key = idempotencyKey;
  const response = await api.post(`/api/quiz/questions/${questionId}/regenerate`, payload);
  return response.data;
}

export async function startAttempt(quizId: string) {
  const response = await api.post(`/api/quiz/attempts/start`, { quiz_id: quizId });
  return response.data;
}

export async function submitAttempt(payload: SubmitAttemptRequest) {
  const response = await api.post(`/api/quiz/attempts/submit`, payload);
  return response.data;
}

export async function getAttempt(attemptId: string) {
  const response = await api.get(`/api/quiz/attempts/${attemptId}`);
  return response.data;
}
