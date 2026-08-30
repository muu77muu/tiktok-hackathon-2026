
# to maintain transient context for the current shopping session
# Keeps the last N turns verbatim for the LLM to see directly, and rolls anything older into a compact running summary rather than letting context grow unbounded across a long conversation.

from dataclasses import dataclass, field

DEFAULT_WINDOW_SIZE = 6

SUMMARY_PROMPT = """
Summarize this shopping conversation excerpt in 2-3 sentences. Focus on
what the user is looking for, constraints they've stated, and anything
they've rejected or ruled out. Do not include pleasantries or filler.
"""

@dataclass
class ShortTermWindow:
    recent_turns: list[dict] = field(default_factory=list)
    rolling_summary: str | None = None
    last_pipeline_result: dict | None = None  # most recent buying/browsing PipelineResult

class ShortTermMemory:
    def __init__(self, llm_client=None, window_size: int = DEFAULT_WINDOW_SIZE):
        self.llm_client = llm_client
        self.window_size = window_size

    async def get_window(
        self, conversation_history: list[dict], prior_summary: str | None = None
    ) -> ShortTermWindow:
        conversation_history = conversation_history or []

        recent = conversation_history[-self.window_size:]
        overflow = conversation_history[: -self.window_size] if len(conversation_history) > self.window_size else []

        summary = prior_summary
        if overflow and self.llm_client is not None:
            summary = await self._summarize(overflow, prior_summary)

        last_result = self._extract_last_pipeline_result(conversation_history)

        return ShortTermWindow(
            recent_turns=recent,
            rolling_summary=summary,
            last_pipeline_result=last_result,
        )

    async def _summarize(self, overflow_turns: list[dict], prior_summary: str | None) -> str:
        transcript = self._format_turns(overflow_turns)
        prefix = f"Summary so far: {prior_summary}\n\n" if prior_summary else ""
        try:
            summary = await self.llm_client.complete(
                system=SUMMARY_PROMPT,
                user=f"{prefix}New turns to fold in:\n{transcript}",
            )
            return summary.strip()
        except Exception:
            # summarisation failing shouldnt break the pipeline; fall back to whatever summary we already had, even if stale.
            return prior_summary or ""

    def _format_turns(self, turns: list[dict]) -> str:
        lines = []
        for t in turns:
            role = t.get("role", "user")
            content = t.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    # goes through history for most recent turn carrying a pipeline result to be used as seed prior_constraint / prior_scenario
    def _extract_last_pipeline_result(self, conversation_history: list[dict]) -> dict | None:
        for turn in reversed(conversation_history):
            result = turn.get("pipeline_result")
            if result:
                return result
        return None