
# to analyse an exploratory shopping request and identify the user's scenario, goals, activities, preferences, and product needs

class ScenarioAnalyzer:
    async def analyze(
        self,
        query: str,
        context: dict | None = None,
    ) -> dict:
        context = context or {}

        return {
            "scenario": None,
            "goal": None,
            "activities": [],
            "preferences": [],
            "implicit_needs": [],
            "entities": [],
            "category_hints": [],
            "raw_query": query,
        }