-- Migration 015: Presentation Engine Persistent Caching with Versioning and TTL
-- Stores Topic Ontology checklists and Stock Photo results across server instances.

CREATE TABLE IF NOT EXISTS ontology_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_key TEXT UNIQUE NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  checklist JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + interval '90 days')
);

CREATE INDEX IF NOT EXISTS idx_ontology_cache_lookup 
  ON ontology_cache(topic_key, version, expires_at);

CREATE TABLE IF NOT EXISTS image_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_hash TEXT UNIQUE NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  provider TEXT NOT NULL,
  image_url TEXT NOT NULL,
  metadata JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + interval '30 days')
);

CREATE INDEX IF NOT EXISTS idx_image_cache_lookup 
  ON image_cache(query_hash, version, expires_at);

-- RLS policies for cache tables
ALTER TABLE ontology_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_cache ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'ontology_cache' AND policyname = 'Allow read on ontology cache'
  ) THEN
    CREATE POLICY "Allow read on ontology cache" ON ontology_cache FOR SELECT USING (true);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'ontology_cache' AND policyname = 'Allow write on ontology cache'
  ) THEN
    CREATE POLICY "Allow write on ontology cache" ON ontology_cache FOR ALL USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'image_cache' AND policyname = 'Allow read on image cache'
  ) THEN
    CREATE POLICY "Allow read on image cache" ON image_cache FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'image_cache' AND policyname = 'Allow write on image cache'
  ) THEN
    CREATE POLICY "Allow write on image cache" ON image_cache FOR ALL USING (true);
  END IF;
END $$;
