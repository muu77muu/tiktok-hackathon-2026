
# to generate clarification requirements when the current request is too broad, ambiguous, or produces an unmanageable candidate pool
# handle Over-Generality --> Proactive Guidnace requirement
# generates a clarifying question in two distinct situations that orchestration_service.py needs to route through the same place:
#  1. Intent itself was unclear (intent_router.py returned "unclear")
#  2. A pipeline got far enough to identify a *specific* ambiguity 

GENERIC_PROMPT = (
    "Are you looking to buy something specific, or would you like help "
    "exploring some options?"
)

REFINEMENT_SCHEMA_HINT = """
Return JSON: {"prompt": str}
Write one short, natural clarifying question. Reference what the user
already said if there's relevant context -- don't ask a generic question
when you have specifics to narrow down instead.
"""

class ClarificationService:
    def __init__(self, llm_client=None, prompt_template: str | None = None):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()

    def _default_prompt(self) -> str:
        return ("You write a single, short clarifying question for a shopping assistant when the user's intent is unclear.\n\n" + REFINEMENT_SCHEMA_HINT)

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

        # intent-level ambiguity, no LLM available; fall back to the generic framing question rather than failing the turn
        if self.llm_client is None:
            return self._result(GENERIC_PROMPT, source="fallback")

        prompt = await self._generate_contextual_prompt(message, context)
        return self._result(prompt, source="generated")

    async def _generate_contextual_prompt(self, message: str, context: dict) -> str:
        summary = context.get("summary")
        hint = f"Prior context: {summary}\n" if summary else ""

        try:
            raw = await self.llm_client.complete(
                system=self.prompt_template, user=f"{hint}User message: {message}"
            )
            return self._parse(raw)
        except Exception:
            return GENERIC_PROMPT

    def _parse(self, raw: str) -> str:
        import json

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