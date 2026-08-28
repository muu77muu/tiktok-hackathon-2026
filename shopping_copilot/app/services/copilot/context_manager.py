
# to coordinate session and user context used by the conversational shopping workflow

class ContextManager:
    def __init__(
        self,
        context_distiller=None,
        short_term_memory=None,
        long_term_memory=None,
        preference_manager=None,
        context_relevance=None,
    ):
        self.context_distiller = context_distiller
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.preference_manager = preference_manager
        self.context_relevance = context_relevance

    async def build_context(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        session_state: dict | None = None,
    ) -> dict:

        return {
            "query": query,
            "conversation_history": conversation_history or [],
            "session_state": session_state or {},
            "user_profile": {},
        }