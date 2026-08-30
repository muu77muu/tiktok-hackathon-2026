
# to detect when candidate pool is too broad to be worth ranking -> Over-Generality requirement
# runs immediately after retrieval, before ranking

from dataclasses import dataclass, field

DEFAULT_MIN_POOL_SIZE = 40  
DEFAULT_CATEGORY_DISPERSION_THRESHOLD = 0.6  # unique categories / pool size
DEFAULT_PRICE_SPREAD_THRESHOLD = 3.0  # max_price / min_price ratio
DEFAULT_TOP_CLUSTER_SHARE_THRESHOLD = 0.35  # largest single category's share of the pool

@dataclass
class PoolAnalysis:
    is_over_general: bool
    reason: str | None = None
    suggested_dims: list[str] = field(default_factory=list)
    pool_size: int = 0
    unique_categories: int = 0
    top_cluster_share: float = 0.0

class PoolAnalyzer:
    def __init__(
        self,
        min_pool_size: int = DEFAULT_MIN_POOL_SIZE,
        category_dispersion_threshold: float = DEFAULT_CATEGORY_DISPERSION_THRESHOLD,
        price_spread_threshold: float = DEFAULT_PRICE_SPREAD_THRESHOLD,
        top_cluster_share_threshold: float = DEFAULT_TOP_CLUSTER_SHARE_THRESHOLD,
    ):
        self.min_pool_size = min_pool_size
        self.category_dispersion_threshold = category_dispersion_threshold
        self.price_spread_threshold = price_spread_threshold
        self.top_cluster_share_threshold = top_cluster_share_threshold

    def analyze(self, candidates: list[dict]) -> PoolAnalysis:
        pool_size = len(candidates)

        if pool_size < self.min_pool_size:
            return PoolAnalysis(is_over_general=False, pool_size=pool_size)

        categories = self._category_counts(candidates)
        unique_categories = len(categories)
        dispersion = unique_categories / pool_size if pool_size else 0.0

        top_cluster_share = (max(categories.values()) / pool_size) if categories else 0.0

        price_spread = self._price_spread(candidates)

        # no single category should dominate AND prices span a wide range; both conditions together
        is_over_general = (
            dispersion >= self.category_dispersion_threshold
            and top_cluster_share < self.top_cluster_share_threshold
            and price_spread >= self.price_spread_threshold
        )

        if not is_over_general:
            return PoolAnalysis(
                is_over_general=False,
                pool_size=pool_size,
                unique_categories=unique_categories,
                top_cluster_share=top_cluster_share,
            )

        suggested_dims = self._suggest_narrowing_dims(categories, price_spread)
        reason = (
            f"{pool_size} results spread across {unique_categories} categories "
            f"with no dominant cluster and a {price_spread:.1f}x price spread"
        )

        return PoolAnalysis(
            is_over_general=True,
            reason=reason,
            suggested_dims=suggested_dims,
            pool_size=pool_size,
            unique_categories=unique_categories,
            top_cluster_share=top_cluster_share,
        )

    # deterministic fallback prompt -> LLM call may not be necessary
    def build_prompt(self, analysis: PoolAnalysis) -> str:
        if not analysis.suggested_dims:
            return ("I'm finding a lot of different options here, can you narrow down what you're looking for a bit?")
        dims = " or ".join(analysis.suggested_dims)

        return f"I'm finding a wide range of options. Do you want to narrow by {dims}?"

    def _category_counts(self, candidates: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in candidates:
            category = c.get("metadata", {}).get("category")
            if category:
                counts[category] = counts.get(category, 0) + 1
        return counts

    def _price_spread(self, candidates: list[dict]) -> float:
        prices = [
            p for p in (c.get("metadata", {}).get("price") for c in candidates)
            if isinstance(p, (int, float)) and p > 0
        ]
        if len(prices) < 2:
            return 0.0
        return max(prices) / min(prices)

    def _suggest_narrowing_dims(self, categories: dict[str, int], price_spread: float) -> list[str]:
        dims = []
        if len(categories) > 1:
            dims.append("category")
        if price_spread >= self.price_spread_threshold:
            dims.append("price")
        if not dims:
            dims.append("brand")
        return dims