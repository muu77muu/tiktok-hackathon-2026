
# to diversify ranked results to avoid excessive redundancy and improve discovery coverage
# Diversifies final ranked list using a MMR-style greedy selection: at each step, pick the candidate that's a good balance of (still highly relevant) and (dissimilar to what's already been picked). Prevents returning 10 near-identical variants of the same product.
# `strength` controls relevance/diversity tradeoff (0 = pure relevance order, 1 = maximize diversity, relevance mostly ignored). 
# - buying_strategy.py should pass a low strength (precision matters more)
# - browsing_strategy.py should pass a higher one (variety matters more)

from .scoring import ScoredCandidate

DEFAULT_STRENGTH = 0.3

class Diversification:
    def diversify(
        self, candidates: list[ScoredCandidate], k: int, strength: float = DEFAULT_STRENGTH
    ) -> list[ScoredCandidate]:
        if not candidates:
            return []
        if strength <= 0:
            return candidates[:k]

        remaining = list(candidates)
        selected: list[ScoredCandidate] = []

        max_relevance = max((c.base_score for c in remaining), default=1.0) or 1.0

        while remaining and len(selected) < k:
            best_candidate = None
            best_mmr = float("-inf")

            for c in remaining:
                relevance = c.base_score / max_relevance
                redundancy = self._max_similarity(c, selected)
                mmr = (1 - strength) * relevance - strength * redundancy

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_candidate = c

            selected.append(best_candidate)
            remaining.remove(best_candidate)

        return selected

    def _max_similarity(self, candidate: ScoredCandidate, selected: list[ScoredCandidate]) -> float:
        if not selected:
            return 0.0
        return max(self._similarity(candidate, s) for s in selected)

    # cheap structural similarity only (eg. category, brand, tags)
    def _similarity(self, a: ScoredCandidate, b: ScoredCandidate) -> float:
        meta_a = a.candidate.get("metadata", {})
        meta_b = b.candidate.get("metadata", {})

        signals = 0
        matches = 0

        for field in ("category", "subcategory", "brand"):
            if meta_a.get(field) is not None and meta_b.get(field) is not None:
                signals += 1
                if meta_a.get(field) == meta_b.get(field):
                    matches += 1

        tags_a = set(meta_a.get("tags", []))
        tags_b = set(meta_b.get("tags", []))
        if tags_a or tags_b:
            signals += 1
            union = tags_a | tags_b
            if union:
                matches += len(tags_a & tags_b) / len(union)

        return matches / signals if signals > 0 else 0.0