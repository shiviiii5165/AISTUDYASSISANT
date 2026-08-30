-- ============================================================================
-- TeachGenie — Security Fix: scope get_top_chunks by owning user
-- Run this ONCE in your Supabase SQL Editor (supabase.com → SQL Editor)
-- Fixes: cross-tenant document read via the Exam Predictor (get_top_chunks
--        previously filtered by pdf_id only, with no ownership check).
-- ============================================================================

-- ─── Recreate get_top_chunks with an owning-user filter ─────────────────────
-- Adds a required filter_user_id argument and joins document_chunks to pdfs
-- so only chunks belonging to a PDF owned by that user are returned. This
-- mirrors the ownership join already used by match_document_chunks
-- (see 006_fix_missing_schema.sql).
--
-- NOTE: the argument list changed, so drop the old single-purpose signature
-- first to avoid an overloaded-function ambiguity.
DROP FUNCTION IF EXISTS get_top_chunks(UUID, INT);

CREATE OR REPLACE FUNCTION get_top_chunks(
  match_pdf_id UUID,
  match_count INT,
  filter_user_id UUID
)
RETURNS TABLE(chunk_text TEXT) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT dc.chunk_text
  FROM document_chunks dc
  JOIN pdfs p ON p.id = dc.pdf_id
  WHERE dc.pdf_id = match_pdf_id
    AND p.user_id = filter_user_id
  ORDER BY dc.page_number ASC, dc.id ASC
  LIMIT match_count;
END;
$$;

-- ─── Done! ───────────────────────────────────────────────────────────────────
