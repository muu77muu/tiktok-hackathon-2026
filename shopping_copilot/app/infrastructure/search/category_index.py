
# In-memory category index over the frozen catalog: any-level term lookup
# eg. "Women" matches every product with "Women" anywhere in its category chain (plus the full hierarchical tree)
# CategoryRetriever assigns its own flat default score. Ties are broken by rating_number as a reasonable proxy for which matches are worth showing first within top_k.

import json
from collections import defaultdict

from .filtering import record_matches, to_metadata

DEFAULT_TOP_K = 30

# normalise categories field into clean list[str] chain
def _parse_categories(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(c).strip() for c in parsed if str(c).strip()]
        except (json.JSONDecodeError, ValueError):
            pass
    return []


class CategoryIndex:
    def __init__(self):
        self._by_term: dict[str, set[str]] = defaultdict(set)  # casefolded term -> product ids
        self._chains: dict[str, list[str]] = {}
        self._records: dict[str, dict] = {}

    @classmethod
    def build_from_jsonl(cls, path: str, id_field: str = "parent_asin") -> "CategoryIndex":
        idx = cls()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                product_id = record.get(id_field)
                if not product_id:
                    continue
                idx.add(product_id, record)
        return idx

    def add(self, product_id: str, record: dict) -> None:
        chain = _parse_categories(record.get("categories"))
        if not chain:
            return
        self._records[product_id] = record
        self._chains[product_id] = chain
        for term in chain:
            self._by_term[term.casefold()].add(product_id)

    def search(self, category: str | None, filters: dict | None = None, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """Matches CategoryRetriever's call: category_index.search(category=..., filters=..., top_k=...)."""
        if not category:
            return []

        ids = self._by_term.get(category.casefold(), set())

        results = []
        for product_id in ids:
            record = self._records.get(product_id, {})
            if not record_matches(record, filters):
                continue
            results.append({
                "product_id": product_id,
                "metadata": to_metadata(record),
            })

        # No inherent relevance score for a category match; break ties by rating_number so higher-signal products surface first within top_k.
        results.sort(key=lambda r: r["metadata"].get("rating_number") or 0, reverse=True)
        return results[:top_k]

    def get_by_term(self, term: str) -> set[str]:
        return set(self._by_term.get(term.casefold(), set()))

    def filter(self, candidate_ids, term: str) -> set[str]:
        return set(candidate_ids) & self.get_by_term(term)

    def chain_for(self, product_id: str) -> list[str]:
        return list(self._chains.get(product_id, []))

    def all_terms(self) -> list[str]:
        return sorted(self._by_term.keys())

    def as_tree(self) -> list[dict]:
        tree: dict = {}
        for chain in self._chains.values():
            level = tree
            for cat in chain:
                level = level.setdefault(cat, {})

        def to_list(node: dict) -> list[dict]:
            return [{"name": name, "children": to_list(children)} for name, children in node.items()]

        return to_list(tree)

if __name__ == "__main__":
    idx = CategoryIndex.build_from_jsonl("catalog.jsonl")
    print(f"indexed {len(idx._chains)} products, {len(idx.all_terms())} distinct terms")
    print(idx.search("Women", top_k=3))
    print(idx.search("Women", filters={"must": [{"field": "price", "op": "lte", "value": 20}]}, top_k=3))