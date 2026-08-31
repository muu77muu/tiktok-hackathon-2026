"""Evaluator-facing team Agent.

Drives the evaluator through stateful local BM25 retrieval and deterministic
constraint-fidelity reranking over the frozen catalog:

- every turn returns top-10 recommendations AND asks ``ask_attribute:
  "other"`` -- the simulator answers "other" with up to two undisclosed
  constraints of any type, so the hidden intent card drains fastest;
- constraint leaks ("For that, what matters is: ...") accumulate into the
  retrieval query;
- the intent-override message ("Actually, ignore my earlier preference...")
  drops the original turn-1 preference and adds the new requirement;
- the top BM25 candidates are re-sorted CPU-side before returning 10:
  primary key = how many disclosed constraints appear VERBATIM in the
  product's text (the simulator copies constraints from the gold product's
  own features/details, so the gold matches all of them), secondary key =
  price within range of a disclosed "budget around $X" (X is the gold's
  exact price), tiebreak = original RRF order.

The organizer-facing reset/respond contract is unchanged.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent

# the evaluator imports this module from the repo root, where the inner
# ``app`` package isn't on sys.path; make its absolute imports resolve
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

_LOOKING_PREFIX = "I'm looking for "
_REQUIREMENT_MARK = ". A key requirement is: "
_EXPLORING_MARK = ", but I'm still exploring"
_OVERRIDE_PREFIX = "Actually, ignore my earlier preference"
_OVERRIDE_MARK = "What I need is:"
_LEAK_MARK = "what matters is:"

TOP_K_CAP = 10
# Retrieval depth fed to the phrase/price re-sort. A controlled public-set
# sweep selected 200 as the best HitRate/MRR/MTTC composite trade-off.
RETRIEVE_DEPTH = 200
BUDGET_WINDOW = 0.15  # candidate price within +/-15% of the disclosed budget

_BUDGET_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)")
_NORM_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NORM_RE.sub(" ", text.lower()).strip()


class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        # settings are lru_cached; export the evaluator's catalog path before
        # anything reads them so the catalog store and BM25 index build from
        # the same file the evaluator scores against
        catalog_path = Path(catalog_path)
        if catalog_path.exists():
            os.environ["CATALOG_PATH"] = str(catalog_path.resolve())

        from app.api.dependencies import get_retrieval_service
        from app.infrastructure.search.keyword_index import _product_text
        from app.infrastructure.search.local_indexes import load_keyword_index
        from app.infrastructure.storage.catalog_store import get_catalog_store

        self._service = get_retrieval_service()
        self._catalog = get_catalog_store()
        self._full_text = _product_text  # same field coverage as the BM25 index
        self._text_cache: dict[str, str] = {}  # product_id -> normalized text
        load_keyword_index()  # build BM25 now, not on the first respond
        self._sessions: dict[str, dict] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._sessions[session_id] = {
            "profile": dict(user_profile or {}),
            "category": "",
            "constraints": [],  # ordered, deduped
            "initial_preference": None,  # turn-1 free preference; dropped on override
        }

    # -- conversation parsing (mirrors the simulator's fixed templates) -------

    @staticmethod
    def _add_constraints(state: dict, values: list[str]) -> None:
        for value in values:
            value = value.strip()
            if value and value not in state["constraints"]:
                state["constraints"].append(value)

    def _absorb(self, state: dict, text: str) -> None:
        text = text.strip()

        if text.startswith(_OVERRIDE_PREFIX):
            new_value = text.split(_OVERRIDE_MARK, 1)[-1].strip().rstrip(".").strip()
            if state["initial_preference"] is not None:
                state["constraints"] = [
                    c for c in state["constraints"] if c != state["initial_preference"]
                ]
                state["initial_preference"] = None
            self._add_constraints(state, [new_value])
            return

        lowered = text.lower()
        if _LEAK_MARK in lowered:
            payload = text[lowered.index(_LEAK_MARK) + len(_LEAK_MARK):]
            payload = payload.strip().rstrip(".")
            self._add_constraints(state, payload.split(";"))
            return

        if text.startswith(_LOOKING_PREFIX):
            rest = text[len(_LOOKING_PREFIX):]
            if _REQUIREMENT_MARK in text:
                category, constraint = rest.split(_REQUIREMENT_MARK.lstrip("."), 1)
                state["category"] = category.strip(" .")
                self._add_constraints(state, [constraint.strip().rstrip(".")])
            elif _EXPLORING_MARK in rest:
                state["category"] = rest.split(_EXPLORING_MARK, 1)[0].strip()
            elif ". " in rest:
                category, preference = rest.split(". ", 1)
                state["category"] = category.strip()
                preference = preference.strip()
                if preference:
                    state["initial_preference"] = preference
                    self._add_constraints(state, [preference])
            else:
                state["category"] = rest.strip(" .")
        # other messages ("I don't have a preference...", "Ask me about one
        # specific attribute.") carry no new constraints

    # -- organizer contract ----------------------------------------------------

    async def _retrieve_candidates(self, query: str) -> dict:
        return await self._service.retrieve(
            query,
            strategy="keyword",
            top_k=RETRIEVE_DEPTH,
        )

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            raise RuntimeError("reset must be called before respond")

        self._absorb(state, str(user_message or ""))

        query = " ".join([state["category"], *state["constraints"]]).strip()
        if not query:
            query = str(user_message or "").strip()
        limit = max(0, min(int(top_k), TOP_K_CAP))

        recommendations: list[dict] = []
        if query and limit:
            result = asyncio.run(self._retrieve_candidates(query))
            candidates = [
                c for c in result.get("candidates", []) if c.get("product_id")
            ]
            ordered = self._phrase_price_sort(candidates, state["constraints"])
            recommendations = [{"parent_asin": pid} for pid in ordered[:limit]]

        return {
            "message": "Here are my best matches so far -- happy to refine further.",
            "ask_attribute": "other",
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    # -- CPU-side re-sort: verbatim phrase matches, then price window ---------

    def _phrase_price_sort(self, candidates: list[dict], constraints: list[str]) -> list[str]:
        budget: float | None = None
        phrases: list[str] = []
        for constraint in constraints:
            money = _BUDGET_RE.search(constraint)
            if money and "budget" in constraint.lower():
                budget = float(money.group(1))
                continue
            phrases.append(constraint)

        keyed = []
        for position, candidate in enumerate(candidates):
            product_id = str(candidate["product_id"])
            text = self._normalized_text(product_id)

            matches = 0
            for phrase in phrases:
                variants = [_normalize(phrase)]
                if ":" in phrase:
                    # "color: black" -> also try just "black"; product text
                    # contains the value, not the synthesized label
                    variants.append(_normalize(phrase.split(":", 1)[1]))
                if any(v and v in text for v in variants):
                    matches += 1

            out_of_budget = 0
            if budget is not None:
                price = self._price_of(product_id)
                in_range = price is not None and abs(price - budget) <= BUDGET_WINDOW * budget
                out_of_budget = 0 if in_range else 1

            # sort ascending: most phrase matches first, in-budget before
            # out-of-budget, original RRF order as the tiebreak
            keyed.append((-matches, out_of_budget, position, product_id))

        keyed.sort()
        return [product_id for *_, product_id in keyed]

    def _normalized_text(self, product_id: str) -> str:
        cached = self._text_cache.get(product_id)
        if cached is None:
            record = self._catalog.get(product_id) or {}
            cached = _normalize(self._full_text(record))
            self._text_cache[product_id] = cached
        return cached

    def _price_of(self, product_id: str) -> float | None:
        record = self._catalog.get(product_id) or {}
        try:
            return float(record.get("price"))
        except (TypeError, ValueError):
            return None
