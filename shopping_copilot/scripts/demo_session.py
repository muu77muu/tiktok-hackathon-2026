"""Print one reproducible multi-turn session for the submission demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluator.local_evaluator import (  # noqa: E402
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.agent import Agent  # noqa: E402


def product_line(parent_asin: str, products: dict[str, dict]) -> str:
    product = products.get(parent_asin, {})
    title = " ".join(str(product.get("title") or "Unknown product").split())
    if len(title) > 82:
        title = title[:79].rstrip() + "..."
    price = product.get("price")
    price_text = f" · ${price}" if price not in (None, "") else ""
    return f"{parent_asin} · {title}{price_text}"


def run_demo(sample_id: str, catalog_path: Path, dataset_path: Path) -> int:
    samples = {sample["sample_id"]: sample for sample in load_jsonl(dataset_path)}
    if sample_id not in samples:
        available = ", ".join(list(samples)[:5])
        raise SystemExit(f"Unknown sample {sample_id!r}. Examples: {available}")

    sample = samples[sample_id]
    catalog_ids, categories, products = catalog_index(catalog_path)
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective_sample = {**sample, "intent_card": card, "behavior": behavior}

    print("Loading the local 50,000-product BM25 index...", flush=True)
    agent = Agent(catalog_path)
    session_id = f"demo_{sample_id}"
    agent.reset(session_id, sample.get("user_profile") or {})

    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(
        effective_sample,
        coarse_category(categories.get(target, [])),
        disclosed,
    )

    print("\nSHOPPING COPILOT — REPRODUCIBLE SESSION")
    print(f"Sample: {sample_id} · Scenario: {sample['scenario_type']}")
    print("The target remains hidden until a valid conversion.\n")

    for turn in range(1, MAX_TURNS + 1):
        print(f"TURN {turn}")
        print(f"Customer: {user_message}")

        response = agent.respond(session_id, user_message, turn, TOP_K)
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        state = agent._sessions[session_id]
        active = [state.get("category", ""), *state.get("constraints", [])]
        active = [value for value in active if value]

        print(f"Agent: {response['message']}")
        print(f"Asks: {response.get('ask_attribute')}")
        print("Active state: " + (" | ".join(active) if active else "(empty)"))
        print("Top products:")
        for rank, parent_asin in enumerate(ranked[:3], start=1):
            print(f"  {rank}. {product_line(parent_asin, products)}")

        if override_applied and target in ranked:
            rank = ranked.index(target) + 1
            print(f"\nCONVERTED on turn {turn} at rank {rank}")
            print("Target: " + product_line(target, products))
            print("Token usage: 0 prompt + 0 completion")
            return 0

        print()
        if turn == MAX_TURNS:
            break

        override = effective_sample.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(override.get("message"))
        else:
            user_message, boundary_used = customer_reply(
                effective_sample,
                response.get("ask_attribute"),
                disclosed,
                boundary_used,
            )

    print("NO CONVERSION within ten turns")
    print("Target: " + product_line(target, products))
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-id", default="public_0003")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=REPO_ROOT / "starter" / "catalog.jsonl",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "data" / "public_set.jsonl",
    )
    args = parser.parse_args()
    raise SystemExit(run_demo(args.sample_id, args.catalog, args.dataset))


if __name__ == "__main__":
    main()
