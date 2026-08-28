
# to generate multiple complementary queries for exploratory retrieval

class MultiQueryGenerator:
    async def generate(
        self,
        query: str,
        scenario: dict | None = None,
        expanded_queries: list[str] | None = None,
    ) -> list[str]:
        if expanded_queries:
            return expanded_queries

        return [query]