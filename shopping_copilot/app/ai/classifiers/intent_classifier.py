from dataclasses import dataclass


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    method: str

# Intent classifier interface (may consider lightweight ML, rules, embeddings, or other classification models in the future)
class IntentClassifier:
    BUYING = "buying"
    BROWSING = "browsing"
    UNCLEAR = "unclear"

    def classify(
        self,
        message: str,
        context: dict | None = None,
    ) -> IntentPrediction:

        raise NotImplementedError(
            "Intent classifier has not been configured."
        )