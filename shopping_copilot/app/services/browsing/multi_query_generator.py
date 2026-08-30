
# to generate multiple complementary queries for exploratory retrieval
# standard "multi-query retrieval" pattern: a single query catches one facet of intent, several catch more.

from dataclasses import dataclass, field

from .scenario_analyzer import ScenarioAnalysis

GENERATION_SCHEMA_HINT = """
Return JSON: {"queries": [str, str, ...]}
Generate 3-5 distinct search queries. Vary the angle each time (literal
rewording, category-focused, use-case-focused, attribute-focused). Do not
just repeat the original query with minor word swaps.
"""

@dataclass
class MultiQueryResult:
    original: str
    queries: list[str] = field(default_factory=list)  # includes original as queries[0]

class MultiQueryGenerator:
    def __init__(self, llm_client=None, prompt_template: str | None = None, max_queries: int = 5):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
        self.max_queries = max_queries

    def _default_prompt(self) -> str:
        return (
            "You generate diverse search query reformulations for product "
            "retrieval. Each query should target a different facet of what "
            "the user might mean, so a search system can retrieve a wider, "
            "more relevant candidate set than a single query would.\n\n"
            + GENERATION_SCHEMA_HINT
        )

    async def generate(
        self, query: str, scenario: ScenarioAnalysis | None = None
    ) -> MultiQueryResult:
        scenario_hint = ""
        if scenario and scenario.scenario_summary:
            scenario_hint = f"Scenario context: {scenario.scenario_summary}\n"

        raw = await self.llm_client.complete(
            system=self.prompt_template,
            user=f"{scenario_hint}Original query: {query}",
        )
        generated = self._parse(raw)

        queries = [query] + [q for q in generated if q.strip().lower() != query.strip().lower()]
        queries = self._dedupe(queries)[: self.max_queries]

        return MultiQueryResult(original=query, queries=queries)

    def _parse(self, raw: str) -> list[str]:
        import json

        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            return data.get("queries", []) or []
        except json.JSONDecodeError:
            return []

    def _dedupe(self, queries: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            key = q.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(q)
        return out