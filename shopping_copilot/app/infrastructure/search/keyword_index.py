
# Pure-Python BM25 keyword index over the frozen catalog for light execution
# this returns raw dicts with product_id / score / metadata that KeywordRetriever._to_candidate then normalizes into a candidate.

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
 
from .filtering import record_matches, to_metadata
 
_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_TOP_K = 50
 
def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return _TOKEN_RE.findall(text.lower())
 
def _product_text(record: dict) -> str:
    parts = [record.get("title") or ""]
    parts.extend(record.get("features") or [])
    parts.extend(record.get("description") or [])
    return " ".join(str(p) for p in parts)
 
@dataclass
class KeywordIndex:
    k1: float = 1.5
    b: float = 0.75
 
    _postings: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(dict))  # term -> {product_id: tf}
    _doc_len: dict[str, int] = field(default_factory=dict)
    _records: dict[str, dict] = field(default_factory=dict)
    _avgdl: float = 0.0
    _n_docs: int = 0
 
    @classmethod
    def build_from_jsonl(cls, path: str, id_field: str = "parent_asin", k1: float = 1.5, b: float = 0.75) -> "KeywordIndex":
        idx = cls(k1=k1, b=b)
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
        idx._finalize()
        return idx
 
    def add(self, product_id: str, record: dict) -> None:
        self._records[product_id] = record
        tokens = tokenize(_product_text(record))
        self._doc_len[product_id] = len(tokens)
        tf: dict[str, int] = defaultdict(int)
        for tok in tokens:
            tf[tok] += 1
        for tok, count in tf.items():
            self._postings[tok][product_id] = count
 
    def _finalize(self) -> None:
        self._n_docs = len(self._doc_len)
        self._avgdl = (sum(self._doc_len.values()) / self._n_docs) if self._n_docs else 0.0

    def search(self, query: str, filters: dict | None = None, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """Matches KeywordRetriever's call: keyword_index.search(query=..., filters=..., top_k=...)."""
        if self._n_docs == 0:
            return []
 
        scores = self._bm25_scores(query)
 
        results = []
        for product_id, score in scores.items():
            record = self._records.get(product_id, {})
            if not record_matches(record, filters):
                continue
            results.append({
                "product_id": product_id,
                "score": score,
                "metadata": to_metadata(record),
            })
 
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]
 
    def _bm25_scores(self, query: str) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        for term in set(tokenize(query)):
            postings = self._postings.get(term)
            if not postings:
                continue
            idf = self._idf(term)
            if idf <= 0:
                continue
            for product_id, tf in postings.items():
                dl = self._doc_len.get(product_id, 0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1))
                scores[product_id] += idf * (tf * (self.k1 + 1)) / (denom or 1)
        return scores
 
    def _idf(self, term: str) -> float:
        df = len(self._postings.get(term, {}))
        if df == 0:
            return 0.0
        return math.log(1 + (self._n_docs - df + 0.5) / (df + 0.5))
 
    def get_product(self, product_id: str) -> dict | None:
        return self._records.get(product_id)
 
    @property
    def size(self) -> int:
        return self._n_docs
 
if __name__ == "__main__":
    idx = KeywordIndex.build_from_jsonl("catalog.jsonl")
    print(f"indexed {idx.size} products")
    print(idx.search("mens hoodie", top_k=3))
    print(idx.search("mens hoodie", filters={"must": [{"field": "category", "value": "Novelty"}]}, top_k=3))
 
