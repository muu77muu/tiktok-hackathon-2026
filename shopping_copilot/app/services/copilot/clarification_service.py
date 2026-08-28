
# to generate clarification requirements when the current request is too broad, ambiguous, or produces an unmanageable candidate pool
# handle Over-Generality --> Proactive Guidnace requirement

class ClarificationService:
    def should_clarify(
        self,
        context: dict,
        retrieval_result: dict | None = None,
    ) -> bool:

        if not retrieval_result:
            return False

        return retrieval_result.get(
            "is_over_general",
            False,
        )

    async def generate(
        self,
        query: str,
        context: dict | None = None,
        reason: str | None = None,
    ) -> dict:

        return {
            "needs_clarification": True,
            "reason": reason,
            "question": None,
            "options": [],
        }