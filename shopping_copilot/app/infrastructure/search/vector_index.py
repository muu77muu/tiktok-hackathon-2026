
# In-memory dense vector index over the frozen catalog.
# VectorRetriever calls embedder.embed(query) and only ever calls this index via search(vector=..., filters=..., top_k=...), which is also the direct entry point browsing's HyDE flow uses through `search_by_vector`.

# no external vector DB; a normalized float32 numpy matrix + dot product is fast enough for 50k products in-memory

import json
import numpy as np

from .filtering import record_matches, to_metadata

DEFAULT_TOP_K = 50

# what gets embeded for each product
def _product_text(record: dict) -> str:
    parts = [record.get("title") or ""]
    categories = record.get("categories") or []
    if categories:
        parts.append(" ".join(categories))
    return " ".join(str(p) for p in parts).strip()

def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms

class VectorIndex:
    def __init__(self):
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None  # (n_docs, dim), L2-normalized rows
        self._records: dict[str, dict] = {}

    @classmethod
    def build_from_jsonl(
        cls,
        path: str,
        embed_fn,
        id_field: str = "parent_asin",
        batch_size: int = 64,
    ) -> "VectorIndex":
        """embed_fn: list[str] -> np.ndarray, e.g. embedder.embed_texts."""
        ids: list[str] = []
        texts: list[str] = []
        records: dict[str, dict] = {}

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                product_id = record.get(id_field)
                if not product_id:
                    continue
                ids.append(product_id)
                texts.append(_product_text(record))
                records[product_id] = record

        vectors: list[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            vectors.append(np.asarray(embed_fn(batch), dtype=np.float32))

        matrix = np.vstack(vectors) if vectors else np.zeros((0, 0), dtype=np.float32)

        idx = cls()
        idx.build(ids, matrix, records=records)
        return idx

    def build(self, product_ids: list[str], vectors: np.ndarray, records: dict[str, dict] | None = None) -> None:
        self._ids = list(product_ids)
        self._matrix = _normalize(np.asarray(vectors, dtype=np.float32))
        self._records = records or {}

    def search(self, vector, filters: dict | None = None, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """Matches VectorRetriever's call: vector_index.search(vector=..., filters=..., top_k=...)."""
        if self._matrix is None or len(self._ids) == 0:
            return []

        q = _normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        sims = self._matrix @ q  # cosine similarity, both sides normalized

        results = []
        for i, product_id in enumerate(self._ids):
            record = self._records.get(product_id, {})
            if not record_matches(record, filters):
                continue
            results.append({
                "product_id": product_id,
                "score": float(sims[i]),
                "metadata": to_metadata(record),
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def save(self, path: str) -> None:
        np.savez_compressed(
            path,
            ids=np.array(self._ids, dtype=object),
            matrix=self._matrix,
            records=np.array(json.dumps(self._records)),
        )

    @classmethod
    def load(cls, path: str) -> "VectorIndex":
        data = np.load(path, allow_pickle=True)
        idx = cls()
        idx._ids = list(data["ids"])
        idx._matrix = data["matrix"]
        idx._records = json.loads(str(data["records"]))
        return idx

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def dim(self) -> int:
        return 0 if self._matrix is None or self._matrix.size == 0 else self._matrix.shape[1]

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    _cache: dict[str, np.ndarray] = {}

    def fake_embed_fn(texts: list[str]) -> np.ndarray:
        out = []
        for t in texts:
            if t not in _cache:
                _cache[t] = rng.normal(size=32).astype(np.float32)
            out.append(_cache[t])
        return np.vstack(out)

    idx = VectorIndex.build_from_jsonl("catalog.jsonl", embed_fn=fake_embed_fn)
    print(f"indexed {idx.size} products, dim={idx.dim}")

    query_vec = fake_embed_fn(["mens hoodie"])[0]
    print(idx.search(query_vec, top_k=3))
    print(idx.search(query_vec, filters={"must": [{"field": "category", "value": "Men"}]}, top_k=3))

    idx.save("vector_index.npz")
    reloaded = VectorIndex.load("vector_index.npz")
    print("reloaded size:", reloaded.size, "match:", reloaded.search(query_vec, top_k=3) == idx.search(query_vec, top_k=3))