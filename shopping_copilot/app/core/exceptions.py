

# raised by retrieval / pool_analyzer.py (via buying_strategy.py / browsing_strategy.py) when candidate pool to broad to rank meaningfully
# raised before ranking stage runs -> retrieval cutoff
class OverGeneralityDetected(Exception):
    def __init__(self, prompt: str, suggested_dims: list[str] | None = None, pool_size: int = 0):
        self.prompt = prompt
        self.suggested_dims = suggested_dims or []
        self.pool_size = pool_size
        super().__init__(prompt)
