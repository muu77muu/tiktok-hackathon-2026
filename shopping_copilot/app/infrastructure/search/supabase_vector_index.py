
# Supabase pgvector-backed replacement for the in-memory vector_index.py.
# Same call contract VectorRetriever expects -- search(vector=..., filters=...,
# top_k=...) -- but async: the retriever's _safe_search awaits awaitable results.
# Similarity ordering happens in Postgres via the match_products RPC
# (migrations/001_pgvector.sql); filters are applied Python-side with the
# shared record_matches contract, so behavior matches the other indexes.

import asyncio

from .catalog_records import normalize_record
from .filtering import record_matches

DEFAULT_TOP_K = 50
# fetch extra so Python-side filtering can drop rows and still fill top_k
OVERFETCH = 3


class SupabaseVectorIndex:
    def __init__(self, client):
        self.client = client

    async def search(
        self, vector, filters: dict | None = None, top_k: int = DEFAULT_TOP_K
    ) -> list[dict]:
        # supabase-py is sync; to_thread keeps the event loop free
        rows = await asyncio.to_thread(self._rpc, list(vector), top_k * OVERFETCH)

        results = []
        for row in rows:
            metadata = normalize_record(row.get("metadata") or {})
            if not record_matches(metadata, filters):
                continue
            results.append({
                "product_id": row.get("product_id"),
                "score": float(row.get("similarity") or 0.0),
                "metadata": metadata,
            })
            if len(results) >= top_k:
                break
        return results

    def _rpc(self, vector: list[float], match_count: int) -> list[dict]:
        resp = self.client.rpc(
            "match_products",
            {"query_embedding": vector, "match_count": match_count},
        ).execute()
        return resp.data or []
