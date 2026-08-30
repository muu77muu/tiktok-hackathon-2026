
# to build and maintain context supplied to agent decisions
# agent-facing entry point for context assembly. Pulls session state + conversation history from SessionService, fetches a user profile if a user store is configured, and hands it all to services/context/ContextDistiller
# NOTE: this needs the current message, not just session_id

class ContextManager:
    def __init__(self, session_service, context_distiller, user_store=None):
        self.session_service = session_service
        self.context_distiller = context_distiller
        self.user_store = user_store

    async def get_context(self, session_id: str, message: str) -> dict:
        session = self.session_service.get(session_id)
        if session is None:
            session = self.session_service.create(session_id)

        user_profile = await self._get_user_profile(session.user_id)

        return await self.context_distiller.distill(
            query=message,
            conversation_history=session.conversation_history,
            session_state=session.to_dict(),
            user_profile=user_profile,
        )

    async def _get_user_profile(self, user_id: str | None) -> dict:
        if not user_id or self.user_store is None:
            return {}
        try:
            result = self.user_store.get_profile(user_id)
            if hasattr(result, "__await__"):
                result = await result
            return result or {}
        except Exception:
            return {}