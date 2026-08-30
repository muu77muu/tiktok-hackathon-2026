
# to define decision-making rules specific to buying scenarios
# buying require precision-oriented approach

import logging
from dataclasses import dataclass
from typing import Any

from .constraint_extractor import Constraints
logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 20
DEFAULT_RETURN_K = 10

@dataclass
class Candidate:
    product_id: str
    score: float
    source: str  # "keyword" | "vector" | "category" | "fused"
    metadata: dict[str, Any]

class BuyingStrategy:
    def __init__(
        self,
        retrieval_service=None,
        ranking_service=None,
        top_k: int = DEFAULT_TOP_K,
        return_k: int = DEFAULT_RETURN_K,
    ):
        self.retrieval_service = retrieval_service
        self.ranking_service = ranking_service
        self.top_k = top_k
        self.return_k = return_k

    async def execute(
        self, filters: dict, constraints: Constraints, context: dict | None = None
    ) -> list[Candidate]:
        context = context or {}

        candidates = await self.retrieval_service.retrieve(
            query=constraints.raw_query,
            filters=filters,
            top_k=self.top_k,
            context=context,
        )

        if not candidates:
            candidates = await self._retry_with_relaxed_filters(
                constraints, filters, context
            )
            if not candidates:
                return []

        ranked = await self.ranking_service.rank(
            candidates=candidates, constraints=constraints, context=context
        )

        diversified = await self.ranking_service.diversify(
            candidates=ranked, k=self.return_k
        )

        return diversified[: self.return_k]

    async def _retry_with_relaxed_filters(
        self, constraints: Constraints, filters: dict, context: dict
    ) -> list[Candidate]:
        if "should" not in filters:
            logger.info("no candidates and no relaxable filters for query=%r", constraints.raw_query)
            return []

        relaxed_filters = {k: v for k, v in filters.items() if k != "should"}
        logger.info("retrying retrieval with relaxed (should-dropped) filters")

        return await self.retrieval_service.retrieve(
            query=constraints.raw_query,
            filters=relaxed_filters,
            top_k=self.top_k,
            context=context,
        )