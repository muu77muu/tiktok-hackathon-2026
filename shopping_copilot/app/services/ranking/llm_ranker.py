
# to perform final semantic ranking using a LLM

class LLMRanker:
    async def rank(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
    ) -> list[dict]:
        return candidates