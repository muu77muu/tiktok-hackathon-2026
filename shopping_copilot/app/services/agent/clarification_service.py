
# to generate clarification requirements when the current request is too broad, ambiguous, or produces an unmanageable candidate pool
# handle Over-Generality --> Proactive Guidnace requirement

class ClarificationService:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    # generate a structured clarification response.
    async def generate(
        self,
        message: str,
        context: dict | None = None,
        state: dict | None = None,
    ) -> dict:
        if self.llm_client:
            return await self.llm_client.generate_clarification(
                message=message,
                context=context or {},
                state=state or {},
            )

        return {
            "status": "clarification_required",
            "question": (
                "Could you tell me a little more "
                "about what you are looking for?"
            ),
        }