-- ==============================================================================
-- LearnByGenie - Migration 033: Learning Core & RLS Hardening
-- ==============================================================================
--   1. Enables RLS on the tables from migrations 030-032, which had none.
--   2. Allows zero-amount XP rows, which the 10 XP/day easy-repeat cap produces.
--   3. Rejects prerequisite cycles with a trigger.
--   4. Adds IRT parameters, CAT sessions, BKT state, review schedule,
--      the dual-ledger XP event table and guardian consent.
-- The backend's service role bypasses RLS. Policies below govern direct client access.
-- ==============================================================================

-- 1. RLS for existing tables. Tables with no policy deny all direct client access.
ALTER TABLE public.schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.school_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.classrooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.classroom_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parent_student_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parent_digest_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.xp_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_streaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spaced_repetition_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spaced_repetition_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parent_student_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parent_student_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_role_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.creator_practice_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS own_memberships_select ON public.school_memberships;
CREATE POLICY own_memberships_select ON public.school_memberships
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS teacher_classrooms_select ON public.classrooms;
CREATE POLICY teacher_classrooms_select ON public.classrooms
    FOR SELECT USING (teacher_id = auth.uid());
DROP POLICY IF EXISTS own_enrollments_select ON public.classroom_enrollments;
CREATE POLICY own_enrollments_select ON public.classroom_enrollments
    FOR SELECT USING (student_id = auth.uid());
DROP POLICY IF EXISTS own_parent_links_select ON public.parent_student_links;
CREATE POLICY own_parent_links_select ON public.parent_student_links
    FOR SELECT USING (parent_id = auth.uid() OR student_id = auth.uid());
DROP POLICY IF EXISTS own_xp_select ON public.xp_ledger;
CREATE POLICY own_xp_select ON public.xp_ledger
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS own_streak_select ON public.learner_streaks;
CREATE POLICY own_streak_select ON public.learner_streaks
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS own_badges_select ON public.learner_badges;
CREATE POLICY own_badges_select ON public.learner_badges
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS own_cards_select ON public.spaced_repetition_cards;
CREATE POLICY own_cards_select ON public.spaced_repetition_cards
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS own_reviews_select ON public.spaced_repetition_reviews;
CREATE POLICY own_reviews_select ON public.spaced_repetition_reviews
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS own_invitations_select ON public.parent_student_invitations;
CREATE POLICY own_invitations_select ON public.parent_student_invitations
    FOR SELECT USING (student_id = auth.uid());
DROP POLICY IF EXISTS own_role_select ON public.user_roles;
CREATE POLICY own_role_select ON public.user_roles
    FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS author_items_select ON public.creator_practice_items;
CREATE POLICY author_items_select ON public.creator_practice_items
    FOR SELECT USING (author_id = auth.uid());

-- 2. RULE_XP_07 can legitimately compute 0 XP once the daily cap is reached.
ALTER TABLE public.xp_ledger DROP CONSTRAINT IF EXISTS xp_ledger_amount_check;
ALTER TABLE public.xp_ledger ADD CONSTRAINT xp_ledger_amount_check CHECK (amount >= 0);

-- 3. Prerequisite DAG acyclicity.
CREATE OR REPLACE FUNCTION public.reject_prerequisite_cycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT NEW.is_active THEN
        RETURN NEW;
    END IF;
    -- Serialize graph edits: concurrent inserts could otherwise form a cycle together.
    PERFORM pg_advisory_xact_lock(hashtext('skill_prerequisites_dag'));
    IF EXISTS (
        WITH RECURSIVE downstream(skill_id) AS (
            SELECT NEW.dependent_skill_id
            UNION
            SELECT e.dependent_skill_id
            FROM public.skill_prerequisites e
            JOIN downstream d ON e.prerequisite_skill_id = d.skill_id
            WHERE e.is_active AND e.id IS DISTINCT FROM NEW.id
        )
        SELECT 1 FROM downstream WHERE skill_id = NEW.prerequisite_skill_id
    ) THEN
        RAISE EXCEPTION 'Prerequisite cycle: % -> %', NEW.prerequisite_skill_id, NEW.dependent_skill_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reject_prerequisite_cycle ON public.skill_prerequisites;
CREATE TRIGGER trg_reject_prerequisite_cycle
    BEFORE INSERT OR UPDATE ON public.skill_prerequisites
    FOR EACH ROW EXECUTE FUNCTION public.reject_prerequisite_cycle();

-- 4. New tables.
-- No client policy: item parameters and answer data stay server-side.
CREATE TABLE IF NOT EXISTS public.item_irt_parameters (
    item_id TEXT PRIMARY KEY,
    model TEXT NOT NULL CHECK (model IN ('1PL', '2PL', '3PL')),
    b DOUBLE PRECISION NOT NULL,
    a DOUBLE PRECISION NOT NULL DEFAULT 1 CHECK (a > 0),
    c DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (c >= 0 AND c < 1),
    calibration_status TEXT NOT NULL DEFAULT 'provisional'
        CHECK (calibration_status IN ('provisional', 'calibrated')),
    sample_size INT NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
    calibrated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.cat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    subject TEXT NOT NULL,
    theta DOUBLE PRECISION NOT NULL DEFAULT 0,
    se DOUBLE PRECISION NOT NULL DEFAULT 1,
    items_answered INT NOT NULL DEFAULT 0 CHECK (items_answered BETWEEN 0 AND 15),
    responses JSONB NOT NULL DEFAULT '[]'::jsonb,
    stop_reason TEXT CHECK (stop_reason IN ('precision_reached', 'max_items', 'bank_exhausted')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_cat_sessions_student ON public.cat_sessions(student_id);

CREATE TABLE IF NOT EXISTS public.learner_bkt_state (
    student_id UUID NOT NULL,
    skill_id TEXT NOT NULL,
    p_l DOUBLE PRECISION NOT NULL CHECK (p_l BETWEEN 0 AND 1),
    p_s DOUBLE PRECISION NOT NULL DEFAULT 0.1 CHECK (p_s BETWEEN 0 AND 0.20),
    p_g DOUBLE PRECISION NOT NULL DEFAULT 0.2 CHECK (p_g BETWEEN 0 AND 1),
    tier SMALLINT NOT NULL DEFAULT 0 CHECK (tier BETWEEN 0 AND 5),
    unhinted_streak INT NOT NULL DEFAULT 0 CHECK (unhinted_streak >= 0),
    retention_clock_start TIMESTAMPTZ,
    day7_passed BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (student_id, skill_id),
    CONSTRAINT bkt_non_degenerate CHECK (1 - p_s > p_g)
);

CREATE TABLE IF NOT EXISTS public.review_schedule (
    student_id UUID NOT NULL,
    skill_id TEXT NOT NULL,
    stability_days DOUBLE PRECISION NOT NULL CHECK (stability_days > 0),
    step INT NOT NULL DEFAULT 0 CHECK (step >= 0),
    due_at TIMESTAMPTZ NOT NULL,
    last_reviewed_at TIMESTAMPTZ,
    PRIMARY KEY (student_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_review_schedule_due ON public.review_schedule(student_id, due_at);

CREATE TABLE IF NOT EXISTS public.xp_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    rule_id TEXT NOT NULL CHECK (rule_id ~ '^RULE_XP_0[1-7]$'),
    target_entity_id TEXT NOT NULL,
    time_window_bucket BIGINT NOT NULL,
    ledger CHAR(1) NOT NULL CHECK (ledger IN ('A', 'B')),
    amount INT NOT NULL CHECK (amount >= 0),
    badge TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_xp_event UNIQUE (student_id, rule_id, target_entity_id, time_window_bucket)
);

CREATE TABLE IF NOT EXISTS public.guardian_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    guardian_id UUID,
    purpose TEXT NOT NULL CHECK (purpose IN ('learning_analytics', 'parent_reports', 'school_sharing')),
    method TEXT NOT NULL CHECK (method IN ('otp', 'digital_token')),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    withdrawn_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_guardian_consents_student ON public.guardian_consents(student_id, purpose);

ALTER TABLE public.item_irt_parameters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_bkt_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.xp_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guardian_consents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS own_bkt_select ON public.learner_bkt_state;
CREATE POLICY own_bkt_select ON public.learner_bkt_state
    FOR SELECT USING (student_id = auth.uid());
DROP POLICY IF EXISTS own_reviews_due_select ON public.review_schedule;
CREATE POLICY own_reviews_due_select ON public.review_schedule
    FOR SELECT USING (student_id = auth.uid());
DROP POLICY IF EXISTS own_xp_events_select ON public.xp_events;
CREATE POLICY own_xp_events_select ON public.xp_events
    FOR SELECT USING (student_id = auth.uid());
DROP POLICY IF EXISTS own_consents_select ON public.guardian_consents;
CREATE POLICY own_consents_select ON public.guardian_consents
    FOR SELECT USING (student_id = auth.uid() OR guardian_id = auth.uid());
