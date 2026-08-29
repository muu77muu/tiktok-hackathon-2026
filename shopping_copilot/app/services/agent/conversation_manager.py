
# to manage lifecycle of a conversational turn
# to coordinate conversation history for the agent.
# Coordinates conversation history for the agent.

class ConversationManager:

    def __init__(self, conversation_service=None):
        self.conversation_service = conversation_service

    async def record_user_message(
        self,
        session_id: str,
        message: str,
    ) -> None:
        if self.conversation_service:
            await self.conversation_service.add_message(
                session_id=session_id,
                role="user",
                content=message,
            )

    async def record_agent_message(
        self,
        session_id: str,
        message: str,
    ) -> None:
        if self.conversation_service:
            await self.conversation_service.add_message(
                session_id=session_id,
                role="assistant",
                content=message,
            )