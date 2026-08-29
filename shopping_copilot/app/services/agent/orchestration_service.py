from .clarification_service import ClarificationService
from .context_manager import ContextManager
from .conversation_manager import ConversationManager
from .intent_router import IntentRouter
from .recommendation_service import RecommendationService
from .state_manager import StateManager
from .workflow.workflow_decision import WorkflowDecision

# coordiantes agent's runtime workflow
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
        context = await self.context_manager.get_context(session_id)
        state = await self.state_manager.get_state(session_id)

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

        return {
            "session_id": session_id,
            "intent": intent,
            "action": decision.action,
            "result": result,
        }

    # to transflate intent and state into next workflow action
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

        if (decision.action == "buying" and self.buying_pipeline
        ):
            return await self.buying_pipeline.run(
                query=message,
                context=context,
            )

        if (decision.action == "browsing" and self.browsing_pipeline
        ):
            return await self.browsing_pipeline.run(
                query=message,
                context=context,
            )

        if decision.action == "clarify":
            return await self.clarification_service.generate(
                message=message,
                context=context,
                state=state,
            )

        return {
            "status": "no_pipeline_configured",
            "action": decision.action,
        }