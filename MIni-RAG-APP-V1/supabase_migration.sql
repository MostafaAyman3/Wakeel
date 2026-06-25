-- Enable the pgvector extension to work with embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Projects Table
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Assets Table
CREATE TABLE IF NOT EXISTS assets (
    asset_id SERIAL PRIMARY KEY,
    asset_uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    asset_type TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    asset_size INTEGER NOT NULL,
    asset_config JSONB,
    asset_project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks Table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id SERIAL PRIMARY KEY,
    chunk_uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB,
    chunk_order INTEGER NOT NULL,
    chunk_project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE NOT NULL,
    chunk_asset_id INTEGER REFERENCES assets(asset_id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add vector column to chunks if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chunks' AND column_name='vector') THEN
        ALTER TABLE chunks ADD COLUMN vector vector(1536);
    END IF;
END $$;

-- Vector Search Function
-- NOTE: We must drop the function before changing its return signature
DROP FUNCTION IF EXISTS public.match_vectors(vector, float, int, text, bigint);
DROP FUNCTION IF EXISTS public.match_vectors(vector, double precision, integer, text);
DROP FUNCTION IF EXISTS public.match_vectors(vector, double precision, integer, text, integer);

CREATE OR REPLACE FUNCTION match_vectors (
  query_embedding vector,
  match_threshold float,
  match_count int,
  target_table_name text,
  filter_project_id int DEFAULT NULL
)
RETURNS TABLE (
  chunk_id int,
  chunk_text text,
  chunk_metadata jsonb,
  score float,
  chunk_project_id int
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY EXECUTE format('
    SELECT 
      chunk_id, 
      chunk_text, 
      chunk_metadata, 
      1 - (vector <=> %L) as score,
      chunk_project_id
    FROM %I
    WHERE (1 - (vector <=> %L) > %L)
      AND (%L IS NULL OR chunk_project_id = %L)
    ORDER BY score DESC
    LIMIT %L', 
    query_embedding, target_table_name, query_embedding, match_threshold, filter_project_id, filter_project_id, match_count);
END;
$$;
