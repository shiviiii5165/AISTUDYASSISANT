import { api } from './api';

export interface ParentChildView {
  student_id: string;
  student_name: string;
  email: string;
  grade_or_class: string;
  curriculum: string;
  target_exam: string | null;
  total_xp: number;
  current_streak: number;
  mastered_skills_count: number;
  in_progress_skills_count: number;
  needs_repair_count: number;
  active_mistakes_count: number;
  recent_activity_date: string | null;
}

export interface ParentDashboardSummary {
  parent_id: string;
  linked_children: ParentChildView[];
  unread_alerts_count: number;
}

export interface ChildMistakeAlert {
  skill_id: string;
  skill_name: string;
  error_type: string;
  pattern_status: string;
  occurrence_count: number;
  recommended_repair_action?: string;
}

export interface ChildDetailedProgress {
  student: ParentChildView;
  mastery_breakdown: Record<string, any>;
  active_mistake_alerts: ChildMistakeAlert[];
  recent_quiz_scores: Array<{ quiz_title: string; score: string; date: string }>;
}

export interface ClassroomView {
  id: string;
  school_id: string | null;
  teacher_id: string;
  name: string;
  grade_level: string;
  academic_stream: string | null;
  academic_year: string;
  student_count: number;
  average_mastery_percentage: number;
  created_at: string;
}

export interface ClassroomMisconceptionSummary {
  skill_id: string;
  skill_name: string;
  error_type: string;
  affected_students_count: number;
  recommended_reteach_strategy: string;
}

export interface TeacherDashboardSummary {
  teacher_id: string;
  classrooms: ClassroomView[];
  total_students: number;
  active_assignments_count: number;
  top_class_misconceptions: ClassroomMisconceptionSummary[];
}

export interface ClassroomRosterItem {
  student_id: string;
  student_name: string;
  email: string;
  enrolled_at: string;
  mastery_percentage: number;
  diagnostic_completed: boolean;
  pending_repairs_count: number;
}

export interface SchoolStats {
  total_students: number;
  total_teachers: number;
  total_classrooms: number;
  average_school_mastery: number;
  active_live_quizzes_today: number;
}

export interface TeacherAssignmentItem {
  teacher_id: string;
  teacher_name: string;
  email: string;
  department: string;
  assigned_classrooms_count: number;
  status: string;
}

export interface SchoolOverview {
  school_id: string;
  school_name: string;
  domain: string;
  subscription_tier: string;
  licensed_seats: number;
  allocated_seats: number;
  stats: SchoolStats;
  teachers: TeacherAssignmentItem[];
}

export interface ItemBankSummary {
  total_items: number;
  mcq_count: number;
  numeric_count: number;
  derivation_count: number;
  verified_items_count: number;
  domains_covered_count: number;
}

export interface CreatorDashboardSummary {
  user_id: string;
  item_bank_stats: ItemBankSummary;
  recent_curriculum_modules: Array<{ id: string; name: string; domain: string; skills_count: number }>;
}

export interface LLMProviderTelemetry {
  provider_name: string;
  status: string;
  latency_ms: number;
  tokens_used_today: number;
  error_rate_percentage: number;
}

export interface SystemHealthOverview {
  service_status: string;
  total_active_users: number;
  database_health: string;
  llm_telemetry: LLMProviderTelemetry[];
  circuit_breaker_status: Record<string, string>;
  uptime_percentage: number;
}

// ── Parent Portal APIs ───────────────────────────────────

export async function fetchParentDashboard(): Promise<ParentDashboardSummary> {
  const response = await api.get<ParentDashboardSummary>('/api/portals/parent/dashboard');
  return response.data;
}

export async function linkChild(studentId: string, relationship = 'guardian'): Promise<{ linked: boolean; message: string }> {
  const response = await api.post<{ linked: boolean; message: string }>('/api/portals/parent/link-child', {
    student_id: studentId,
    relationship,
  });
  return response.data;
}

export async function fetchChildDetailedProgress(childId: string): Promise<ChildDetailedProgress> {
  const response = await api.get<ChildDetailedProgress>(`/api/portals/parent/child/${childId}/progress`);
  return response.data;
}

// ── Teacher Portal APIs ──────────────────────────────────

export async function fetchTeacherDashboard(): Promise<TeacherDashboardSummary> {
  const response = await api.get<TeacherDashboardSummary>('/api/portals/teacher/dashboard');
  return response.data;
}

export async function createClassroom(payload: {
  name: string;
  grade_level: string;
  academic_stream?: string;
  academic_year: string;
  school_id?: string;
}): Promise<ClassroomView> {
  const response = await api.post<ClassroomView>('/api/portals/teacher/classrooms', payload);
  return response.data;
}

export async function fetchClassroomRoster(classroomId: string): Promise<ClassroomRosterItem[]> {
  const response = await api.get<ClassroomRosterItem[]>(`/api/portals/teacher/classrooms/${classroomId}/roster`);
  return response.data;
}

// ── School Admin Portal APIs ─────────────────────────────

export async function fetchSchoolAdminOverview(): Promise<SchoolOverview> {
  const response = await api.get<SchoolOverview>('/api/portals/school-admin/overview');
  return response.data;
}

// ── Creator Portal APIs ──────────────────────────────────

export async function fetchCreatorDashboard(): Promise<CreatorDashboardSummary> {
  const response = await api.get<CreatorDashboardSummary>('/api/portals/creator/dashboard');
  return response.data;
}

export async function createPracticeItem(item: Record<string, any>): Promise<{ id: string; message: string }> {
  const response = await api.post<{ id: string; message: string }>('/api/portals/creator/items', item);
  return response.data;
}

// ── Super Admin Portal APIs ──────────────────────────────

export async function fetchSuperAdminOverview(): Promise<SystemHealthOverview> {
  const response = await api.get<SystemHealthOverview>('/api/portals/super-admin/overview');
  return response.data;
}

export async function updateUserRole(targetUserId: string, newRole: string): Promise<{ success: boolean; message: string }> {
  const response = await api.post<{ success: boolean; message: string }>(
    `/api/portals/super-admin/user-role?target_user_id=${encodeURIComponent(targetUserId)}&new_role=${encodeURIComponent(newRole)}`
  );
  return response.data;
}

