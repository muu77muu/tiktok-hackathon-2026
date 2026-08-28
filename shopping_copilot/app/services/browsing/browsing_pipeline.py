class BrowsingPipeline:
    def __init__(
        self,
        scenario_analyzer=None,
        query_expander=None,
        multi_query_generator=None,
        hyde_service=None,
        strategy=None,
    ):
        self.scenario_analyzer = scenario_analyzer
        self.query_expander = query_expander
        self.multi_query_generator = multi_query_generator
        self.hyde_service = hyde_service
        self.strategy = strategy

    async def run(self, query: str, context: dict | None = None) -> dict:
        context = context or {}

        return {
            "intent": "browsing",
            "query": query,
            "context": context,
            "status": "pipeline_initialized",
        }