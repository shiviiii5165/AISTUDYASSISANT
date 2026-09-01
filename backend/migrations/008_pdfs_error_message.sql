-- ============================================================================
-- TeachGenie — Fix: dedicated error column for pdfs
-- Run this ONCE in your Supabase SQL Editor (supabase.com → SQL Editor)
-- Fixes: PDF-processing error text was written into the `subject` column
--        (schema misuse + leaks raw exception text to the client via /pdfs/list).
-- ============================================================================

-- Add a nullable error_message column so processing failures are recorded in a
-- field meant for it, instead of overwriting the user-facing `subject`.
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS error_message TEXT;

-- ─── Done! ───────────────────────────────────────────────────────────────────
