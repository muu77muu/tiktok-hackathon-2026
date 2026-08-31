-- Phase 1: pgvector vectorstore for semantic search over Catalog.
-- Run this in the Supabase dashboard SQL editor (project fjswotfxrxspvbbpwexv)
-- or via a direct Postgres connection. Safe to re-run (idempotent).
--
-- The HNSW index is intentionally NOT created here -- it lives in
-- 002_hnsw_index.sql and must be run AFTER scripts/backfill_embeddings.py
-- has populated the embedding column (building the index on filled data is
-- much faster than maintaining it during 50k inserts).

-- 1. Enable pgvector (Supabase convention: extensions schema).
create extension if not exists vector with schema extensions;

-- 2. Embedding column: 1024 dims = Qwen/Qwen3-Embedding-0.6B (EMBEDDING_DIMENSIONS).
alter table "Catalog" add column if not exists embedding extensions.vector(1024);

-- 3. Semantic search RPC called by SupabaseVectorIndex via PostgREST.
--    Returns metadata as jsonb so it maps 1:1 onto the app's to_metadata()
--    candidate contract regardless of the underlying column types.
create or replace function match_products(
  query_embedding extensions.vector(1024),
  match_count int default 150
)
returns table (
  product_id text,
  similarity double precision,
  metadata jsonb
)
language sql
stable
as $$
  select
    c.parent_asin::text as product_id,
    1 - (c.embedding <=> query_embedding) as similarity,
    jsonb_build_object(
      'title', c.title,
      'price', c.price,
      'categories', c.categories,
      'average_rating', c.average_rating,
      'rating_number', c.rating_number,
      'store', c.store
    ) as metadata
  from "Catalog" c
  where c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

grant execute on function match_products(extensions.vector(1024), int)
  to anon, authenticated, service_role;
