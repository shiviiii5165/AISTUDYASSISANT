-- ==============================================================================
-- LearnByGenie - Migration 035: Parent-link consent default and erasure receipts
-- Requires 030 and 034. Existing links keep their current verification_status.
-- ==============================================================================

ALTER TABLE public.parent_student_links DROP CONSTRAINT IF EXISTS parent_student_links_verification_status_check;
ALTER TABLE public.parent_student_links ADD CONSTRAINT parent_student_links_verification_status_check
    CHECK (verification_status IN ('pending_otp', 'pending', 'verified', 'rejected'));
ALTER TABLE public.parent_student_links ALTER COLUMN verification_status SET DEFAULT 'pending_otp';

-- A completed erasure receipt is immutable.
CREATE OR REPLACE FUNCTION public.protect_completed_erasure()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Completed erasure receipts are immutable' USING ERRCODE = 'check_violation';
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_completed_erasure ON public.erasure_requests;
CREATE TRIGGER trg_protect_completed_erasure
    BEFORE UPDATE OR DELETE ON public.erasure_requests
    FOR EACH ROW WHEN (OLD.status = 'completed')
    EXECUTE FUNCTION public.protect_completed_erasure();
