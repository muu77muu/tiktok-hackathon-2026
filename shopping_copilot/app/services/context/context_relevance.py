
# to determine which stored context is relevant to the current shopping request
# scores conversation history and preferences for relevance to the *current* query, rather than passing everything through. 
# uses embedding similarity when an embedder is available, falling back to a cheap recency + keyword-overlap heuristic otherwise -- distillation runs on every turn, so it needs a fallback that doesn't require an embedding call.

import math
from dataclasses import dataclass

from .preference_manager import ActivePreference

DEFAULT_MAX_HISTORY = 6
DEFAULT_MAX_PREFERENCES = 8
DEFAULT_THRESHOLD = 0.15  # heuristic-score floor; embedding scores use a higher effective bar

@dataclass
class ScoredItem:
    item: object
    score: float

class ContextRelevance:
    def __init__(
        self,
        embedder=None,
        max_history: int = DEFAULT_MAX_HISTORY,
        max_preferences: int = DEFAULT_MAX_PREFERENCES,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.embedder = embedder
        self.max_history = max_history
        self.max_preferences = max_preferences
        self.threshold = threshold

    async def filter_history(self, query: str, turns: list[dict]) -> list[dict]:
        if not turns:
            return []

        if self.embedder is not None:
            scored = await self._score_by_embedding(query, turns, self._turn_text)
        else:
            scored = self._score_by_heuristic(query, turns, self._turn_text, recency_weighted=True)

        return [s.item for s in scored[: self.max_history]]

    async def filter_preferences(
        self, query: str, preferences: list[ActivePreference]
    ) -> list[ActivePreference]:
        if not preferences:
            return []

        # Explicit, high-strength preferences always pass through regardless of topical relevance
        # eg. a stated allergy / must-avoid shouldnt get filtered out just because this turn's query is on another topic.
        always_keep = [p for p in preferences if p.source == "explicit" and p.strength >= 0.9]
        rest = [p for p in preferences if p not in always_keep]

        if not rest:
            return always_keep

        text_fn = lambda p: f"{p.key}: {p.value}"
        if self.embedder is not None:
            scored = await self._score_by_embedding(query, rest, text_fn)
        else:
            scored = self._score_by_heuristic(query, rest, text_fn, recency_weighted=False)

        filtered = [s.item for s in scored if s.score >= self.threshold]
        remaining_slots = max(self.max_preferences - len(always_keep), 0)
        return always_keep + filtered[:remaining_slots]

    def _turn_text(self, turn: dict) -> str:
        return turn.get("content", "")

    async def _score_by_embedding(self, query: str, items: list, text_fn) -> list[ScoredItem]:
        query_vec = await self._safe_embed(query)
        if query_vec is None:
            return self._score_by_heuristic(query, items, text_fn, recency_weighted=True)

        scored = []
        for item in items:
            vec = await self._safe_embed(text_fn(item))
            score = self._cosine_similarity(query_vec, vec) if vec else 0.0
            scored.append(ScoredItem(item=item, score=score))

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored

    async def _safe_embed(self, text: str) -> list[float] | None:
        try:
            result = self.embedder.embed(text)
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception:
            return None

    def _score_by_heuristic(
        self, query: str, items: list, text_fn, recency_weighted: bool
    ) -> list[ScoredItem]:
        query_terms = self._terms(query)
        scored = []
        n = len(items)

        for i, item in enumerate(items):
            item_terms = self._terms(text_fn(item))
            overlap = len(query_terms & item_terms) / max(len(query_terms), 1)

            recency_boost = 0.0
            if recency_weighted and n > 1:
                recency_boost = (i / (n - 1)) * 0.3  # later items score slightly higher

            scored.append(ScoredItem(item=item, score=overlap + recency_boost))

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored

    def _terms(self, text: str) -> set[str]:
        stopwords = {"a", "an", "the", "for", "with", "and", "or", "my", "of", "to", "is", "in"}
        return {w for w in text.lower().split() if w not in stopwords and len(w) > 2}

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)