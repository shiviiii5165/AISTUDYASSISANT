-- ============================================================================
-- TeachGenie — Bug Fix SQL Migration
-- Run this ONCE in your Supabase SQL Editor (supabase.com → SQL Editor)
-- Fixes: Bugs 4, 5, 6, 14, 15
-- ============================================================================

-- ─── Bug 4: Add missing source_type column to pdfs table ─────────────────────
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'pdf';

-- ─── Bug 5: Add missing chunk_index column to document_chunks table ──────────
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER DEFAULT 0;

-- ─── Bug 6: Create missing quiz_scores table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_scores (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  pdf_id UUID,
  session_id TEXT,
  question_id TEXT,
  topic TEXT,
  is_correct BOOLEAN DEFAULT false,
  answered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on quiz_scores
ALTER TABLE quiz_scores ENABLE ROW LEVEL SECURITY;

-- Policies: users can only see and insert their own scores
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'quiz_scores' AND policyname = 'Users see own scores'
  ) THEN
    CREATE POLICY "Users see own scores" ON quiz_scores
      FOR SELECT USING (auth.uid() = user_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'quiz_scores' AND policyname = 'Users insert own scores'
  ) THEN
    CREATE POLICY "Users insert own scores" ON quiz_scores
      FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

-- ─── Bug 14: Create missing get_top_chunks RPC function ──────────────────────
-- Used by the Exam Predictor to fetch all document chunks
CREATE OR REPLACE FUNCTION get_top_chunks(match_pdf_id UUID, match_count INT)
RETURNS TABLE(chunk_text TEXT) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT dc.chunk_text FROM document_chunks dc
  WHERE dc.pdf_id = match_pdf_id
  ORDER BY dc.page_number ASC, dc.id ASC
  LIMIT match_count;
END;
$$;

-- ─── Bug 15: Create missing match_document_chunks RPC function ───────────────
-- Used by the RAG pipeline for semantic similarity search (requires pgvector)
-- NOTE: Gemini embedding-001 uses 768 dimensions. If your embedding column
-- uses a different dimension, change vector(768) accordingly.
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(768),
  match_count INT,
  filter_pdf_id UUID,
  filter_user_id UUID
)
RETURNS TABLE(
  id UUID,
  chunk_text TEXT,
  page_number INT,
  similarity FLOAT
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.chunk_text,
    dc.page_number,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  JOIN pdfs p ON p.id = dc.pdf_id
  WHERE dc.pdf_id = filter_pdf_id
    AND p.user_id = filter_user_id
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ─── Done! ───────────────────────────────────────────────────────────────────
