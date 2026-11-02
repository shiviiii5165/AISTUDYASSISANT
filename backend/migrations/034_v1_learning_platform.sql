-- ==============================================================================
-- LearnByGenie - Migration 034: /api/v1 Learning Platform Tables
-- Requires migration 033. The backend service role bypasses RLS; policies below
-- allow students read-only direct access to their own rows. Tables without a policy
-- hold secrets, answer data or peer data, and deny all direct client access.
-- ==============================================================================

ALTER TABLE public.cat_sessions ADD COLUMN IF NOT EXISTS class_level INT;
ALTER TABLE public.cat_sessions ADD COLUMN IF NOT EXISTS current_item_id TEXT;

CREATE TABLE IF NOT EXISTS public.ncert_concepts (
    concept_id TEXT PRIMARY KEY, class_level INT NOT NULL, subject TEXT NOT NULL,
    title TEXT NOT NULL, citation_id TEXT NOT NULL UNIQUE,
    prerequisites JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE IF NOT EXISTS public.ncert_chunks (
    chunk_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES public.ncert_concepts(concept_id) ON DELETE CASCADE,
    class_level INT NOT NULL, subject TEXT NOT NULL, citation_id TEXT NOT NULL,
    title TEXT NOT NULL, block TEXT NOT NULL, text TEXT NOT NULL, search_terms TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS public.practice_sessions_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, concept_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('practice','transfer','retention')),
    sequence_index INT NOT NULL DEFAULT 0, consecutive_failures INT NOT NULL DEFAULT 0,
    current_item_id TEXT, helped BOOLEAN NOT NULL DEFAULT false, fade_stage INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.practice_attempts_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL,
    session_id UUID NOT NULL REFERENCES public.practice_sessions_v1(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL, item_id TEXT NOT NULL, correct BOOLEAN NOT NULL,
    idempotency_key TEXT NOT NULL, confidence TEXT, hints_used INT NOT NULL DEFAULT 0,
    result JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (student_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_attempts_student_concept ON public.practice_attempts_v1(student_id, concept_id);
CREATE TABLE IF NOT EXISTS public.error_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, concept_id TEXT NOT NULL,
    item_id TEXT, token TEXT NOT NULL CHECK (token ~ '^E(0[1-9]|1[0-9]|20)$'),
    tier SMALLINT NOT NULL, rule TEXT NOT NULL, deterministic BOOLEAN NOT NULL,
    entrenched BOOLEAN NOT NULL DEFAULT false, status TEXT NOT NULL CHECK (status IN ('active','resolved')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_error_tokens_student ON public.error_tokens(student_id, status);
CREATE TABLE IF NOT EXISTS public.tutor_sessions_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, concept_id TEXT, mode TEXT,
    current_item_id TEXT, paper JSONB NOT NULL DEFAULT '[]'::jsonb, socratic_turn INT NOT NULL DEFAULT 0,
    seen JSONB NOT NULL DEFAULT '[]'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.tutor_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, mode TEXT, query TEXT NOT NULL,
    gates JSONB NOT NULL, outcome TEXT NOT NULL, citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tutor_audit_student ON public.tutor_audit(student_id);
CREATE TABLE IF NOT EXISTS public.safety_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, kind TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.consent_otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), request_id TEXT NOT NULL UNIQUE, student_id UUID NOT NULL,
    purpose TEXT NOT NULL, contact_hash TEXT NOT NULL, otp_hash TEXT NOT NULL, attempts INT NOT NULL DEFAULT 0,
    consumed BOOLEAN NOT NULL DEFAULT false, expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.erasure_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL, requested_by UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','partial','completed')),
    failed_tables JSONB NOT NULL DEFAULT '[]'::jsonb, requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS public.mfa_factors (
    user_id UUID PRIMARY KEY, secret_encrypted TEXT NOT NULL, confirmed BOOLEAN NOT NULL DEFAULT false,
    last_counter BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS public.quests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('daily','recovery','boss')), quest_key TEXT NOT NULL, title TEXT NOT NULL,
    estimated_minutes INT NOT NULL, tasks JSONB NOT NULL, status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (student_id, kind, quest_key)
);
CREATE TABLE IF NOT EXISTS public.activity_days (
    student_id UUID NOT NULL, day DATE NOT NULL, PRIMARY KEY (student_id, day)
);
CREATE TABLE IF NOT EXISTS public.guilds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL, join_code TEXT NOT NULL UNIQUE,
    class_band TEXT NOT NULL CHECK (class_band IN ('6-8','9-12')), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.guild_members (
    guild_id UUID NOT NULL REFERENCES public.guilds(id) ON DELETE CASCADE,
    student_id UUID NOT NULL UNIQUE, joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_id, student_id)
);
CREATE TABLE IF NOT EXISTS public.league_entries (
    student_id UUID PRIMARY KEY, pseudonym TEXT NOT NULL UNIQUE, opted_in BOOLEAN NOT NULL DEFAULT true,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.implementation_intentions (
    student_id UUID PRIMARY KEY, when_text TEXT NOT NULL, action_text TEXT NOT NULL,
    statement TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.homework_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL,
    classroom_id UUID NOT NULL REFERENCES public.classrooms(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL, teacher_id UUID NOT NULL, status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (student_id, classroom_id, concept_id)
);
CREATE TABLE IF NOT EXISTS public.creator_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code TEXT NOT NULL UNIQUE, creator_id UUID NOT NULL,
    concept_id TEXT NOT NULL, campaign TEXT NOT NULL, url TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.creator_link_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code TEXT NOT NULL REFERENCES public.creator_links(code) ON DELETE CASCADE,
    event TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['ncert_concepts','ncert_chunks','practice_sessions_v1','practice_attempts_v1','error_tokens',
        'tutor_sessions_v1','tutor_audit','safety_events','consent_otps','erasure_requests','mfa_factors','quests',
        'activity_days','guilds','guild_members','league_entries','implementation_intentions','homework_assignments',
        'creator_links','creator_link_events'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    END LOOP;
    FOREACH t IN ARRAY ARRAY['error_tokens','quests','activity_days','homework_assignments','implementation_intentions'] LOOP
        EXECUTE format('DROP POLICY IF EXISTS own_select ON public.%I', t);
        EXECUTE format('CREATE POLICY own_select ON public.%I FOR SELECT USING (student_id = auth.uid())', t);
    END LOOP;
END $$;

-- cat_sessions (from 033) has no client policy: its rows hold live responses.
