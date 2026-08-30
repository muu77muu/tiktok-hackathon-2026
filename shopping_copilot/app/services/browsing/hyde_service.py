
# to provide HyDE (Hypothetical Document Embedding) support for highly semantic / abstract browsing queries
# Product listings and shopping queries live in different linguistic registers 
# "something to keep my dad busy on weekends" vs. "12-piece stainless fishing tackle set, adjustable drag..."

from dataclasses import dataclass

from .scenario_analyzer import ScenarioAnalysis

HYDE_SCHEMA_HINT = """
Write a short, realistic product listing (title + 2-3 sentence description)
for the single product that best matches what the user is looking for.
Write it the way an actual e-commerce listing would read -- concrete
product name, key features, no meta-commentary. Do not return JSON, just
the listing text.
"""

@dataclass
class HydeDocument:
    query: str
    hypothetical_listing: str
    embedding: list[float] | None = None

class HydeService:
    def __init__(self, llm_client=None, embedder=None, prompt_template: str | None = None):
        self.llm_client = llm_client
        self.embedder = embedder
        self.prompt_template = prompt_template or self._default_prompt()

    def _default_prompt(self) -> str:
        return (
            "You write realistic hypothetical product listings to help a "
            "retrieval system understand shopping intent.\n\n" + HYDE_SCHEMA_HINT
        )

    async def generate(
        self, query: str, scenario: ScenarioAnalysis | None = None
    ) -> HydeDocument:
        scenario_hint = ""
        if scenario and scenario.scenario_summary:
            scenario_hint = f"Context: {scenario.scenario_summary}\n"

        listing = await self.llm_client.complete(
            system=self.prompt_template,
            user=f"{scenario_hint}User is looking for: {query}",
        )
        listing = listing.strip()

        embedding = None
        if self.embedder is not None:
            embedding = await self._safe_embed(listing)

        return HydeDocument(query=query, hypothetical_listing=listing, embedding=embedding)

    async def _safe_embed(self, text: str) -> list[float] | None:
        try:
            result = self.embedder.embed(text)
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception:
            return None