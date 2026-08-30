
# routes a message to "buying" or "browsing" (exploratory) intent, or "unclear" when confidence is too low
# wwo-tier classification: 
# - a cheap classifier first (ai/classifiers/intent_classifier.py, eg. embeddings + logistic regression) since this runs on every turn
# - its own confidence is too low to trust.
# continuity matters here: regardless of intent signal, it inherits the previous turn's intent rather than forcing a fresh, likely-low-confidence classification.

DEFAULT_CONFIDENCE_THRESHOLD = 0.55
SHORT_FOLLOWUP_WORD_COUNT = 5

INTENT_SCHEMA_HINT = """
Return JSON: {"intent": "buying" | "browsing", "confidence": number}
"buying" = the user knows roughly what they want and is stating constraints
(category, brand, price, features) to narrow down to specific products.
"browsing" = open-ended, exploratory, or scenario-based ("gift for...",
"something for...") without a clear, specific target yet.
"""

class IntentRouter:
    def __init__(
        self,
        classifier=None,
        llm_client=None,
        prompt_template: str | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self.classifier = classifier
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
        self.confidence_threshold = confidence_threshold

    def _default_prompt(self) -> str:
        return ("You classify shopping messages by intent.\n\n" + INTENT_SCHEMA_HINT)

    async def route(self, message: str, context: dict, state: dict) -> str:
        if self._is_short_followup(message) and self._has_active_intent(context, state):
            return state.get("intent") or self._infer_from_context(context)

        intent, confidence = await self._classify(message)

        if confidence < self.confidence_threshold:
            # Low confidence on a message mid-conversation; prefer sticking with the established intent over changing between buying/browsing/clarify on every turn
            prior = state.get("intent")
            if prior in ("buying", "browsing"):
                return prior
            return "unclear"

        return intent

    async def _classify(self, message: str) -> tuple[str, float]:
        if self.classifier is not None:
            try:
                result = self.classifier.classify(message)
                if hasattr(result, "__await__"):
                    result = await result
                return result
            except Exception:
                pass  # fall through to LLM

        if self.llm_client is None:
            return "unclear", 0.0

        try:
            raw = await self.llm_client.complete(system=self.prompt_template, user=message)
            return self._parse(raw)
        except Exception:
            return "unclear", 0.0

    def _parse(self, raw: str) -> tuple[str, float]:
        import json

        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            intent = data.get("intent", "unclear")
            confidence = float(data.get("confidence", 0.0))
            if intent not in ("buying", "browsing"):
                intent = "unclear"
            return intent, confidence
        except (json.JSONDecodeError, ValueError, TypeError):
            return "unclear", 0.0

    def _is_short_followup(self, message: str) -> bool:
        return len(message.strip().split()) <= SHORT_FOLLOWUP_WORD_COUNT

    def _has_active_intent(self, context: dict, state: dict) -> bool:
        return bool(
            state.get("intent")
            or context.get("prior_constraints")
            or context.get("prior_scenario")
        )

    def _infer_from_context(self, context: dict) -> str:
        if context.get("prior_constraints"):
            return "buying"
        if context.get("prior_scenario"):
            return "browsing"
        return "unclear"