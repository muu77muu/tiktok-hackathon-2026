class BuyingPipeline:
    def __init__(
        self,
        constraint_extractor=None,
        constraint_validator=None,
        filter_builder=None,
        strategy=None,
    ):
        self.constraint_extractor = constraint_extractor
        self.constraint_validator = constraint_validator
        self.filter_builder = filter_builder
        self.strategy = strategy

    async def run(self, query: str, context: dict | None = None) -> dict:
        context = context or {}
        
        return {
            "intent": "buying",
            "query": query,
            "context": context,
            "status": "pipeline_initialized",
        }