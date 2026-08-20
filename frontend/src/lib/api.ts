import axios from 'axios';
import { supabase } from './supabase';

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
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
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

export async function askQuestion(
  pdfId: string,
  question: string,
  mode: string = 'Quick Answer',
  history: ChatMessage[] = []
): Promise<ChatResponse> {
  const response = await api.post('/chat/ask', {
    pdf_id: pdfId,
    question,
    mode,
    history,
  });
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

