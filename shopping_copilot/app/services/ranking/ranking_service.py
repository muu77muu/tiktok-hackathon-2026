
# to coordinate candidate scoring, semantic reranking, and result diversification as one pipeline: scoring (cheap, full set) -> cross-encoder (mid-cost, shortlist) -> LLM ranker (expensive, small shortlist) -> diversification.
# `strategy` picks which stages run and how aggressively diversification kicks in:
#   - "buying":   precision-first. Full stack, low diversification strength (near-duplicates are fine if they're both good matches to a specific, constrained ask).
#   - "browsing": recall/variety-first. Full stack, high diversification strength (avoid showing 10 near-identical items for an open-ended query).
#   - "fast":     scoring + cross-encoder only, skips the LLM ranker for latency-sensitive paths (e.g. typeahead, low-stakes turns).
#   - "default":  same as "fast" -- conservative baseline if no strategy is specified.

import logging

from .scoring import Scoring, ScoredCandidate
from .cross_encoder import CrossEncoderReranker
from .llm_ranker import LLMRanker
from .diversification import Diversification

logger = logging.getLogger(__name__)

STRATEGY_CONFIGS = {
    "buying": {"use_llm_ranker": True, "diversification_strength": 0.2},
    "browsing": {"use_llm_ranker": True, "diversification_strength": 0.6},
    "fast": {"use_llm_ranker": False, "diversification_strength": 0.3},
    "default": {"use_llm_ranker": False, "diversification_strength": 0.3},
}

class RankingService:
    def __init__(
        self,
        scoring: Scoring | None = None,
        cross_encoder: CrossEncoderReranker | None = None,
        llm_ranker: LLMRanker | None = None,
        diversification: Diversification | None = None,
    ):
        self.scoring = scoring or Scoring()
        self.cross_encoder = cross_encoder
        self.llm_ranker = llm_ranker
        self.diversification = diversification or Diversification()

    async def rank(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
        strategy: str = "default",
        top_k: int = 10,
    ) -> dict:
        context = context or {}
        config = STRATEGY_CONFIGS.get(strategy, STRATEGY_CONFIGS["default"])

        if not candidates:
            return self._result(query, strategy, candidates, [], "no_candidates")

        try:
            scored = await self.scoring.score(candidates, query, context)
        except Exception:
            logger.exception("scoring failed, falling back to input order")
            scored = [
                ScoredCandidate(product_id=c.get("product_id", ""), candidate=c, base_score=0.0)
                for c in candidates
            ]

        if self.cross_encoder is not None:
            try:
                scored = await self.cross_encoder.rerank(query, scored)
            except Exception:
                logger.exception("cross-encoder reranking failed, keeping prior order")

        if config["use_llm_ranker"] and self.llm_ranker is not None:
            try:
                scored = await self.llm_ranker.rank(query, scored, context)
            except Exception:
                logger.exception("LLM ranking failed, keeping prior order")

        diversified = self.diversification.diversify(
            scored, k=top_k, strength=config["diversification_strength"]
        )

        ranked_products = [self._to_output_dict(c) for c in diversified]
        return self._result(query, strategy, candidates, ranked_products, "ok")

    # merge scorting metadata back to original candidate dict so downstream consumers can see why something is ranked where it did
    def _to_output_dict(self, c: ScoredCandidate) -> dict:
        return {
            **c.candidate,
            "rank_score": c.base_score,
            "cross_encoder_score": c.cross_encoder_score,
            "llm_score": c.llm_score,
            "llm_rationale": c.llm_rationale,
        }

    def _result(
        self, query: str, strategy: str, candidates: list[dict], ranked_products: list[dict], status: str
    ) -> dict:
        return {
            "query": query,
            "strategy": strategy,
            "candidates": candidates,
            "ranked_products": ranked_products,
            "status": status,
        }