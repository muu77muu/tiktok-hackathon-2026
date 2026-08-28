
# to extract purchasing constraints from a user's shopping request

class ConstraintExtractor:
    async def extract(self, query: str, context: dict | None = None) -> dict:
        context = context or {}
        
        return {
            "category": None,
            "price": {
                "min": None,
                "max": None,
            },
            "brands": [],
            "attributes": {},
            "requirements": [],
            "preferences": [],
            "raw_query": query,
        }