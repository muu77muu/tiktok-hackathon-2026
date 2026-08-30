
# buying pipeline: filtered retrieval -> over-generality check -> ranking -> diversification. 
# leans on metadata filters + exact/keyword matching first, with vector search filling gaps

import logging

from .constraint_extractor import Constraints
from app.core.exceptions import OverGeneralityDetected
from app.services.retrieval.pool_analyzer import PoolAnalyzer

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 100  # wide enough for pool_analyzer to judge dispersion meaningfully
DEFAULT_RETURN_K = 10
PRICE_WIDEN_STEP = 0.2  # 20% wider per relaxation level

class BuyingStrategy:
    def __init__(
        self,
        retrieval_service=None,
        ranking_service=None,
        pool_analyzer: PoolAnalyzer | None = None,
        top_k: int = DEFAULT_TOP_K,
        return_k: int = DEFAULT_RETURN_K,
    ):
        self.retrieval_service = retrieval_service
        self.ranking_service = ranking_service
        self.pool_analyzer = pool_analyzer or PoolAnalyzer()
        self.top_k = top_k
        self.return_k = return_k

    async def execute(
        self, filters: dict, constraints: Constraints, context: dict | None = None
    ) -> list[dict]:
        context = context or {}
        no_results_streak = self._get_no_results_streak(context)

        result = await self.retrieval_service.retrieve(
            query=constraints.raw_query, filters=filters, top_k=self.top_k, context=context
        )
        candidates = result.get("candidates", [])

        if not candidates:
            candidates = await self._retry_with_relaxed_filters(
                constraints, filters, context, aggressiveness=no_results_streak
            )
            if not candidates:
                return []

        # Over-generality cutoff: check dispersion BEFORE ranking spends any cross-encoder/LLM budget on a pool that's too scattered to rank meaningfully. 
        analysis = self.pool_analyzer.analyze(candidates)
        if analysis.is_over_general:
            raise OverGeneralityDetected(
                prompt=self.pool_analyzer.build_prompt(analysis),
                suggested_dims=analysis.suggested_dims,
                pool_size=analysis.pool_size,
            )

        rank_result = await self.ranking_service.rank(
            query=constraints.raw_query,
            candidates=candidates,
            context=context,
            strategy="buying",
            top_k=self.return_k,
        )

        return rank_result.get("ranked_products", [])

    # relaxation scales with how many consecutive turns this sesion has hit no_results
    # Adaptive Orchestration -> a session that keeps striking out gets progressively looser retrieval without violating the stated hard constraints
    async def _retry_with_relaxed_filters(
        self, constraints: Constraints, filters: dict, context: dict, aggressiveness: int
    ) -> list[dict]:
        relaxed = self._relax_filters(filters, aggressiveness)
        if relaxed == filters:
            logger.info("no candidates and no further relaxation available for query=%r", constraints.raw_query)
            return []

        logger.info("retrying retrieval with relaxed filters (aggressiveness=%d)", aggressiveness)
        result = await self.retrieval_service.retrieve(
            query=constraints.raw_query, filters=relaxed, top_k=self.top_k, context=context
        )
        return result.get("candidates", [])

    def _relax_filters(self, filters: dict, aggressiveness: int) -> dict:
        relaxed = {k: [dict(clause) for clause in v] for k, v in filters.items()}

        # Level 0+: drop "should" clauses -- preferences, not requirements.
        relaxed.pop("should", None)

        if aggressiveness >= 1:
            # Level 1+: widen a price range clause, so a repeated no-results streak loosens the budget gradually rather than ignoring it
            for clause in relaxed.get("must", []):
                if clause.get("field") == "price" and clause.get("op") == "range":
                    clause["value"] = self._widen_price_range(clause["value"], aggressiveness)

        if aggressiveness >= 2:
            # Level 2+: drop non-price, non-category "must" clauses (specific attributes like color/size); price and category stay as the last hard constraints
            relaxed["must"] = [
                c for c in relaxed.get("must", [])
                if c.get("field") in ("price", "category")
            ]

        return relaxed

    def _widen_price_range(self, range_value: dict, aggressiveness: int) -> dict:
        widened = dict(range_value)
        factor = PRICE_WIDEN_STEP * aggressiveness
        if "lte" in widened:
            widened["lte"] = widened["lte"] * (1 + factor)
        if "gte" in widened:
            widened["gte"] = max(0, widened["gte"] * (1 - factor))
        return widened

    def _get_no_results_streak(self, context: dict) -> int:
        return context.get("adaptive_signals", {}).get("consecutive_no_results", 0)