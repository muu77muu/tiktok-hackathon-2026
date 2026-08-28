
# to diversify ranked results to avoid excessive redundancy and improve discovery coverage

class ResultDiversifier:
    def diversify(
        self,
        candidates: list[dict],
        top_k: int = 10,
        strategy: str = "default",
    ) -> list[dict]:

        return candidates[:top_k]