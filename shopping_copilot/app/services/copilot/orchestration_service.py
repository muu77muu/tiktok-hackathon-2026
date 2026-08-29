from typing import Any, Dict, Optional

# to determine which workflow should execute for the current conversational turn
# Responsibilities:
# - select the appropriate pipeline
# - pass session/context information
# - normalize pipeline responses
# - provide a safe fallback for unknown intent

class OrchestrationService:
    BUYING = "buying"
    BROWSING = "browsing"
    UNKNOWN = "unknown"

    def __init__(
        self,
        buying_service=None,
        browsing_service=None,
    ):
        self.buying_service = buying_service
        self.browsing_service = browsing_service

    async def execute(
        self,
        session_id: str,
        message: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        
        context = context or {}
        intent = (intent.lower().strip() if intent else self.UNKNOWN)

        if intent == self.BUYING:
            return await self._execute_buying(
                session_id=session_id,
                message=message,
                context=context,
            )
        
        if intent == self.BROWSING:
            return await self._execute_browsing(
                session_id=session_id,
                message=message,
                context=context,
            )

        return self._unknown_intent_response()

    # buying pipeline
    async def _execute_buying(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.buying_service is None:
            return {
                "response": (
                    "I understand that you're looking "
                    "to buy a specific product. "
                    "The Buying pipeline is not "
                    "connected yet."
                ),
                "recommendations": [],
                "route": self.BUYING,
                "status": "pipeline_not_configured",
            }

        result = await self._call_service(
            self.buying_service,
            session_id=session_id,
            message=message,
            context=context,
        )

        return self._normalize_pipeline_result(
            result=result,
            route=self.BUYING,
        )

    # browsing pipeline
    async def _execute_browsing(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.browsing_service is None:
            return {
                "response": (
                    "I can help you explore products "
                    "based on your needs. The Browsing "
                    "pipeline is not connected yet."
                ),
                "recommendations": [],
                "route": self.BROWSING,
                "status": "pipeline_not_configured",
            }

        result = await self._call_service(
            self.browsing_service,
            session_id=session_id,
            message=message,
            context=context,
        )

        return self._normalize_pipeline_result(
            result=result,
            route=self.BROWSING,
        )

    # helper function for pipeline to expose process or execute functions in other services
    async def _call_service(
        self,
        service: Any,
        **kwargs,
    ) -> Any:
        if hasattr(service, "process"):
            result = service.process(**kwargs)
        elif hasattr(service, "execute"):
            result = service.execute(**kwargs)
        else:
            raise AttributeError(
                "Pipeline service must expose "
                "'process' or 'execute'."
            )

        if hasattr(result, "__await__"):
            result = await result

        return result

    # normalise responses into structured input for copilot_service
    def _normalize_pipeline_result(
        self,
        result: Any,
        route: str,
    ) -> Dict[str, Any]:
        if result is None:
            return {
                "response": (
                    "I couldn't find any suitable "
                    "products."
                ),
                "recommendations": [],
                "route": route,
                "status": "no_results",
            }

        if isinstance(result, list):
            return {
                "response": (
                    "Here are some products "
                    "you may be interested in."
                ),
                "recommendations": result,
                "route": route,
                "status": "ok",
            }

        if isinstance(result, str):
            return {
                "response": result,
                "recommendations": [],
                "route": route,
                "status": "ok",
            }

        if isinstance(result, dict):
            return {
                "response": result.get(
                    "response",
                    "Here are some products "
                    "you may be interested in.",
                ),
                "recommendations": result.get(
                    "recommendations",
                    [],
                ),
                "route": result.get(
                    "route",
                    route,
                ),
                "status": result.get(
                    "status",
                    "ok",
                ),
                "metadata": result.get(
                    "metadata",
                    {},
                ),
            }

        raise TypeError(
            "Pipeline returned an unsupported "
            f"result type: {type(result).__name__}"
        )

    def _unknown_intent_response(self) -> Dict[str, Any]:
        return {
            "response": (
                "I'd be happy to help you shop. "
                "Could you tell me a little more "
                "about what you're looking for?"
            ),
            "recommendations": [],
            "route": self.UNKNOWN,
            "status": "clarification_required",
        }