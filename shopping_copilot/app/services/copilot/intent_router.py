from typing import Any, Dict, Optional

# to determine user's intent and route request to appropriate pipeline

class IntentRouter:
    BUYING = "buying"
    BROWSING = "browsing"
    UNKNOWN = "unknown"

    def __init__(
        self,
        intent_classifier=None,
        confidence_threshold: float = 0.70,
    ):
        self.intent_classifier = intent_classifier
        self.confidence_threshold = confidence_threshold

    async def route(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if not message or not message.strip():
            return self._unknown_result()

        context = context or {}
        # Use configured classifier when available
        if self.intent_classifier is not None:
            result = await self._classify(
                message=message,
                context=context,
            )

            normalized = self._normalize_result(result)
            if (
                normalized["intent"] != self.UNKNOWN
                and normalized["confidence"]
                >= self.confidence_threshold
            ):
                return normalized

            # Low-confidence classification may be handled by LLM fallback in future.
            fallback = await self._fallback_classification(
                message=message,
                context=context,
            )

            if fallback is not None:
                return fallback

        return self._keyword_fallback(message)

    async def _classify(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> Any:
        if hasattr(self.intent_classifier, "classify"):
            result = self.intent_classifier.classify(
                message=message,
                context=context,
            )

        elif hasattr(self.intent_classifier, "predict"):
            result = self.intent_classifier.predict(
                message=message,
                context=context,
            )

        else:
            raise AttributeError("Intent classifier must expose " "'classify' or 'predict'.")

        if hasattr(result, "__await__"):
            result = await result

        return result

    def _normalize_result(
        self,
        result: Any,
    ) -> Dict[str, Any]:
        if isinstance(result, str):
            intent = result.lower().strip()

            if intent in {self.BUYING, self.BROWSING}:
                return {
                    "intent": intent,
                    "confidence": 1.0,
                    "route": intent,
                    "source": "classifier",
                }

            return self._unknown_result()

        if not isinstance(result, dict):
            return self._unknown_result()

        intent = str(result.get("intent", self.UNKNOWN)).lower().strip()
        confidence = result.get(
            "confidence",
            0.0,
        )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        if intent not in {self.BUYING,self.BROWSING}:
            intent = self.UNKNOWN

        return {
            "intent": intent,
            "confidence": confidence,
            "route": (intent if intent != self.UNKNOWN else self.UNKNOWN),
            "source": result.get(
                "source",
                "classifier",
            ),
        }

    # placeholder for now
    async def _fallback_classification(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return None

    # may be temporary if classification integrated
    def _keyword_fallback(
        self,
        message: str,
    ) -> Dict[str, Any]:
        text = message.lower()
        buying_terms = {
            "buy",
            "purchase",
            "looking for",
            "find me",
            "i need",
            "i want",
            "under $",
            "below $",
            "less than",
            "price",
            "budget",
            "order",
            "get me",
        }

        browsing_terms = {
            "ideas",
            "recommend",
            "recommendations",
            "what are some",
            "what can i get",
            "options",
            "explore",
            "suggest",
            "best products",
            "show me",
        }

        buying_score = sum(
            1
            for term in buying_terms
            if term in text
        )

        browsing_score = sum(
            1
            for term in browsing_terms
            if term in text
        )

        if (buying_score > browsing_score) and (buying_score > 0):
            return {
                "intent": self.BUYING,
                "confidence": 0.60,
                "route": self.BUYING,
                "source": "keyword_fallback",
            }

        if browsing_score > 0:
            return {
                "intent": self.BROWSING,
                "confidence": 0.60,
                "route": self.BROWSING,
                "source": "keyword_fallback",
            }

        return self._unknown_result()

    def _unknown_result(self) -> Dict[str, Any]:
        return {
            "intent": self.UNKNOWN,
            "confidence": 0.0,
            "route": self.UNKNOWN,
            "source": "router",
        }