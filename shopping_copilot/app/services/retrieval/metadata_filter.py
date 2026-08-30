
# to apply deterministic catalog constraints to product candidates
# applies the filter dict shape produced by services/buying/filter_builder.py ({"must": [...], "should": [...], "must_not": [...]}) against retrieved candidates to act as a post-filter safety net
# - "must" clauses are hard requirements (candidate dropped if unmet)
# - "must_not" clauses exclude matching candidates
# - "should" clauses dont filter anything; they're recorded as a match count on the candidate for ranking to use as a boost signal

SUPPORTED_OPS = {"eq", "in", "range", "contains"}

class MetadataFilter:
    async def apply(self, candidates: list[dict], filters: dict | None) -> list[dict]:
        if not filters:
            return candidates

        must = filters.get("must", [])
        must_not = filters.get("must_not", [])
        should = filters.get("should", [])

        filtered = []
        for c in candidates:
            metadata = c.get("metadata", {})

            if must and not all(self._matches(metadata, clause) for clause in must):
                continue
            if must_not and any(self._matches(metadata, clause) for clause in must_not):
                continue

            should_matches = sum(1 for clause in should if self._matches(metadata, clause))
            if should:
                c = {**c, "should_match_count": should_matches, "should_match_ratio": should_matches / len(should)}

            filtered.append(c)

        return filtered

    def _matches(self, metadata: dict, clause: dict) -> bool:
        field = clause.get("field", "")
        op = clause.get("op", "eq")
        value = clause.get("value")

        actual = self._resolve_field(metadata, field)
        if actual is None:
            return False

        if op == "eq":
            return actual == value
        if op == "in":
            return actual in value if isinstance(value, (list, set, tuple)) else False
        if op == "range":
            return self._in_range(actual, value)
        if op == "contains":
            if isinstance(actual, (list, set, tuple)):
                return value in actual
            return str(value).lower() in str(actual).lower()

        return False

    # for dotted paths
    def _resolve_field(self, metadata: dict, field: str):
        parts = field.split(".")
        current = metadata
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _in_range(self, actual, range_value: dict) -> bool:
        if actual is None or not isinstance(range_value, dict):
            return False
        if "gte" in range_value and actual < range_value["gte"]:
            return False
        if "lte" in range_value and actual > range_value["lte"]:
            return False
        if "gt" in range_value and actual <= range_value["gt"]:
            return False
        if "lt" in range_value and actual >= range_value["lt"]:
            return False
        return True