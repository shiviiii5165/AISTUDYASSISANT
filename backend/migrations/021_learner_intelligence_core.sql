-- ============================================================================
-- LearnByGenie — Feature 1: Learner Intelligence Core Migration
-- Run this securely in your Supabase SQL Editor (supabase.com -> SQL Editor)
-- Creates canonical learner_profiles and database-driven academic configuration
-- ============================================================================

-- ─── 1. Academic Configuration Catalog Table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.academic_catalog (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL, -- 'education_level', 'curriculum', 'exam_track', 'subject', 'goal', 'language'
    code TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    stage TEXT,              -- 'PRIMARY', 'MIDDLE', 'SECONDARY', 'SENIOR_SECONDARY', 'EXAM_PREP', 'UNDERGRADUATE'
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on academic_catalog (Readable by all authenticated users, editable only by service/admin)
ALTER TABLE public.academic_catalog ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'academic_catalog' AND policyname = 'Academic catalog is publicly readable'
    ) THEN
        CREATE POLICY "Academic catalog is publicly readable" ON public.academic_catalog
            FOR SELECT USING (true);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_academic_catalog_category ON public.academic_catalog(category);
CREATE INDEX IF NOT EXISTS idx_academic_catalog_code ON public.academic_catalog(code);


-- ─── 2. Canonical Student Profile Table ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.learner_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Academic Details
    education_level TEXT NOT NULL DEFAULT 'class_11',
    grade_or_class TEXT NOT NULL DEFAULT 'Class 11',
    education_stage TEXT NOT NULL DEFAULT 'SENIOR_SECONDARY',
    board_or_curriculum TEXT NOT NULL DEFAULT 'CBSE',
    academic_stream TEXT DEFAULT 'science_pcm',
    target_exam TEXT DEFAULT 'JEE',
    target_year INT DEFAULT (EXTRACT(YEAR FROM CURRENT_DATE)::INT + 1),
    subjects TEXT[] DEFAULT ARRAY['Physics', 'Chemistry', 'Mathematics']::TEXT[],
    
    -- Language Preferences
    preferred_language TEXT NOT NULL DEFAULT 'hinglish',
    secondary_language TEXT DEFAULT 'en',
    explanation_language_preference TEXT DEFAULT 'hinglish',
    country_or_region TEXT DEFAULT 'IN',
    
    -- Study Goals & Availability
    short_term_goal TEXT DEFAULT 'Master foundational concepts and revise weekly syllabus',
    long_term_goal TEXT DEFAULT 'Excel in entrance and board examinations',
    weekly_study_availability_hours NUMERIC(4,1) DEFAULT 10.0,
    preferred_session_minutes INT DEFAULT 30,
    
    -- Interaction Preferences
    content_difficulty_preference TEXT DEFAULT 'standard',
    voice_preference TEXT DEFAULT 'neutral',
    accessibility_preferences JSONB DEFAULT '{}'::jsonb,
    
    -- State & Versioning
    onboarding_completed BOOLEAN DEFAULT FALSE,
    profile_version INT DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on learner_profiles (Strict User Isolation)
ALTER TABLE public.learner_profiles ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'learner_profiles' AND policyname = 'Users can view their own learner profile'
    ) THEN
        CREATE POLICY "Users can view their own learner profile" ON public.learner_profiles
            FOR SELECT USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'learner_profiles' AND policyname = 'Users can insert their own learner profile'
    ) THEN
        CREATE POLICY "Users can insert their own learner profile" ON public.learner_profiles
            FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'learner_profiles' AND policyname = 'Users can update their own learner profile'
    ) THEN
        CREATE POLICY "Users can update their own learner profile" ON public.learner_profiles
            FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

-- Indexes for lightning-fast tenant lookup
CREATE INDEX IF NOT EXISTS idx_learner_profiles_user_id ON public.learner_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_learner_profiles_education_level ON public.learner_profiles(education_level);
CREATE INDEX IF NOT EXISTS idx_learner_profiles_target_exam ON public.learner_profiles(target_exam);

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_learner_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_learner_profile_timestamp ON public.learner_profiles;
CREATE TRIGGER trigger_update_learner_profile_timestamp
    BEFORE UPDATE ON public.learner_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_learner_profile_timestamp();

-- ─── 3. Seed Canonical Academic Catalog Data ─────────────────────────────────
INSERT INTO public.academic_catalog (id, category, code, label, stage, display_order, metadata) VALUES
    -- Education Levels: Class 3 to 12 + Undergraduate
    ('lvl_class_3', 'education_level', 'class_3', 'Class 3', 'PRIMARY', 1, '{"has_streams": false}'::jsonb),
    ('lvl_class_4', 'education_level', 'class_4', 'Class 4', 'PRIMARY', 2, '{"has_streams": false}'::jsonb),
    ('lvl_class_5', 'education_level', 'class_5', 'Class 5', 'PRIMARY', 3, '{"has_streams": false}'::jsonb),
    ('lvl_class_6', 'education_level', 'class_6', 'Class 6', 'MIDDLE', 4, '{"has_streams": false}'::jsonb),
    ('lvl_class_7', 'education_level', 'class_7', 'Class 7', 'MIDDLE', 5, '{"has_streams": false}'::jsonb),
    ('lvl_class_8', 'education_level', 'class_8', 'Class 8', 'MIDDLE', 6, '{"has_streams": false}'::jsonb),
    ('lvl_class_9', 'education_level', 'class_9', 'Class 9', 'SECONDARY', 7, '{"has_streams": false}'::jsonb),
    ('lvl_class_10', 'education_level', 'class_10', 'Class 10', 'SECONDARY', 8, '{"has_streams": false}'::jsonb),
    ('lvl_class_11', 'education_level', 'class_11', 'Class 11', 'SENIOR_SECONDARY', 9, '{"has_streams": true, "allowed_streams": ["science_pcm", "science_pcb", "commerce", "humanities", "general"]}'::jsonb),
    ('lvl_class_12', 'education_level', 'class_12', 'Class 12', 'SENIOR_SECONDARY', 10, '{"has_streams": true, "allowed_streams": ["science_pcm", "science_pcb", "commerce", "humanities", "general"]}'::jsonb),
    ('lvl_ug_y1', 'education_level', 'ug_year_1', 'Undergraduate Year 1', 'UNDERGRADUATE', 11, '{"has_streams": true, "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]}'::jsonb),
    ('lvl_ug_y2', 'education_level', 'ug_year_2', 'Undergraduate Year 2', 'UNDERGRADUATE', 12, '{"has_streams": true, "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]}'::jsonb),
    ('lvl_ug_y3', 'education_level', 'ug_year_3', 'Undergraduate Year 3', 'UNDERGRADUATE', 13, '{"has_streams": true, "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]}'::jsonb),
    ('lvl_ug_y4', 'education_level', 'ug_year_4', 'Undergraduate Year 4', 'UNDERGRADUATE', 14, '{"has_streams": true, "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]}'::jsonb),

    -- Curricula / Boards
    ('cur_cbse', 'curriculum', 'CBSE', 'Central Board of Secondary Education (CBSE)', 'ALL', 1, '{"region": "IN"}'::jsonb),
    ('cur_icse', 'curriculum', 'ICSE_ISC', 'ICSE / ISC', 'ALL', 2, '{"region": "IN"}'::jsonb),
    ('cur_state', 'curriculum', 'STATE_BOARD', 'State Board (State Curriculum)', 'ALL', 3, '{"region": "IN"}'::jsonb),
    ('cur_ib', 'curriculum', 'IB', 'International Baccalaureate (IB)', 'ALL', 4, '{"region": "GLOBAL"}'::jsonb),
    ('cur_cambridge', 'curriculum', 'CAMBRIDGE', 'Cambridge (IGCSE / A-Levels)', 'ALL', 5, '{"region": "GLOBAL"}'::jsonb),
    ('cur_univ', 'curriculum', 'UNIVERSITY', 'University / College Syllabus', 'UNDERGRADUATE', 6, '{"region": "ALL"}'::jsonb),

    -- Exam Tracks
    ('exam_jee', 'exam_track', 'JEE', 'JEE (Main & Advanced)', 'SENIOR_SECONDARY', 1, '{"eligible_stages": ["SENIOR_SECONDARY", "EXAM_PREP"]}'::jsonb),
    ('exam_neet', 'exam_track', 'NEET', 'NEET (Medical Entrance)', 'SENIOR_SECONDARY', 2, '{"eligible_stages": ["SENIOR_SECONDARY", "EXAM_PREP"]}'::jsonb),
    ('exam_boards', 'exam_track', 'BOARDS', 'Board Examinations (CBSE/ICSE/State)', 'ALL', 3, '{"eligible_stages": ["SECONDARY", "SENIOR_SECONDARY"]}'::jsonb),
    ('exam_school', 'exam_track', 'SCHOOL_EXAMS', 'School Term Exams & Revision', 'ALL', 4, '{"eligible_stages": ["PRIMARY", "MIDDLE", "SECONDARY"]}'::jsonb),
    ('exam_ug_sem', 'exam_track', 'UG_SEMESTER', 'University Semester Exams', 'UNDERGRADUATE', 5, '{"eligible_stages": ["UNDERGRADUATE"]}'::jsonb),
    ('exam_concept', 'exam_track', 'FOUNDATION', 'Concept Mastery & Foundations', 'ALL', 6, '{"eligible_stages": ["ALL"]}'::jsonb),

    -- Academic Goals
    ('goal_mastery', 'goal', 'subject_mastery', 'Improve Subject Mastery', 'ALL', 1, '{}'::jsonb),
    ('goal_boards', 'goal', 'board_preparation', 'Board Preparation', 'ALL', 2, '{}'::jsonb),
    ('goal_jee', 'goal', 'jee_preparation', 'JEE Preparation', 'SENIOR_SECONDARY', 3, '{}'::jsonb),
    ('goal_neet', 'goal', 'neet_preparation', 'NEET Preparation', 'SENIOR_SECONDARY', 4, '{}'::jsonb),
    ('goal_school', 'goal', 'school_revision', 'School Revision', 'ALL', 5, '{}'::jsonb),
    ('goal_semester', 'goal', 'semester_preparation', 'Semester Preparation', 'UNDERGRADUATE', 6, '{}'::jsonb),
    ('goal_concept', 'goal', 'concept_learning', 'Concept Learning', 'ALL', 7, '{}'::jsonb),

    -- Languages
    ('lang_hinglish', 'language', 'hinglish', 'Hinglish (Hindi + English blend)', 'ALL', 1, '{"code": "hinglish"}'::jsonb),
    ('lang_en', 'language', 'en', 'English', 'ALL', 2, '{"code": "en"}'::jsonb),
    ('lang_hi', 'language', 'hi', 'Hindi (हिन्दी)', 'ALL', 3, '{"code": "hi"}'::jsonb),
    ('lang_bn', 'language', 'bn', 'Bengali (বাংলা)', 'ALL', 4, '{"code": "bn"}'::jsonb),
    ('lang_ta', 'language', 'ta', 'Tamil (தமிழ்)', 'ALL', 5, '{"code": "ta"}'::jsonb),
    ('lang_te', 'language', 'te', 'Telugu (తెలుగు)', 'ALL', 6, '{"code": "te"}'::jsonb),
    ('lang_mr', 'language', 'mr', 'Marathi (मराठी)', 'ALL', 7, '{"code": "mr"}'::jsonb),
    ('lang_gu', 'language', 'gu', 'Gujarati (ગુજરાતી)', 'ALL', 8, '{"code": "gu"}'::jsonb),
    ('lang_kn', 'language', 'kn', 'Kannada (ಕನ್ನಡ)', 'ALL', 9, '{"code": "kn"}'::jsonb)
ON CONFLICT (id) DO NOTHING;
