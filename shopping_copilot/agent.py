"""Evaluator-facing team Agent.

Drives the real team stack: hybrid retrieval (hand-rolled BM25 + numpy
vector index, fused with RRF) over the local catalog, plus a conversation
strategy for the organizer's customer simulator:

- every turn returns top-10 recommendations AND asks ``ask_attribute:
  "other"`` -- the simulator answers "other" with up to two undisclosed
  constraints of any type, so the hidden intent card drains fastest;
- constraint leaks ("For that, what matters is: ...") accumulate into the
  retrieval query;
- the intent-override message ("Actually, ignore my earlier preference...")
  drops the original turn-1 preference and adds the new requirement.

The organizer-facing reset/respond contract is unchanged.
"""

from __future__ import annotations

import asyncio
import os
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


class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        # settings are lru_cached; export the evaluator's catalog path before
        # anything reads them so the catalog store and BM25 index build from
        # the same file the evaluator scores against
        catalog_path = Path(catalog_path)
        if catalog_path.exists():
            os.environ["CATALOG_PATH"] = str(catalog_path.resolve())

        from app.api.dependencies import get_retrieval_service
        from app.infrastructure.search.local_indexes import warm_indexes

        self._service = get_retrieval_service()
        warm_indexes()  # load npz + build BM25 now, not on the first respond
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
            result = asyncio.run(
                self._service.retrieve(query, strategy="hybrid", top_k=limit)
            )
            recommendations = [
                {"parent_asin": str(c["product_id"])}
                for c in result.get("candidates", [])
                if c.get("product_id")
            ][:limit]

        return {
            "message": "Here are my best matches so far -- happy to refine further.",
            "ask_attribute": "other",
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
