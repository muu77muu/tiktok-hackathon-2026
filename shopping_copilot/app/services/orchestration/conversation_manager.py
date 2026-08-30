
# to manage lifecycle of a conversational turn
# to coordinate conversation history for the agent.
# agent-facing wrapper over services/sessions/SessionService
# NOTE: SessionService's methods are sync (see sessions/session_service.py)

class ConversationManager:
    def __init__(self, session_service):
        self.session_service = session_service

    async def record_user_message(self, session_id: str, message: str) -> None:
        session = self.session_service.get(session_id)
        if session is None:
            session = self.session_service.create(session_id)

        self.session_service.turn_manager.add_user_turn(session, message)
        self.session_service.store.update(session)

    async def record_assistant_message(
        self, session_id: str, message: str, pipeline_result: dict | None = None
    ) -> None:
        session = self.session_service.get(session_id)
        if session is None:
            return  # nothing to attach the reply to; caller's session vanished mid-turn

        self.session_service.turn_manager.add_assistant_turn(session, message, pipeline_result)
        session.turn_count += 1
        self.session_service.store.update(session)

    async def get_history(self, session_id: str) -> list[dict]:
        session = self.session_service.get(session_id)
        return session.conversation_history if session else []