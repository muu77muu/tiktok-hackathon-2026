
# to perform semantic product retrieval using vector similarity
# Semantic retrieval over the vector index (infrastructure/search/vector_index.py).
# Exposes two entry points: 
# - `search` (embeds the query text itself)
# - `search_by_vector` (takes a pre-computed embedding directly which is used by browsing's HyDE flow where the embedding comes from a hypothetical document rather than the raw query.

DEFAULT_TOP_K = 50

class VectorRetriever:
    def __init__(self, vector_index=None, embedder=None):
        self.vector_index = vector_index
        self.embedder = embedder

    async def search(
        self, query: str, filters: dict | None = None, top_k: int = DEFAULT_TOP_K
    ) -> list[dict]:
        if self.vector_index is None or self.embedder is None:
            return []

        vector = await self._safe_embed(query)
        if vector is None:
            return []

        return await self.search_by_vector(vector, filters=filters, top_k=top_k)

    async def search_by_vector(
        self, vector: list[float], filters: dict | None = None, top_k: int = DEFAULT_TOP_K
    ) -> list[dict]:
        if self.vector_index is None:
            return []

        try:
            raw_results = await self._safe_search(vector, filters, top_k)
        except Exception:
            return []

        return [self._to_candidate(r) for r in raw_results]

    async def _safe_embed(self, text: str) -> list[float] | None:
        try:
            result = self.embedder.embed(text)
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception:
            return None

    async def _safe_search(self, vector: list[float], filters: dict | None, top_k: int) -> list[dict]:
        result = self.vector_index.search(vector=vector, filters=filters, top_k=top_k)
        if hasattr(result, "__await__"):
            result = await result
        return result or []

    def _to_candidate(self, raw: dict) -> dict:
        return {
            "product_id": raw.get("id") or raw.get("product_id"),
            "score": raw.get("score", raw.get("similarity", 0.0)),
            "source": "vector",
            "metadata": raw.get("metadata", raw.get("fields", {})),
        }