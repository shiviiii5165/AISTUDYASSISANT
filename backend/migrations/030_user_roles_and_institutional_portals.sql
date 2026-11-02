-- ==============================================================================
-- LearnByGenie — Migration 030: User Roles & Institutional Portals
-- ==============================================================================
-- Enables:
--   1. Institutional Portals (School Administrator, Teacher, Parent)
--   2. Schools & Institutional Multi-Tenancy
--   3. Classrooms (Batches / Cohorts) & Student Enrollments
--   4. Parent-Student Linkage & Progress Digest Settings
-- ==============================================================================

-- 1. Institutional Entities (Schools / Organizations)
CREATE TABLE IF NOT EXISTS public.schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT UNIQUE,
    subscription_tier TEXT NOT NULL DEFAULT 'standard' CHECK (subscription_tier IN ('free', 'standard', 'enterprise')),
    max_seats INT NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 2. School Memberships (School Admins, Teachers, Staff)
CREATE TABLE IF NOT EXISTS public.school_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('school_admin', 'teacher', 'staff')),
    department TEXT DEFAULT 'General',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE(school_id, user_id)
);

-- 3. Classrooms (Batches / Cohorts)
CREATE TABLE IF NOT EXISTS public.classrooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL,
    name TEXT NOT NULL,
    grade_level TEXT NOT NULL,
    academic_stream TEXT DEFAULT 'general',
    academic_year TEXT NOT NULL DEFAULT '2026-2027',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 4. Classroom Enrollments
CREATE TABLE IF NOT EXISTS public.classroom_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classroom_id UUID NOT NULL REFERENCES public.classrooms(id) ON DELETE CASCADE,
    student_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'enrolled' CHECK (status IN ('enrolled', 'withdrawn', 'completed')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE(classroom_id, student_id)
);

-- 5. Parent-Student Links
CREATE TABLE IF NOT EXISTS public.parent_student_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID NOT NULL,
    student_id UUID NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'guardian' CHECK (relationship IN ('mother', 'father', 'guardian')),
    verification_status TEXT NOT NULL DEFAULT 'verified' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    invitation_code TEXT UNIQUE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE(parent_id, student_id)
);

-- 6. Parent Digest & Notification Settings
CREATE TABLE IF NOT EXISTS public.parent_digest_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_id UUID NOT NULL REFERENCES public.parent_student_links(id) ON DELETE CASCADE UNIQUE,
    email_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    digest_frequency TEXT NOT NULL DEFAULT 'weekly' CHECK (digest_frequency IN ('daily', 'weekly', 'biweekly')),
    alert_on_persistent_mistake BOOLEAN NOT NULL DEFAULT true,
    alert_on_mastery_gain BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_school_memberships_user ON public.school_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_school_memberships_school ON public.school_memberships(school_id);
CREATE INDEX IF NOT EXISTS idx_classrooms_teacher ON public.classrooms(teacher_id);
CREATE INDEX IF NOT EXISTS idx_classrooms_school ON public.classrooms(school_id);
CREATE INDEX IF NOT EXISTS idx_classroom_enrollments_student ON public.classroom_enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_parent_student_links_parent ON public.parent_student_links(parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_student_links_student ON public.parent_student_links(student_id);

