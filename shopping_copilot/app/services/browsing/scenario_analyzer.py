
# to analyse an exploratory shopping request and identify the user's scenario, goals, activities, preferences, and product needs

import json
from dataclasses import dataclass, field

@dataclass
class ScenarioAnalysis:
    scenario_summary: str = ""         
    occasion: str | None = None         # "gift", "self-purchase", "replacement", "research"
    audience: str | None = None         # for who?
    inferred_categories: list[str] = field(default_factory=list)
    inferred_interests: list[str] = field(default_factory=list)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None
    confidence: float = 0.0
    raw_query: str = ""

ANALYSIS_SCHEMA_HINT = """
Return JSON:
{
  "scenario_summary": str,
  "occasion": str | null,
  "audience": str | null,
  "inferred_categories": [str],
  "inferred_interests": [str],
  "is_ambiguous": bool,
  "ambiguity_reason": str | null,
  "confidence": number  // 0.0-1.0
}
"""

class ScenarioAnalyzer:
    def __init__(self, llm_client=None, prompt_template: str | None = None):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()

    def _default_prompt(self) -> str:
        return (
            "You analyze open-ended shopping queries to understand the "
            "underlying scenario: who it's for, why they're buying, and "
            "what product categories or interests are implied. Flag "
            "is_ambiguous=true only if the query is genuinely too vague to "
            "search well (e.g. 'find me something nice'), not just broad.\n\n"
            + ANALYSIS_SCHEMA_HINT
        )

    async def analyze(self, query: str, context: dict | None = None) -> ScenarioAnalysis:
        context = context or {}
        history_hint = self._history_hint(context)

        raw = await self.llm_client.complete(
            system=self.prompt_template,
            user=f"{history_hint}Query: {query}",
        )
        parsed = self._parse(raw)
        return self._to_analysis(parsed, raw_query=query)

    def _history_hint(self, context: dict) -> str:
        prior_scenario = context.get("prior_scenario")
        if prior_scenario:
            return f"Prior scenario in this conversation: {prior_scenario}\n"
        return ""

    def _parse(self, raw: str) -> dict:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}

    def _to_analysis(self, parsed: dict, raw_query: str) -> ScenarioAnalysis:
        return ScenarioAnalysis(
            scenario_summary=parsed.get("scenario_summary", ""),
            occasion=parsed.get("occasion"),
            audience=parsed.get("audience"),
            inferred_categories=parsed.get("inferred_categories", []) or [],
            inferred_interests=parsed.get("inferred_interests", []) or [],
            is_ambiguous=bool(parsed.get("is_ambiguous", False)),
            ambiguity_reason=parsed.get("ambiguity_reason"),
            confidence=parsed.get("confidence", 0.0) or 0.0,
            raw_query=raw_query,
        )