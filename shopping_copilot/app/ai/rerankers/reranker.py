from dataclasses import dataclass


@dataclass
class RankedCandidate:
    product_id: str
    score: float
    rank: int
    metadata: dict | None = None

# Provider-agnostic semantic reranking interface (may wrap cross-encoder, LLM-based ranker, or hybrid reranking strategy in the future)
class Reranker:
    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
    ) -> list[RankedCandidate]:

        raise NotImplementedError(
            "Reranker has not been configured."
        )