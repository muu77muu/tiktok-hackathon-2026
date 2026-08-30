
# Browsing-mode search strategy: multi-query + HyDE fan-out -> fuse -> over-generality check -> ranking -> diversification. 
# no hard filters to relax; recall comes from generating many candidate angles up front (multi-query + HyDE) rather than retrying with loosened filters.

import logging

from .scenario_analyzer import ScenarioAnalysis
from .multi_query_generator import MultiQueryResult
from .hyde_service import HydeDocument
from app.core.exceptions import OverGeneralityDetected
from app.services.retrieval.pool_analyzer import PoolAnalyzer

logger = logging.getLogger(__name__)

DEFAULT_TOP_K_PER_QUERY = 30
DEFAULT_RETURN_K = 12
DEFAULT_DIVERSIFICATION_STRENGTH = 0.6  # higher than buying's 
MAX_DIVERSIFICATION_STRENGTH = 0.85

class BrowsingStrategy:
    def __init__(
        self,
        retrieval_service=None,
        ranking_service=None,
        pool_analyzer: PoolAnalyzer | None = None,
        top_k_per_query: int = DEFAULT_TOP_K_PER_QUERY,
        return_k: int = DEFAULT_RETURN_K,
        diversification_strength: float = DEFAULT_DIVERSIFICATION_STRENGTH,
    ):
        self.retrieval_service = retrieval_service
        self.ranking_service = ranking_service
        self.pool_analyzer = pool_analyzer or PoolAnalyzer()
        self.top_k_per_query = top_k_per_query
        self.return_k = return_k
        self.diversification_strength = diversification_strength

    async def execute(
        self,
        multi_query: MultiQueryResult,
        hyde_doc: HydeDocument | None,
        scenario: ScenarioAnalysis,
        context: dict | None = None,
    ) -> list[dict]:
        context = context or {}

        candidate_lists = await self._fan_out_retrieve(multi_query, hyde_doc, context)
        candidate_lists = [c for c in candidate_lists if c]

        if not candidate_lists:
            logger.info("no candidates retrieved for any query variant, query=%r", multi_query.original)
            return []

        fused = await self.retrieval_service.fuse(candidate_lists)

        # Over-generality cutoff; browsing queries are expected to span more categories than a buying query would
        # pool_analyzer's dispersion check is what separates "healthily broad browsing result" from "so scattered it isn't useful yet."
        analysis = self.pool_analyzer.analyze(fused)
        if analysis.is_over_general:
            raise OverGeneralityDetected(
                prompt=self.pool_analyzer.build_prompt(analysis),
                suggested_dims=analysis.suggested_dims,
                pool_size=analysis.pool_size,
            )

        rank_result = await self.ranking_service.rank(
            query=multi_query.original,
            candidates=fused,
            context=context,
            strategy="browsing",
            top_k=self.return_k,
        )

        return rank_result.get("ranked_products", [])

    async def _fan_out_retrieve(
        self,
        multi_query: MultiQueryResult,
        hyde_doc: HydeDocument | None,
        context: dict,
    ) -> list[list[dict]]:
        results: list[list[dict]] = []

        for q in multi_query.queries:
            try:
                result = await self.retrieval_service.retrieve(
                    query=q, filters=None, top_k=self.top_k_per_query, context=context
                )
                results.append(result.get("candidates", []))
            except Exception:
                logger.exception("retrieval failed for query variant=%r", q)

        if hyde_doc and hyde_doc.embedding:
            try:
                hyde_result = await self.retrieval_service.retrieve_by_vector(
                    vector=hyde_doc.embedding, top_k=self.top_k_per_query, context=context
                )
                results.append(hyde_result.get("candidates", []))
            except Exception:
                logger.exception("HyDE vector retrieval failed")

        return results