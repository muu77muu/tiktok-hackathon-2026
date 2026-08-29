from typing import Any, Dict, Optional

# to determine user's intent and route request to appropriate pipeline

BUYING = "buying"
BROWSING = "browsing"
UNKNOWN = "unknown"

class IntentRouter:
    def __init__(self, intent_classifier=None):
        self.intent_classifier = intent_classifier

    async def route(
        self,
        message: str,
        context: dict | None = None,
        state: dict | None = None,
    ) -> str:

        context = context or {}
        state = state or {}

        if self.intent_classifier:
            return await self.intent_classifier.classify(
                message=message,
                context=context,
                state=state,
            )

        return UNKNOWN