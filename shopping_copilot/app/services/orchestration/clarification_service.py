
# to generate clarification requirements when the current request is too broad, ambiguous, or produces an unmanageable candidate pool
# handle Over-Generality --> Proactive Guidnace requirement
# generates a clarifying question in two distinct situations that orchestration_service.py needs to route through the same place:
#  1. Intent itself was unclear (intent_router.py returned "unclear")
#  2. A pipeline got far enough to identify a *specific* ambiguity 

import json
import logging
 
logger = logging.getLogger(__name__)
 
GENERIC_PROMPT = (
    "Are you looking to buy something specific, or would you like help "
    "exploring some options?"
)
 
REFINEMENT_SCHEMA_HINT = """
Return JSON: {"prompt": str}
Write one short, natural clarifying question. Reference what the user
already said if there's relevant context -- don't ask a generic question
when you have specifics to narrow down instead. If this is a repeat
clarification (the user already answered once and it's still ambiguous),
narrow the question further rather than repeating the same one.
"""

class ClarificationService:
    def __init__(self, llm_client=None, prompt_template: str | None = None):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
 
    def _default_prompt(self) -> str:
        return (
            "You write a single, short clarifying question for a shopping "
            "assistant when the user's intent is unclear.\n\n" + REFINEMENT_SCHEMA_HINT
        )
 
    async def generate(
        self,
        message: str,
        context: dict,
        state: dict,
        clarification_prompt: str | None = None,
    ) -> dict:
        # if pipeline already produced a specific prompt
        if clarification_prompt:
            return self._result(clarification_prompt, source="pipeline")
 
        # intent-level ambiguity, no LLM available; fall back to the generic
        # framing question rather than failing the turn
        if self.llm_client is None:
            return self._result(GENERIC_PROMPT, source="fallback")
 
        prompt = await self._generate_contextual_prompt(message, context, state)
        return self._result(prompt, source="generated")
 
    async def _generate_contextual_prompt(self, message: str, context: dict, state: dict) -> str:
        hint = self._build_hint(context, state)
 
        try:
            raw = await self.llm_client.complete(
                system=self.prompt_template, user=f"{hint}User message: {message}"
            )
            return self._parse(raw)
        except Exception:
            logger.exception(
                "ClarificationService: LLM completion failed, falling back to generic prompt "
                "(message=%r)", message,
            )
            return GENERIC_PROMPT
 
    def _build_hint(self, context: dict, state: dict) -> str:
        parts = []
 
        summary = context.get("summary")
        if summary:
            parts.append(f"Prior context: {summary}")
 
        dialog_machine = (state or {}).get("dialog_machine") or {}
        consecutive = dialog_machine.get("consecutive_clarifications", 0)
        if consecutive >= 1:
            parts.append(
                f"This is clarification attempt #{consecutive + 1} for this request -- "
                "the user has already answered a clarifying question and it's still "
                "ambiguous. Ask something more specific than before, don't repeat the "
                "same question."
            )
 
        previous_intent = (state or {}).get("intent")
        if previous_intent and previous_intent != "unclear":
            parts.append(f"Previously classified intent: {previous_intent}")
 
        return ("\n".join(parts) + "\n") if parts else ""
 
    def _parse(self, raw: str) -> str:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            return data.get("prompt") or GENERIC_PROMPT
        except json.JSONDecodeError:
            return GENERIC_PROMPT
 
    def _result(self, prompt: str, source: str) -> dict:
        return {
            "status": "needs_clarification",
            "message": prompt,
            "source": source,
        }
 