-- ==============================================================================
-- TeachGenie Migration 020: Persistent Canary Managed Vault
-- Schema for envelope-encrypted identity vault ciphertext and strict service-role RLS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.canary_managed_vault (
  id TEXT PRIMARY KEY,
  ciphertext_b64 TEXT NOT NULL,
  key_version TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.canary_managed_vault ENABLE ROW LEVEL SECURITY;

-- 1. Explicitly deny all public and ordinary authenticated user access
DROP POLICY IF EXISTS "Deny public access to canary vault" ON public.canary_managed_vault;
CREATE POLICY "Deny public access to canary vault" ON public.canary_managed_vault
  FOR ALL USING (false);

-- 2. Explicitly restrict access solely to service_role
DROP POLICY IF EXISTS "Service role full access to canary vault" ON public.canary_managed_vault;
CREATE POLICY "Service role full access to canary vault" ON public.canary_managed_vault
  FOR ALL USING (auth.role() = 'service_role');
