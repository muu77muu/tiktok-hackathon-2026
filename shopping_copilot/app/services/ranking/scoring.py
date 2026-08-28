
# to calculate deterministic candidate relevance scores from retrieval and product-level signals

class CandidateScorer:
    def score(
        self,
        query: str,
        candidate: dict,
        context: dict | None = None,
    ) -> float:
        
        return 0.0

    def score_candidates(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
    ) -> list[dict]:

        return [
            {
                **candidate,
                "score": self.score(
                    query,
                    candidate,
                    context,
                ),
            }
            for candidate in candidates
        ]