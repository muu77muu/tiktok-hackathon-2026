
# to define decision-making rules specific to exploratory shopping scenarios
# Browsing-mode search strategy: broad recall via multi-query fan-out + HyDE, fused, then ranked and diversified. This has no hard filters to relax.

import logging
from dataclasses import dataclass
from typing import Any

from .scenario_analyzer import ScenarioAnalysis
from .multi_query_generator import MultiQueryResult
from .hyde_service import HydeDocument

logger = logging.getLogger(__name__)

DEFAULT_TOP_K_PER_QUERY = 15
DEFAULT_RETURN_K = 12

@dataclass
class Candidate:
    product_id: str
    score: float
    source: str  # "keyword" | "vector" | "hyde" | "fused"
    metadata: dict[str, Any]

class BrowsingStrategy:
    def __init__(
        self,
        retrieval_service=None,
        ranking_service=None,
        top_k_per_query: int = DEFAULT_TOP_K_PER_QUERY,
        return_k: int = DEFAULT_RETURN_K,
        diversification_strength: float = 0.6,  # higher than buying's default
    ):
        self.retrieval_service = retrieval_service
        self.ranking_service = ranking_service
        self.top_k_per_query = top_k_per_query
        self.return_k = return_k
        self.diversification_strength = diversification_strength

    async def execute(
        self,
        multi_query: MultiQueryResult,
        hyde_doc: HydeDocument | None,
        scenario: ScenarioAnalysis,
        context: dict | None = None,
    ) -> list[Candidate]:
        context = context or {}

        candidate_lists = await self._fan_out_retrieve(multi_query, hyde_doc, context)
        candidate_lists = [c for c in candidate_lists if c]

        if not candidate_lists:
            logger.info("no candidates retrieved for any query variant, query=%r", multi_query.original)
            return []

        fused = await self.retrieval_service.fuse(candidate_lists)

        ranked = await self.ranking_service.rank(
            candidates=fused, scenario=scenario, context=context
        )

        diversified = await self.ranking_service.diversify(
            candidates=ranked, k=self.return_k, strength=self.diversification_strength
        )

        return diversified[: self.return_k]

    async def _fan_out_retrieve(
        self,
        multi_query: MultiQueryResult,
        hyde_doc: HydeDocument | None,
        context: dict,
    ) -> list[list[Candidate]]:
        results: list[list[Candidate]] = []

        for q in multi_query.queries:
            try:
                candidates = await self.retrieval_service.retrieve(
                    query=q, filters=None, top_k=self.top_k_per_query, context=context
                )
                results.append(candidates)
            except Exception:
                logger.exception("retrieval failed for query variant=%r", q)

        if hyde_doc and hyde_doc.embedding:
            try:
                hyde_candidates = await self.retrieval_service.retrieve_by_vector(
                    vector=hyde_doc.embedding, top_k=self.top_k_per_query, context=context
                )
                results.append(hyde_candidates)
            except Exception:
                logger.exception("HyDE vector retrieval failed")

        return results