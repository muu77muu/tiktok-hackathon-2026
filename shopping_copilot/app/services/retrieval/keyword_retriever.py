
# to perform lexical product retrieval using keyword-based matching
# Lexical retrieval over the keyword index (infrastructure/search/keyword_index.py).
# Handles exact/near-exact term matches (eg. brand, model numbers, specific phrases) that vector search can under-rank because it optimizes for semantic similarity, not literal term overlap.

DEFAULT_TOP_K = 50

class KeywordRetriever:
    def __init__(self, keyword_index=None):
        self.keyword_index = keyword_index

    async def search(
        self, query: str, filters: dict | None = None, top_k: int = DEFAULT_TOP_K
    ) -> list[dict]:
        if self.keyword_index is None:
            return []

        try:
            raw_results = await self._safe_search(query, filters, top_k)
        except Exception:
            return []

        return [self._to_candidate(r) for r in raw_results]

    async def _safe_search(self, query: str, filters: dict | None, top_k: int) -> list[dict]:
        result = self.keyword_index.search(query=query, filters=filters, top_k=top_k)
        if hasattr(result, "__await__"):
            result = await result
            
        return result or []

    def _to_candidate(self, raw: dict) -> dict:
        return {
            "product_id": raw.get("id") or raw.get("product_id"),
            "score": raw.get("score", 0.0),
            "source": "keyword",
            "metadata": raw.get("metadata", raw.get("fields", {})),
        }