
# to determine which workflow should execute for the current conversational turn

class OrchestrationService:
    async def select_workflow(
        self,
        intent: str | None,
        context: dict | None = None,
    ) -> dict:

        if intent == "buying":
            workflow = "buying"
        elif intent == "browsing":
            workflow = "browsing"
        else:
            workflow = "clarification"

        return {
            "workflow": workflow,
            "intent": intent,
        }