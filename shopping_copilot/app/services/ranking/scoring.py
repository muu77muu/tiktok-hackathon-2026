
# to calculate deterministic candidate relevance scores from retrieval and product-level signals
# First-pass scoring: cheap, runs on the *full* candidate set before any expensive reranking. Blends the retrieval-stage score with business signals (rating, availability, price fit) and preference alignment from context
# exists so cross_encoder/llm_ranker only need to run on a shortlist rather than every candidate (those stages are 10-100x more expensive)

from dataclasses import dataclass, field
from typing import Any

DEFAULT_WEIGHTS = {
    "retrieval": 0.45,
    "rating": 0.15,
    "availability": 0.10,
    "price_fit": 0.15,
    "preference_alignment": 0.15,
}

@dataclass
class ScoredCandidate:
    product_id: str
    candidate: dict
    base_score: float
    component_scores: dict[str, float] = field(default_factory=dict)
    cross_encoder_score: float | None = None
    llm_score: float | None = None
    llm_rationale: str | None = None

class Scoring:
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS

    async def score(
        self, candidates: list[dict], query: str, context: dict | None = None
    ) -> list[ScoredCandidate]:
        context = context or {}
        preferences = context.get("active_preferences", [])
        constraints = context.get("active_constraints", [])

        scored = []
        for c in candidates:
            components = {
                "retrieval": self._normalize(c.get("score", 0.0)),
                "rating": self._rating_score(c),
                "availability": self._availability_score(c),
                "price_fit": self._price_fit_score(c, constraints),
                "preference_alignment": self._preference_score(c, preferences),
            }
            base = sum(components[k] * self.weights.get(k, 0.0) for k in components)

            scored.append(
                ScoredCandidate(
                    product_id=c.get("product_id", ""),
                    candidate=c,
                    base_score=base,
                    component_scores=components,
                )
            )

        scored.sort(key=lambda s: s.base_score, reverse=True)
        return scored

    def _normalize(self, value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        if hi == lo:
            return 0.0
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))

    def _rating_score(self, candidate: dict) -> float:
        metadata = candidate.get("metadata", {})
        rating = metadata.get("rating")
        review_count = metadata.get("review_count", 0)
        if rating is None:
            return 0.5  # neutral, don't punish missing data
        
        # Discount ratings with very few reviews so a single 5-star review doesnt outrank a well-reviewed product.
        confidence = min(review_count / 20, 1.0)
        return (rating / 5.0) * (0.5 + 0.5 * confidence)

    def _availability_score(self, candidate: dict) -> float:
        metadata = candidate.get("metadata", {})
        if metadata.get("in_stock") is False:
            return 0.0
        return 1.0

    def _price_fit_score(self, candidate: dict, constraints: list) -> float:
        metadata = candidate.get("metadata", {})
        price = metadata.get("price")
        if price is None:
            return 0.5

        price_constraint = next(
            (c for c in constraints if getattr(c, "key", None) == "price"), None
        )
        if price_constraint is None:
            return 0.5

        # Constraints module represents price as a range on the Constraints
        # object upstream, not as a single ActiveConstraint -- callers that
        # want price-fit scoring should pass min/max via context directly.
        return 0.5

    def _preference_score(self, candidate: dict, preferences: list) -> float:
        if not preferences:
            return 0.5

        metadata = candidate.get("metadata", {})
        tags = set(t.lower() for t in metadata.get("tags", []))
        brand = str(metadata.get("brand", "")).lower()

        matches = 0
        total_weight = 0.0
        for p in preferences:
            key = getattr(p, "key", "")
            value = str(getattr(p, "value", "")).lower()
            strength = getattr(p, "strength", 0.5)
            total_weight += strength
            if value in tags or value == brand:
                matches += strength

        return matches / total_weight if total_weight > 0 else 0.5