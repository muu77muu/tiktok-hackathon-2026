
# to retrieve products using category and category-hierarchy info

class CategoryRetriever:
    async def retrieve(
        self,
        category: str | None = None,
        categories: list[str] | None = None,
        top_k: int = 100,
    ) -> list[dict]:

        return []