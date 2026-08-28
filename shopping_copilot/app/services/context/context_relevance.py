
# to determine which stored context is relevant to the current shopping request

class ContextRelevance:
    def select(
        self,
        query: str,
        context: dict,
    ) -> dict:

        return context