from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOPPING_COPILOT = REPO_ROOT / "shopping_copilot"
if str(SHOPPING_COPILOT) not in sys.path:
    sys.path.insert(0, str(SHOPPING_COPILOT))

from app.services.retrieval.retrieval_service import RetrievalService
from shopping_copilot.agent import Agent, RETRIEVE_DEPTH


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(self, query, filters=None, top_k=50):
        self.calls.append({"query": query, "filters": filters, "top_k": top_k})
        return []


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def retrieve(self, query, strategy, top_k):
        self.calls.append({"query": query, "strategy": strategy, "top_k": top_k})
        return {"candidates": []}


class RetrievalPolicyTest(unittest.TestCase):
    def test_service_forwards_top_k_to_keyword_retriever(self) -> None:
        keyword = RecordingRetriever()
        service = RetrievalService(keyword_retriever=keyword)

        asyncio.run(service.retrieve("red hiking boots", strategy="keyword", top_k=200))

        self.assertEqual(keyword.calls, [{
            "query": "red hiking boots",
            "filters": {},
            "top_k": 200,
        }])

    def test_official_agent_uses_keyword_depth_200(self) -> None:
        agent = Agent.__new__(Agent)
        agent._service = RecordingService()

        asyncio.run(agent._retrieve_candidates("waterproof hiking boots"))

        self.assertEqual(RETRIEVE_DEPTH, 200)
        self.assertEqual(agent._service.calls, [{
            "query": "waterproof hiking boots",
            "strategy": "keyword",
            "top_k": 200,
        }])


if __name__ == "__main__":
    unittest.main()
