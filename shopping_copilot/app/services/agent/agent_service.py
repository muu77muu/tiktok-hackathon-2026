from .orchestration_service import OrchestrationService

class AgentService:
    def __init__(self, orchestration_service: OrchestrationService):
        self.orchestration_service = orchestration_service

    # process one message through agent
    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> dict:

        return await self.orchestration_service.handle_turn(
            session_id=session_id,
            message=message,
        )