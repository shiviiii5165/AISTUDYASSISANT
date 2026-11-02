-- ==============================================================================
-- LearnByGenie — Migration 031: Gamification & Spaced Repetition Engines
-- ==============================================================================
-- Enables:
--   1. Append-Only, Idempotent XP Ledger
--   2. Daily Activity Streak Tracking with Freeze Credits
--   3. Learner Achievement Badges
--   4. Spaced Repetition Cards (SuperMemo SM-2 Engine)
--   5. Spaced Repetition Review Journal
-- ==============================================================================

-- 1. Append-Only XP Ledger (Deterministic & Idempotent)
CREATE TABLE IF NOT EXISTS public.xp_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    amount INT NOT NULL CHECK (amount > 0),
    reason_code TEXT NOT NULL CHECK (
        reason_code IN (
            'DIAGNOSTIC_COMPLETION',
            'MISTAKE_REPAIRED',
            'STEP_CHECK_SUCCESS',
            'PRACTICE_STREAK',
            'TRANSFER_VERIFIED',
            'DAILY_LOGIN',
            'SOCRATIC_SESSION_MILESTONE'
        )
    ),
    source_entity_type TEXT NOT NULL,
    source_entity_id UUID,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 2. Learner Streak Tracking
CREATE TABLE IF NOT EXISTS public.learner_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    current_streak_days INT NOT NULL DEFAULT 0,
    longest_streak_days INT NOT NULL DEFAULT 0,
    last_activity_date DATE NOT NULL DEFAULT CURRENT_DATE,
    freeze_credits_remaining INT NOT NULL DEFAULT 2,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 3. Learner Badges & Achievements
CREATE TABLE IF NOT EXISTS public.learner_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    badge_key TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'bronze' CHECK (tier IN ('bronze', 'silver', 'gold', 'platinum')),
    awarded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE(user_id, badge_key)
);

-- 4. Spaced Repetition Cards (SuperMemo SM-2)
CREATE TABLE IF NOT EXISTS public.spaced_repetition_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    skill_id TEXT NOT NULL,
    card_type TEXT NOT NULL DEFAULT 'concept_check' CHECK (
        card_type IN ('concept_check', 'formula_recall', 'mistake_avoidance')
    ),
    prompt TEXT NOT NULL,
    answer TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    ease_factor FLOAT NOT NULL DEFAULT 2.50 CHECK (ease_factor >= 1.30),
    interval_days INT NOT NULL DEFAULT 1,
    repetition_number INT NOT NULL DEFAULT 0,
    next_review_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 5. Spaced Repetition Review Journal
CREATE TABLE IF NOT EXISTS public.spaced_repetition_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES public.spaced_repetition_cards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    quality_rating INT NOT NULL CHECK (quality_rating BETWEEN 0 AND 5),
    previous_interval INT NOT NULL,
    new_interval INT NOT NULL,
    previous_ease_factor FLOAT NOT NULL,
    new_ease_factor FLOAT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_xp_ledger_user ON public.xp_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_spaced_cards_user_review ON public.spaced_repetition_cards(user_id, next_review_date);
CREATE INDEX IF NOT EXISTS idx_spaced_cards_skill ON public.spaced_repetition_cards(skill_id);

