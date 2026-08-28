
# to manage retrieved candidate pool (incl. deduplication, truncation, and pool-size assessment)

class CandidateManager:
    def deduplicate(
        self,
        candidates: list[dict],
    ) -> list[dict]:

        return candidates

    def truncate(
        self,
        candidates: list[dict],
        limit: int,
    ) -> list[dict]:

        return candidates[:limit]

    # Over-Generality requirement
    def assess(
        self,
        candidates: list[dict],
    ) -> dict:

        return {
            "count": len(candidates),
            "is_empty": not candidates,
            "is_over_general": False,
            "is_sufficient": bool(candidates),
        }