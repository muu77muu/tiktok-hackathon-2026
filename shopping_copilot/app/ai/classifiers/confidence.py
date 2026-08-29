
# evaluate classification confidence and determine if fallback reasoning is required

class ConfidenceEvaluator:
    def __init__(
        self,
        threshold: float = 0.75,
    ):
        self.threshold = threshold

    def is_confident(
        self,
        confidence: float,
    ) -> bool:
        return confidence >= self.threshold

    def requires_fallback(
        self,
        confidence: float,
    ) -> bool:
        return not self.is_confident(confidence)

    def evaluate(
        self,
        confidence: float,
    ) -> dict:

        return {
            "confidence": confidence,
            "threshold": self.threshold,
            "confident": self.is_confident(
                confidence
            ),
            "requires_fallback": self.requires_fallback(
                confidence
            ),
        }