
# to perform semantic reranking of retrieved candidates using a cross-encoder model

class CrossEncoderRanker:
    async def rank(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
    ) -> list[dict]:
        return candidates