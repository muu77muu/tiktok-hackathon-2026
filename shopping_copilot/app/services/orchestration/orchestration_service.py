
# to coordinate agent's runtime workflow

from .clarification_service import ClarificationService
from .context_manager import ContextManager
from .conversation_manager import ConversationManager
from .intent_router import IntentRouter
from .recommendation_service import RecommendationService
from .state_manager import StateManager
from .workflow_decision import WorkflowDecision

class OrchestrationService:
    def __init__(
        self,
        conversation_manager: ConversationManager,
        intent_router: IntentRouter,
        state_manager: StateManager,
        context_manager: ContextManager,
        clarification_service: ClarificationService,
        recommendation_service: RecommendationService,
        buying_pipeline=None,
        browsing_pipeline=None,
    ):
        self.conversation_manager = conversation_manager
        self.intent_router = intent_router
        self.state_manager = state_manager
        self.context_manager = context_manager
        self.clarification_service = clarification_service
        self.recommendation_service = recommendation_service

        self.buying_pipeline = buying_pipeline
        self.browsing_pipeline = browsing_pipeline

    # execute one conversational turn
    async def handle_turn(
        self,
        session_id: str,
        message: str,
    ) -> dict:
        state = await self.state_manager.get_state(session_id)
        context = await self.context_manager.get_context(session_id, message)

        await self.conversation_manager.record_user_message(
            session_id=session_id,
            message=message,
        )

        intent = await self.intent_router.route(
            message=message,
            context=context,
            state=state,
        )

        decision = self._make_decision(
            intent=intent,
            state=state,
        )

        result = await self._execute_decision(
            decision=decision,
            session_id=session_id,
            message=message,
            context=context,
            state=state,
        )

        await self.state_manager.update_state(
            session_id=session_id,
            updates={
                "previous_intent": state.get("intent"),
                "intent": intent,
                "next_action": decision.action,
            },
        )

        await self.conversation_manager.record_assistant_message(
            session_id=session_id,
            message=result.get("message", ""),
            pipeline_result=result.get("pipeline_result"),
        )

        return {
            "session_id": session_id,
            "intent": intent,
            "action": decision.action,
            "result": result,
        }

    # to translate intent and state into next workflow action
    def _make_decision(
        self,
        intent: str,
        state: dict,
    ) -> WorkflowDecision:
        if intent == "buying":
            return WorkflowDecision(
                action="buying",
                intent=intent,
                reason="High-intent purchasing request detected.",
            )

        elif intent == "browsing":
            return WorkflowDecision(
                action="browsing",
                intent=intent,
                reason="Open-ended browsing request detected.",
            )

        return WorkflowDecision(
            action="clarify",
            intent=intent,
            reason="Intent confidence is insufficient.",
        )

    async def _execute_decision(
        self,
        decision: WorkflowDecision,
        session_id: str,
        message: str,
        context: dict,
        state: dict,
    ) -> dict:

        if decision.action == "buying" and self.buying_pipeline:
            pipeline_result = await self.buying_pipeline.run(query=message, context=context)
            return await self._handle_pipeline_result(pipeline_result, message, context, state)

        if decision.action == "browsing" and self.browsing_pipeline:
            pipeline_result = await self.browsing_pipeline.run(query=message, context=context)
            return await self._handle_pipeline_result(pipeline_result, message, context, state)

        if decision.action == "clarify":
            clarification = await self.clarification_service.generate(
                message=message,
                context=context,
                state=state,
            )
            return clarification

        return {
            "status": "no_pipeline_configured",
            "action": decision.action,
            "message": "",
        }

    async def _handle_pipeline_result(
        self, pipeline_result: dict, message: str, context: dict, state: dict
    ) -> dict:
        if pipeline_result.get("status") == "needs_clarification":
            clarification = await self.clarification_service.generate(
                message=message,
                context=context,
                state=state,
                clarification_prompt=pipeline_result.get("clarification_prompt"),
            )
            clarification["pipeline_result"] = pipeline_result
            return clarification

        formatted = await self.recommendation_service.present(pipeline_result, context)
        formatted["pipeline_result"] = pipeline_result
        return formatted