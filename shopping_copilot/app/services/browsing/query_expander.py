
# to expand exploratory queries into related concepts that may improve discovery across product catalog
# deliberately lightweight (no LLM call by default) since it runs once per query and multi_query_generator.py handles the heavier semantic reformulation.

from dataclasses import dataclass, field

from .scenario_analyzer import ScenarioAnalysis

@dataclass
class ExpandedQuery:
    original: str
    expanded_terms: list[str] = field(default_factory=list)
    expanded_query_string: str = ""  # original + expansions, joined for keyword search

class QueryExpander:
    def __init__(self, synonym_lookup=None, max_expansions: int = 8):
        self.synonym_lookup = synonym_lookup
        self.max_expansions = max_expansions

    async def expand(
        self, query: str, scenario: ScenarioAnalysis | None = None
    ) -> ExpandedQuery:
        terms: list[str] = []

        if scenario:
            terms.extend(scenario.inferred_categories)
            terms.extend(scenario.inferred_interests)

        if self.synonym_lookup:
            for word in self._significant_words(query):
                synonyms = await self._safe_lookup(word)
                terms.extend(synonyms)

        deduped = self._dedupe_preserve_order(terms)[: self.max_expansions]

        expanded_string = query
        if deduped:
            expanded_string = f"{query} {' '.join(deduped)}"

        return ExpandedQuery(
            original=query,
            expanded_terms=deduped,
            expanded_query_string=expanded_string,
        )

    def _significant_words(self, query: str) -> list[str]:
        stopwords = {"a", "an", "the", "for", "with", "and", "or", "my", "of", "to"}
        return [w for w in query.lower().split() if w not in stopwords and len(w) > 2]

    async def _safe_lookup(self, word: str) -> list[str]:
        try:
            result = self.synonym_lookup.lookup(word)
            if hasattr(result, "__await__"):
                result = await result
            return result or []
        except Exception:
            return []

    def _dedupe_preserve_order(self, terms: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for t in terms:
            key = t.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(t)
        return out