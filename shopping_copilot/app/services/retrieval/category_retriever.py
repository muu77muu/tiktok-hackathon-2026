
# to retrieve products using category and category-hierarchy info
# Retrieves by category/taxonomy match rather than text similarity. 
# Mainly useful as a recall supplement in the hybrid strategy: when constraints name a specific category, this catches well-fitting products that happen to be described in wording distant enough from the query to rank low in keyword/vector search.

DEFAULT_TOP_K = 30

class CategoryRetriever:
    def __init__(self, category_index=None):
        self.category_index = category_index

    async def search(
        self,
        category: str | None,
        filters: dict | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[dict]:
        if self.category_index is None or not category:
            return []

        try:
            raw_results = await self._safe_search(category, filters, top_k)
        except Exception:
            return []

        return [self._to_candidate(r) for r in raw_results]

    async def _safe_search(self, category: str, filters: dict | None, top_k: int) -> list[dict]:
        result = self.category_index.search(category=category, filters=filters, top_k=top_k)
        if hasattr(result, "__await__"):
            result = await result
        return result or []

    def _to_candidate(self, raw: dict) -> dict:
        return {
            "product_id": raw.get("id") or raw.get("product_id"),
            # Category matches have no inherent relevance score
            "score": raw.get("score", 0.5),
            "source": "category",
            "metadata": raw.get("metadata", raw.get("fields", {})),
        }