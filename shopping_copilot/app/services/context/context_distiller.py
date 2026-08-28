
# to distill conversation history into relevant context for the current shopping interaction

class ContextDistiller:
    async def distill(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        session_state: dict | None = None,
        user_profile: dict | None = None,
    ) -> dict:

        return {
            "query": query,
            "session_context": session_state or {},
            "user_context": user_profile or {},
            "relevant_history": conversation_history or [],
            "active_preferences": [],
            "active_constraints": [],
            "summary": None,
        }