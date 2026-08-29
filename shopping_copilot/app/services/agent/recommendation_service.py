
# to convert ranked product candidates into recommendation results suitable for the conversational layer

class RecommendationService:
    def __init__(self, ranking_service=None):
        self.ranking_service = ranking_service

    async def recommend(
        self,
        candidates: list,
        query: str,
        context: dict | None = None,
    ) -> dict:
        ranked = candidates
        if self.ranking_service:
            ranked = await self.ranking_service.rank(
                candidates=candidates,
                query=query,
                context=context or {},
            )

        return {
            "status": "recommendations_ready",
            "products": ranked,
        }