
# to perform final semantic ranking using a LLM
# LLM-based reranking: the most expensive and most precise stage, run on a small shortlist (top ~10-20) after scoring + cross-encoder have already narrowed things down. 
# e.g. checking must-have constraints are actually satisfied, not just topically related, or whether a browsing candidate genuinely fits the inferred scenario.

from .scoring import ScoredCandidate

RANKING_SCHEMA_HINT = """
Return JSON: {"rankings": [{"product_id": str, "score": number, "rationale": str}, ...]}
score is 0.0-1.0. Rank ALL provided candidates, most relevant first. rationale
is one short phrase, not a sentence.
"""

DEFAULT_SHORTLIST_SIZE = 15

class LLMRanker:
    def __init__(self, llm_client=None, prompt_template: str | None = None, shortlist_size: int = DEFAULT_SHORTLIST_SIZE):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
        self.shortlist_size = shortlist_size

    def _default_prompt(self) -> str:
        return (
            "You are ranking shopping search results for relevance to the "
            "user's query and any stated constraints or scenario. Check "
            "that must-have requirements are actually satisfied, not just "
            "topically similar. Penalize near-duplicate items by ranking "
            "the best one high and the rest lower.\n\n" + RANKING_SCHEMA_HINT
        )

    async def rank(
        self, query: str, candidates: list[ScoredCandidate], context: dict | None = None
    ) -> list[ScoredCandidate]:
        if not candidates or self.llm_client is None:
            return candidates

        shortlist = candidates[: self.shortlist_size]
        remainder = candidates[self.shortlist_size:]

        prompt = self._build_prompt(query, shortlist, context or {})
        try:
            raw = await self.llm_client.complete(system=self.prompt_template, user=prompt)
            rankings = self._parse(raw)
        except Exception:
            # LLM ranking failing shouldnt drop results; fall back to cross-encoder/base order already on the shortlist.
            return candidates

        reranked = self._apply_rankings(shortlist, rankings)
        return reranked + remainder

    def _build_prompt(self, query: str, shortlist: list[ScoredCandidate], context: dict) -> str:
        lines = [f"Query: {query}"]

        constraints = context.get("prior_constraints") or context.get("active_constraints")
        if constraints:
            lines.append(f"Constraints/preferences: {constraints}")

        scenario = context.get("prior_scenario")
        if scenario:
            lines.append(f"Scenario: {getattr(scenario, 'scenario_summary', scenario)}")

        lines.append("\nCandidates:")
        for c in shortlist:
            metadata = c.candidate.get("metadata", {})
            lines.append(
                f"- product_id={c.product_id}, title={metadata.get('title', '')}, "
                f"price={metadata.get('price', '')}, brand={metadata.get('brand', '')}"
            )

        return "\n".join(lines)

    def _parse(self, raw: str) -> list[dict]:
        import json

        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            return data.get("rankings", []) or []
        except json.JSONDecodeError:
            return []

    def _apply_rankings(
        self, shortlist: list[ScoredCandidate], rankings: list[dict]
    ) -> list[ScoredCandidate]:
        if not rankings:
            return shortlist

        by_id = {c.product_id: c for c in shortlist}
        reranked = []
        seen = set()

        for r in rankings:
            pid = r.get("product_id")
            candidate = by_id.get(pid)
            if candidate is None:
                continue
            candidate.llm_score = r.get("score")
            candidate.llm_rationale = r.get("rationale")
            reranked.append(candidate)
            seen.add(pid)

        # any candidate the LLM omitted from its response keeps its existing order, appended after the ones it did rank
        leftover = [c for c in shortlist if c.product_id not in seen]
        return reranked + leftover