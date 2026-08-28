
# to expand exploratory queries into related concepts that may improve discovery across product catalog

class QueryExpander:
    async def expand(
        self,
        query: str,
        scenario: dict | None = None,
    ) -> list[str]:
        return [query]