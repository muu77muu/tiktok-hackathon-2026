"""Full report over an evaluator results file.

The official evaluator prints only the summary block and writes per-session
detail to its --output JSON. This script joins that JSON with the gold set
to add the breakdowns the summary doesn't show: difficulty split, rank and
first-hit-turn histograms, and where the misses cluster.

Usage (from the repo root):
    shopping_copilot\\venv\\Scripts\\python shopping_copilot\\scripts\\eval_report.py results_phaseB.json
    ...\\python ...\\eval_report.py results.json --dataset data/public_set.jsonl
"""

import argparse
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="?", default="results.json",
                        help="evaluator --output file (default results.json)")
    parser.add_argument("--dataset", default=str(REPO_ROOT / "data" / "public_set.jsonl"))
    args = parser.parse_args()

    r = json.loads(Path(args.results).read_text(encoding="utf-8"))
    sessions = r["sessions"]
    gold = {}
    with open(args.dataset, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sample = json.loads(line)
                gold[sample["sample_id"]] = sample

    print("=== overall ===")
    for key in ("sample_count", "hit_rate_at_10", "mrr", "mttc",
                "efficiency", "recommended_technical_score"):
        print(f"  {key}: {r[key]}")
    print("  token usage:", r["reported_token_usage"])

    print("\n=== per scenario (hit@10 / mrr / mttc) ===")
    for name, m in r["scenario_metrics"].items():
        print(f"  {name:<16} n={m['sample_count']:<4} hit={m['hit_rate_at_10']:<9}"
              f" mrr={round(m['mrr'], 3):<7} mttc={round(m['mttc'], 2)}")

    print("\n=== per difficulty ===")
    by_diff: dict[str, list[dict]] = {}
    for s in sessions:
        by_diff.setdefault(gold[s["sample_id"]]["difficulty_bucket"], []).append(s)
    for diff in ("easy", "medium", "hard"):
        ss = by_diff.get(diff, [])
        if not ss:
            continue
        hit = sum(s["hit"] for s in ss) / len(ss)
        mrr = sum(s["reciprocal_rank"] for s in ss) / len(ss)
        print(f"  {diff:<7} n={len(ss):<4} hit={hit:.3f}  mrr={mrr:.3f}")

    print("\n=== rank of gold product when hit ===")
    ranks = Counter(s["best_rank"] for s in sessions if s["hit"])
    for rank in sorted(ranks):
        print(f"  rank {rank:>2}: {'#' * ranks[rank]} {ranks[rank]}")

    print("\n=== turn of first hit ===")
    turns = Counter(s["first_hit_turn"] for s in sessions if s["hit"])
    for turn in sorted(turns):
        print(f"  turn {turn:>2}: {'#' * turns[turn]} {turns[turn]}")

    misses = [s for s in sessions if not s["hit"]]
    print(f"\n=== misses: {len(misses)} of {len(sessions)} ===")
    cluster = Counter(
        (gold[s["sample_id"]]["scenario_type"], gold[s["sample_id"]]["difficulty_bucket"])
        for s in misses
    )
    for (scenario, diff), n in cluster.most_common():
        print(f"  {scenario:<16} {diff:<7} {n}")
    print("\nmissed sample_ids:", " ".join(sorted(s["sample_id"] for s in misses)))


if __name__ == "__main__":
    main()
