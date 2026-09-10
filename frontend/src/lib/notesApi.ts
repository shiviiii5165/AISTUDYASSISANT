import { api } from './api';

export interface VisualSpec {
  type: string;
  title: string;
  nodes?: { id: string; label: string; description?: string }[];
  edges?: { from: string; to: string; label?: string }[];
  mermaid_code?: string;
}

export interface CalloutItem {
  type: 'warning' | 'tip' | 'exam_alert' | 'misconception' | 'fun_fact';
  title: string;
  text: string;
}

export interface NoteSection {
  id: string;
  section_type: string;
  title: string;
  content: string;
  key_points?: string[];
  examples?: string[];
  formulas?: string[];
  common_mistakes?: string[];
  callouts?: CalloutItem[];
  visual_spec?: VisualSpec;
}

export interface NotesQualityReport {
  score: number;
  accuracy: number;
  curriculum_alignment: number;
  grade_appropriateness: number;
  clarity: number;
  completeness: number;
  relevance: number;
  format_compliance: number;
  misconception_coverage: number;
  warnings: string[];
  feedback: string[];
}

export interface NotesDocument {
  id: string;
  title: string;
  subject: string;
  class_level: string;
  topic: string;
  curriculum: string;
  language: string;
  mode: string;
  generated_at: string;
  selected_formats: string[];
  depth: string;
  difficulty: string;
  sections: NoteSection[];
  source_citations?: { source_name: string; badge: string; snippet: string; page?: number }[];
  quality: NotesQualityReport;
  lineage?: Record<string, any>;
}

export interface GenerateNotesPayload {
  mode: 'topic' | 'lesson_context';
  topic: string;
  class_level?: string;
  subject?: string;
  curriculum?: string;
  language?: string;
  roadmap_id?: string;
  stage_id?: string;
  teach_session_id?: string;
  quiz_id?: string;
  deck_id?: string;
  requested_depth?: string;
  requested_format?: string;
  user_instructions?: string;
}

export interface ContextSourcesResponse {
  roadmaps: { id: string; title?: string; topic: string; level: string; created_at: string }[];
  teach_sessions: { id: string; topic: string; level: string; mode: string; created_at: string }[];
  quizzes: { id: string; title: string; topic: string; mode: string; created_at: string }[];
}

export async function generateNotes(payload: GenerateNotesPayload): Promise<NotesDocument> {
  const response = await api.post('/api/notes-generator/generate', payload);
  return response.data;
}

export async function getNote(noteId: string): Promise<NotesDocument> {
  const response = await api.get(`/api/notes-generator/${noteId}`);
  return response.data;
}

export async function listMyNotes(): Promise<{ notes: any[] }> {
  const response = await api.get('/api/notes-generator/');
  return response.data;
}

export async function deleteNote(noteId: string): Promise<{ message: string; id: string }> {
  const response = await api.delete(`/api/notes-generator/${noteId}`);
  return response.data;
}

export async function getAvailableContextSources(): Promise<ContextSourcesResponse> {
  const response = await api.get('/api/notes-generator/context/sources');
  return response.data;
}
