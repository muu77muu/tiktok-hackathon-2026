
# to perform semantic reranking of retrieved candidates using a cross-encoder model
# Cross-encoder reranking: scores (query, candidate) pairs jointly through a cross-encoder model, which captures semantic relevance that a dot-product retrieval score misses 
# too expensive to run over every candidate, hence only running on the top-N from scoring.py

import asyncio

from .scoring import ScoredCandidate

DEFAULT_SHORTLIST_SIZE = 50
DEFAULT_BLEND_WEIGHT = 0.5  # how much cross-encoder score counts vs. base_score

class CrossEncoderReranker:
    def __init__(
        self,
        model_client=None,
        shortlist_size: int = DEFAULT_SHORTLIST_SIZE,
        blend_weight: float = DEFAULT_BLEND_WEIGHT,
        max_concurrency: int = 10,
    ):
        self.model_client = model_client
        self.shortlist_size = shortlist_size
        self.blend_weight = blend_weight
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def rerank(
        self, query: str, candidates: list[ScoredCandidate]
    ) -> list[ScoredCandidate]:
        if not candidates or self.model_client is None:
            return candidates

        shortlist = candidates[: self.shortlist_size]
        remainder = candidates[self.shortlist_size:]

        scored_shortlist = await asyncio.gather(
            *[self._score_one(query, c) for c in shortlist]
        )

        raw_scores = [c.cross_encoder_score for c in scored_shortlist if c.cross_encoder_score is not None]
        normalized = self._min_max_normalize(scored_shortlist, raw_scores)

        for c in normalized:
            if c.cross_encoder_score is not None:
                c.base_score = (
                    (1 - self.blend_weight) * c.base_score
                    + self.blend_weight * c.cross_encoder_score
                )

        normalized.sort(key=lambda c: c.base_score, reverse=True)
        return normalized + remainder

    async def _score_one(self, query: str, candidate: ScoredCandidate) -> ScoredCandidate:
        async with self._semaphore:
            document = self._document_text(candidate.candidate)
            try:
                raw_score = self.model_client.score_pair(query, document)
                if hasattr(raw_score, "__await__"):
                    raw_score = await raw_score
                candidate.cross_encoder_score = float(raw_score)
            except Exception:
                candidate.cross_encoder_score = None
            return candidate

    def _document_text(self, candidate: dict) -> str:
        metadata = candidate.get("metadata", {})
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        return f"{title}. {description}".strip()

    def _min_max_normalize(
        self, candidates: list[ScoredCandidate], raw_scores: list[float]
    ) -> list[ScoredCandidate]:
        if not raw_scores:
            return candidates
        lo, hi = min(raw_scores), max(raw_scores)
        if hi == lo:
            for c in candidates:
                if c.cross_encoder_score is not None:
                    c.cross_encoder_score = 0.5
            return candidates
        for c in candidates:
            if c.cross_encoder_score is not None:
                c.cross_encoder_score = (c.cross_encoder_score - lo) / (hi - lo)
        return candidates