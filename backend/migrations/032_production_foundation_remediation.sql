-- ==============================================================================
-- LearnByGenie — Migration 032: Production Foundation & Security Remediation
-- ==============================================================================
-- Enables:
--   1. Cryptographically Secure Parent-Student Invitations (Single-Use, Expiry)
--   2. Parent-Student Relationship Audit Trail (DPDP Act 2023)
--   3. Authoritative Server-Side User Roles & Role Change Audit Log
--   4. Content Creator Question Review Workflow (PENDING_REVIEW -> APPROVED/REJECTED)
--   5. Expanded XP Reason Codes for Blueprint Two-Ledger Architecture
-- ==============================================================================

-- 1. Cryptographically Secure Parent-Student Invitations
CREATE TABLE IF NOT EXISTS public.parent_student_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    invitation_code TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_redeemed BOOLEAN NOT NULL DEFAULT false,
    redeemed_by_parent_id UUID,
    redeemed_at TIMESTAMPTZ,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_parent_invitations_code ON public.parent_student_invitations(invitation_code);
CREATE INDEX IF NOT EXISTS idx_parent_invitations_student ON public.parent_student_invitations(student_id);

-- 2. Parent-Student Relationship Audit Trail
CREATE TABLE IF NOT EXISTS public.parent_student_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (
        event_type IN ('INVITATION_GENERATED', 'INVITATION_REDEEMED', 'INVITATION_REVOKED', 'LINK_CREATED', 'LINK_REMOVED')
    ),
    student_id UUID NOT NULL,
    parent_id UUID,
    invitation_code TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_parent_student_audit_student ON public.parent_student_audit(student_id);
CREATE INDEX IF NOT EXISTS idx_parent_student_audit_parent ON public.parent_student_audit(parent_id);

-- 3. Authoritative Server-Side User Roles
CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID PRIMARY KEY,
    role TEXT NOT NULL CHECK (
        role IN ('student', 'parent', 'teacher', 'school_admin', 'content_creator', 'admin', 'super_admin')
    ),
    assigned_by UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.user_role_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_user_id UUID NOT NULL,
    actor_admin_id UUID NOT NULL,
    old_role TEXT NOT NULL,
    new_role TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_user_role_audit_target ON public.user_role_audit(target_user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_audit_actor ON public.user_role_audit(actor_admin_id);

-- 4. Content Creator Question Review Workflow
CREATE TABLE IF NOT EXISTS public.creator_practice_items (
    id UUID PRIMARY KEY,
    skill_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    grade_band TEXT NOT NULL,
    difficulty_band TEXT NOT NULL,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    options JSONB NOT NULL DEFAULT '[]'::jsonb,
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_mistake_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    author_id UUID NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (
        review_status IN ('pending_review', 'approved', 'rejected')
    ),
    reviewed_by UUID,
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_creator_items_skill ON public.creator_practice_items(skill_id);
CREATE INDEX IF NOT EXISTS idx_creator_items_author ON public.creator_practice_items(author_id);
CREATE INDEX IF NOT EXISTS idx_creator_items_status ON public.creator_practice_items(review_status);

-- 5. Expand XP Ledger CHECK constraint to include canonical Blueprint XP Reason Codes
DO $$
BEGIN
    -- Drop existing check constraint if present to update valid reason codes
    ALTER TABLE public.xp_ledger DROP CONSTRAINT IF EXISTS xp_ledger_reason_code_check;
    ALTER TABLE public.xp_ledger ADD CONSTRAINT xp_ledger_reason_code_check CHECK (
        reason_code IN (
            'DIAGNOSTIC_COMPLETION',
            'MISTAKE_REPAIRED',
            'STEP_CHECK_SUCCESS',
            'PRACTICE_STREAK',
            'TRANSFER_VERIFIED',
            'DAILY_LOGIN',
            'SOCRATIC_SESSION_MILESTONE',
            'BASELINE_DIAGNOSTIC',
            'ERROR_RESOLUTION_UNSEEN',
            'TIER_3_INDEPENDENT_PROFICIENCY',
            'TIER_4_FRESH_TRANSFER',
            'TIER_5_DELAYED_RETENTION',
            'TEACH_BACK_RUBRIC_PASS',
            'REPEATED_EASY_PRACTICE'
        )
    );
EXCEPTION
    WHEN undefined_table THEN
        NULL; -- In case table does not exist yet during fresh migration run
END $$;

