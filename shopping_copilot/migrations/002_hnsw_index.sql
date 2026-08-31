-- Phase 3: vector index. Run ONLY after scripts/backfill_embeddings.py has
-- finished populating Catalog.embedding (check: select count(*) from "Catalog"
-- where embedding is not null; -- should be ~50000).
--
-- HNSW over IVFFlat: no training step, better recall at this scale.
-- vector_cosine_ops matches the <=> operator used by match_products().

create index if not exists catalog_embedding_hnsw_idx
  on "Catalog"
  using hnsw (embedding extensions.vector_cosine_ops);
