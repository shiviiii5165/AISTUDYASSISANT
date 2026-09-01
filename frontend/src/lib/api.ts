import axios from 'axios';
import { supabase } from './supabase';
import { useAuthStore } from '../store/useAuthStore';

// Use VITE_API_URL if set, otherwise empty string (requests go to same origin, where Vercel rewrites route them to the serverless function)
const API_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically add the Supabase JWT token to every request
api.interceptors.request.use(
  async (config) => {
    // Try to get token synchronously from the store first (much faster and more reliable if already initialized)
    let token = useAuthStore.getState().session?.access_token;
    
    // Fallback to supabase.auth.getSession() if store is empty (e.g. initial load race conditions)
    if (!token) {
      const { data: { session } } = await supabase.auth.getSession();
      token = session?.access_token;
    }
    
    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ─── Types ───────────────────────────────────────────────────────────────────

export interface PDFDocument {
  id: string;
  name: string;
  subject: string;
  status: 'processing' | 'ready' | 'error';
  page_count?: number;
  created_at: string;
  user_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSource {
  page: number | string;
  text: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  model: string;
  session_id?: string;
}

// ─── API Helpers ─────────────────────────────────────────────────────────────

export async function fetchPdfs(): Promise<PDFDocument[]> {
  const response = await api.get('/pdfs/list');
  return response.data.pdfs;
}

export async function uploadPdf(file: File, subject: string = 'General'): Promise<{ pdf_id: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', subject);
  
  const response = await api.post('/pdfs/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

export async function getPdfStatus(pdfId: string): Promise<{ id: string; status: string; page_count: number }> {
  const response = await api.get(`/pdfs/${pdfId}/status`);
  return response.data;
}

export async function deletePdf(pdfId: string): Promise<void> {
  await api.delete(`/pdfs/${pdfId}`);
}

export async function askQuestion(params: {
  pdf_id?: string;
  question: string;
  mode?: string;
  history?: ChatMessage[];
  session_id?: string;
}): Promise<ChatResponse> {
  const response = await api.post('/chat/ask', {
    pdf_id: params.pdf_id,
    question: params.question,
    mode: params.mode || 'Quick Answer',
    history: params.history || [],
    session_id: params.session_id,
  });
  return response.data;
}

// ─── V2 Pipeline Types & API ──────────────────────────────────────────────────

export interface TutorTurn {
  message: string;
  understanding_level: "not_assessed" | "struggling" | "developing" | "solid";
  concepts_covered: string[];
  concepts_struggled: string[];
  is_topic_complete: boolean;
}

export interface ContentCreatorOutput {
  job_id: string;
  content_type: string;
  status: "processing" | "complete" | "failed";
  output_url_or_path: string | null;
  grounded_in_notes: boolean;
  error_message: string | null;
  flashcards_data: any | null;
}

export interface PipelineOutput {
  response_type: string; // "tutor_turn" | "content" | "direct_message"
  message: string | null;
  tutor_data: TutorTurn | null;
  content_data: ContentCreatorOutput | null;
  intent: string;
  session_id?: string;
}

export async function sendMessageV2(params: {
  message: string;
  pdf_id?: string;
  history?: ChatMessage[];
  session_id?: string;
}): Promise<PipelineOutput> {
  const response = await api.post('/chat/v2/ask', {
    message: params.message,
    pdf_id: params.pdf_id,
    history: params.history || [],
    session_id: params.session_id,
  });
  return response.data;
}

export async function getContentStatus(jobId: string): Promise<ContentCreatorOutput> {
  const response = await api.get(`/content-creator/status/${jobId}`);
  return response.data;
}

// ─── Handwritten Notes Types & API ──────────────────────────────────────────

export interface NoteUploadResponse {
  noteId: string;
  extractedText: string;
  totalChunks: number;
  subject: string;
}

export async function uploadHandwrittenNote(
  file: File,
  subject: string = 'General'
): Promise<NoteUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', subject);

  const response = await api.post('/api/notes/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

// ─── Exam Predictor Types & API ─────────────────────────────────────────────

export interface ExamPrediction {
  id: string;
  question: string;
  topic: string;
  likelihood: 'High' | 'Medium' | 'Low';
  questionType: 'MCQ' | 'Short Answer' | 'Long Answer';
  reason: string;
}

export interface ExamPredictorResponse {
  predictions: ExamPrediction[];
  examType: string;
  chapterSummary: string;
}

export async function predictExamQuestions(
  pdfId: string,
  examType: string = 'CBSE'
): Promise<ExamPredictorResponse> {
  const response = await api.post('/api/predict/exam-questions', {
    pdfId,
    examType,
  });
  return response.data;
}

