from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class OfficialAgentAdapterTest(unittest.TestCase):
    def test_official_import_calls_team_agent_and_returns_contract_shape(self) -> None:
        from starter.agent import Agent

        self.assertEqual(Agent.__module__, "shopping_copilot.agent")

        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            products = [
                {
                    "parent_asin": "A",
                    "title": "Blue cotton running shoe",
                    "features": ["lightweight", "comfortable"],
                    "details": {"Department": "Womens"},
                    "description": ["A blue shoe for running"],
                    "categories": ["Clothing, Shoes & Jewelry", "Women", "Shoes"],
                    "store": "Example",
                    "average_rating": 4.5,
                    "rating_number": 100,
                    "price": 49.0,
                },
                {
                    "parent_asin": "B",
                    "title": "Black leather belt",
                    "features": ["formal"],
                    "details": {"Department": "Mens"},
                    "description": ["A leather dress belt"],
                    "categories": ["Clothing, Shoes & Jewelry", "Men", "Belts"],
                    "store": "Example",
                    "average_rating": 4.0,
                    "rating_number": 20,
                    "price": 35.0,
                },
            ]
            catalog_path.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )

            agent = Agent(catalog_path)
            profile = {
                "purchase_frequency": "occasional",
                "average_prior_rating": 4.2,
                "rating_style": "usually positive",
                "preference_tags": ["comfort"],
                "summary": "Prior purchases emphasize comfort.",
            }
            agent.reset("session-1", profile)
            response = agent.respond(
                "session-1",
                "I need comfortable blue running shoes",
                turn=1,
                top_k=10,
            )

        self.assertEqual(response["message"].__class__, str)
        self.assertIn(response["ask_attribute"], {None, "category", "material", "color", "size", "style", "brand", "budget", "feature", "use_case", "other"})
        self.assertLessEqual(len(response["recommendations"]), 10)
        self.assertEqual(response["recommendations"][0]["parent_asin"], "A")
        self.assertEqual(response["usage"], {"prompt_tokens": 0, "completion_tokens": 0})


if __name__ == "__main__":
    unittest.main()
