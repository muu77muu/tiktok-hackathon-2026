
# to determine user's intent and route request to appropriate pipeline

class IntentRouter:
    async def route(
        self,
        message: str,
        context: dict | None = None,
    ) -> dict:

        return {
            "intent": None,
            "confidence": 0.0,
            "reason": None,
        }