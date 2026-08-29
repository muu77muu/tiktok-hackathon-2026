
# to coordinate conversation state, context, intent routing, Buying/Browsing pipelines, recommendations, and clarification

class CopilotService:
    def __init__(
        self,
        conversation_manager=None,
        intent_router=None,
        state_manager=None,
        context_manager=None,
        clarification_service=None,
        recommendation_service=None,
        orchestration_service=None,
    ):
        self.conversation_manager = conversation_manager
        self.intent_router = intent_router
        self.state_manager = state_manager
        self.context_manager = context_manager
        self.clarification_service = clarification_service
        self.recommendation_service = recommendation_service
        self.orchestration_service = orchestration_service

    # process one conversational shopping turn (up to 10 steps per turn)

    async def process(
        self,
        session_id: str,
        message: str,
    ) -> dict:

        # 1. input validation
        if not session_id:
            raise ValueError("session_id is required")
        if not message or not message.strip():
            raise ValueError("message is required")
        message = message.strip()

        # 2. record conversation turn
        if self.conversation_manager:
            await self.conversation_manager.record_user_message(
                session_id=session_id,
                message=message,
            )

        # 3. retrieve current context
        context = {}
        if self.context_manager:
            context = await self.context_manager.get_context(session_id=session_id)

        # 4. detect intent
        intent = None;
        if self.intent_router:
            intent_result = await self.intent_router.route(
                session_id=session_id,
                context=context
            )
            intent = intent_result.get("intent")


        # 5. update conversational state
        if self.state_manager:
            await self.state_manager.update_state(
                session_id=session_id,
                message=message,
                intent=intent,
                context=context
            )

        # 6. check whether clarification is needed
        if self.clarification_service:
            clarification = await (
                self.clarification_service.check(
                    message=message,
                    intent=intent,
                    context=context
                )
            )

            if clarification.get("required"):
                response = clarification.get(
                    "question",
                    "Could you provide more details?"
                )

                return {
                    "session_id": session_id,
                    "message": message,
                    "intent": intent,
                    "response": response,
                    "recommendations": [],
                    "status": "clarification_required",
                }

        # 7. execute buying/browsing pipeline orchestration service 
        result = {}
        if self.orchestration_service:
            result = await self.orchestration_service.execute(
                session_id=session_id,
                message=message,
                intent=intent,
                context=context
            )

        # 8. generate recommendations
        recommendations = result.get("recommendations", [])
        if (not recommendations and self.recommendation_service):
            recommendations = await (
                self.recommendation_service.recommend(
                    message=message,
                    intent=intent,
                    context=context
                )
            )

        # 9. generate conversation response
        response = result.get("response", "Here are some products that may be relevant:")

        # 10. save assistant response
        if self.conversation_manager:
            await self.conversation_manager.record_assistant_message(
                session_id=session_id,
                message=response
            )
        
        return {
            "session_id": session_id,
            "message": message,
            "intent": intent,
            "response": response,
            "recommendations": recommendations,
            "status": "copilot_ok",
        }