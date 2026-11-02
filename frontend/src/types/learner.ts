export interface EducationLevelOption {
  id: string;
  name: string;
  stage: string;
  display_order: number;
  has_streams: boolean;
  allowed_streams?: string[];
}

export interface CurriculumOption {
  id: string;
  name: string;
  full_name: string;
  region: string;
}

export interface AcademicStreamOption {
  id: string;
  name: string;
  stages: string[];
}

export interface ExamTrackOption {
  id: string;
  name: string;
  description: string;
  eligible_stages: string[];
}

export interface SubjectOption {
  id: string;
  name: string;
  category: string;
}

export interface AcademicGoalOption {
  id: string;
  name: string;
  description: string;
}

export interface LanguageOption {
  id: string;
  code: string;
  name: string;
  native_label: string;
}

export interface AcademicConfig {
  education_levels: EducationLevelOption[];
  curricula: CurriculumOption[];
  academic_streams: AcademicStreamOption[];
  exam_tracks: ExamTrackOption[];
  subjects: SubjectOption[];
  academic_goals: AcademicGoalOption[];
  languages: LanguageOption[];
  session_durations_minutes: number[];
}

export interface ProfileCompleteness {
  is_complete: boolean;
  status: string;
  completion_percentage: number;
  missing_fields: string[];
}

export interface LearnerProfile {
  user_id: string;
  education_level: string;
  grade_or_class: string;
  education_stage: string;
  board_or_curriculum: string;
  academic_stream?: string;
  target_exam?: string;
  target_year?: number;
  subjects: string[];
  preferred_language: string;
  secondary_language?: string;
  explanation_language_preference: string;
  country_or_region: string;
  short_term_goal?: string;
  long_term_goal?: string;
  weekly_study_availability_hours?: number;
  preferred_session_minutes: number;
  content_difficulty_preference: string;
  voice_preference: string;
  accessibility_preferences: Record<string, any>;
  onboarding_completed: boolean;
  profile_version: number;
  completeness: ProfileCompleteness;
  created_at?: string;
  updated_at?: string;
}

export interface LearnerProfileUpdate {
  education_level?: string;
  grade_or_class?: string;
  education_stage?: string;
  board_or_curriculum?: string;
  academic_stream?: string;
  target_exam?: string;
  target_year?: number;
  subjects?: string[];
  preferred_language?: string;
  secondary_language?: string;
  explanation_language_preference?: string;
  country_or_region?: string;
  short_term_goal?: string;
  long_term_goal?: string;
  weekly_study_availability_hours?: number;
  preferred_session_minutes?: number;
  content_difficulty_preference?: string;
  voice_preference?: string;
  accessibility_preferences?: Record<string, any>;
  onboarding_completed?: boolean;
}

export interface EducationContext {
  level: string;
  level_id: string;
  stage: string;
  board: string;
  stream?: string;
  exam_tracks: string[];
}

export interface GoalsContext {
  primary?: string;
  short_term?: string;
  long_term?: string;
  target_year?: number;
}

export interface PreferencesContext {
  preferred_language: string;
  secondary_language?: string;
  explanation_language: string;
  content_difficulty: string;
  preferred_session_minutes: number;
  weekly_study_availability_hours?: number;
  voice_preference: string;
}

export interface LearningActivitySummary {
  recent_subjects: string[];
  total_documents: number;
  total_quiz_attempts: number;
  last_active?: string;
}

export interface LearnerContext {
  student_id: string;
  role: string;
  profile_version: number;
  education: EducationContext;
  goals: GoalsContext;
  subjects: string[];
  preferences: PreferencesContext;
  profile_completeness: ProfileCompleteness;
  learning_activity_summary: LearningActivitySummary;
}
