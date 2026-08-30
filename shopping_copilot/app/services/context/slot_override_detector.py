
# to detect 'Intent Override' requirement
# Two signals, checked cheapy-first:
#  1. Reset-phrase match (fast, deterministic, no model calls)
#  2. Topic-drift via embedding similarity (catches resets that don't use an explicit reset phrase. Only checked on messages with enough words to embed meaningfully; short refinements ("under $50", "in red") are exempted so they aren't misread as drift just for being terse.
# context_distiller.py is the caller: on override, it nulls out prior_constraints / prior_scenario before they'd otherwise be merged into the new turn 

import math
from dataclasses import dataclass

RESET_PHRASES = {
    "actually",
    "instead",
    "never mind",
    "nevermind",
    "forget that",
    "forget it",
    "scratch that",
    "not that",
    "something else",
    "change of plans",
    "different thing",
}

DEFAULT_SIMILARITY_THRESHOLD = 0.35
DEFAULT_MIN_WORDS_FOR_DRIFT_CHECK = 4

@dataclass
class OverrideResult:
    is_override: bool
    reason: str | None = None

class SlotOverrideDetector:
    def __init__(
        self,
        embedder=None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        min_words_for_drift_check: int = DEFAULT_MIN_WORDS_FOR_DRIFT_CHECK,
    ):
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.min_words_for_drift_check = min_words_for_drift_check

    async def detect(self, message: str, prior_focus_text: str | None) -> OverrideResult:
        lowered = message.lower()
        for phrase in RESET_PHRASES:
            if phrase in lowered:
                return OverrideResult(is_override=True, reason=f"reset_phrase:{phrase!r}")

        if not prior_focus_text or self.embedder is None:
            return OverrideResult(is_override=False)

        if len(message.split()) < self.min_words_for_drift_check:
            return OverrideResult(is_override=False)

        message_vec = await self._safe_embed(message)
        focus_vec = await self._safe_embed(prior_focus_text)
        if message_vec is None or focus_vec is None:
            return OverrideResult(is_override=False)

        similarity = self._cosine(message_vec, focus_vec)
        if similarity < self.similarity_threshold:
            return OverrideResult(
                is_override=True, reason=f"topic_drift(similarity={similarity:.2f})"
            )

        return OverrideResult(is_override=False)

    async def _safe_embed(self, text: str) -> list[float] | None:
        try:
            result = self.embedder.embed(text)
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception:
            return None

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)