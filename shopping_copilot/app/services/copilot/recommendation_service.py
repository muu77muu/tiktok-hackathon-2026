
# to convert ranked product candidates into recommendation results suitable for the conversational layer

class RecommendationService:
    def __init__(
        self,
        ranking_service=None,
    ):
        self.ranking_service = ranking_service

    async def recommend(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
        top_k: int = 10,
    ) -> dict:

        if self.ranking_service is None:
            ranked = candidates[:top_k]
        else:
            result = await self.ranking_service.rank(
                query=query,
                candidates=candidates,
                context=context,
                top_k=top_k,
            )

            ranked = result.get(
                "ranked_products",
                [],
            )

        return {
            "products": ranked,
            "count": len(ranked),
        }