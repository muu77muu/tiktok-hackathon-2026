
# to perform lexical product retrieval using keyword-based matching

class KeywordRetriever:
    async def retrieve(
        self,
        query: str,
        top_k: int = 100,
    ) -> list[dict]:
        return []