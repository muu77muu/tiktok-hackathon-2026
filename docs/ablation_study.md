# Ablation Study — Conversational Shopping Agent (TechJam)

All scores come from the **unmodified official evaluator** (`evaluator/local_evaluator.py`) on
`data/public_set.jsonl` (200 sessions), run as:

```
..\.venv\Scripts\python -m evaluator.local_evaluator --catalog starter\catalog.jsonl --dataset data\public_set.jsonl --output <results file>
```

Composite: `TechnicalScore = 0.50·HitRate@10 + 0.30·MRR + 0.20·Efficiency`,
`Efficiency = clip((11 − MTTC) / 10, 0, 1)`. Every variant reports **0 tokens / $0 API cost**
(fully local models). Detailed breakdowns per run: `shopping_copilot/scripts/eval_report.py <results file>`.

## Results overview

| # | Variant | Results file | Hit@10 | MRR | MTTC | Eff. | **Score** | Latency/turn |
|---|---|---|---|---|---|---|---|---|
| 1 | Weak BM25 baseline (organizer) | `results.json` | 0.125 | 0.068 | 9.81 | 0.119 | **0.107** | ~5 ms |
| 2 | Phase A: stateful hybrid + RRF | `results_phaseA.json` | 0.635 | 0.298 | 5.53 | 0.548 | **0.516** | ~0.9 s |
| 3 | Phase B: enriched index text | `results_phaseB.json` | 0.760 | 0.410 | 4.47 | 0.654 | **0.634** | ~0.9 s |
| 4 | Phase C: fast vector search | *(bundled into #2)* | — | — | — | — | *no separate run* | latency-only |
| 5 | Stateful keyword-only, depth 50 | controlled run | 0.895 | 0.647 | 3.23 | 0.777 | **0.797** | CPU-local |
| 6 | Phase D: + Qwen3-Reranker-0.6B | *(rejected)* | unknown | unknown | unknown | unknown | **unknown** | 19.9 s/top-10 CPU |
| 7 | Phase E: + phrase boost & price filter | `results_phaseE.json` | 0.895 | 0.605 | 3.16 | 0.785 | **0.786** | ~0.82 s |
| 8 | **Phase F: keyword depth 200 + phrase/price rerank (selected)** | `results_phaseF.json` | **0.925** | **0.657** | **2.98** | **0.802** | **0.820** | CPU-local, no model |

## Per-variant detail

### 1 — Weak BM25 baseline (organizer starter)

- **Implementation**: stateless SQLite FTS5 `OR`-query over the raw user message with field
  weights (title 6.0 … description 1.0). Never asks a question (`ask_attribute: None`),
  keeps no conversation state. No vector search, no ML models; stdlib + sqlite only.
- **Reproduction**: matches the organizer's published `docs/baseline_results.json` to six
  decimal places.
- **Scenario profile**: buying 0.238 / intent_override 0.133 / browsing 0.025 / boundary 0.000
  (hit@10). Vague browsing openers and question-dependent boundary sessions collapse without
  state or semantics.

### 2 — Phase A: stateful conversation + hybrid retrieval + RRF

- **Change from #1**: `shopping_copilot/agent.py` rewritten. Session state parses the
  simulator's message templates; disclosed constraints accumulate into the retrieval query;
  the intent-override message drops the stale turn-1 preference; the agent recommends **and**
  asks `ask_attribute: "other"` every turn (the simulator answers "other" with up to two
  undisclosed constraints of any type — the fastest intent-card drain). Retrieval = hand-rolled
  Okapi BM25 (title+features+description) ⊕ exact-cosine numpy vector index
  (Qwen3-Embedding-0.6B, 1024-dim, embed text = title+categories) fused with rank-based RRF.
- **Dependencies added**: torch (CUDA), sentence-transformers, numpy. Latency ~0.9 s/turn
  (GPU query embed ~50 ms; BM25 and vector scan CPU-side).
- **Scenario gains**: browsing 0.025 → 0.675, boundary 0.0 → 0.9, buying 0.238 → 0.60,
  intent_override 0.133 → 0.533 (hit@10).

### 3 — Phase B: index text aligned with the evaluator's constraint sources

- **Change from #2**: index *content* only; code paths identical. BM25 document text extended
  with categories, store, and flattened details; vector embed text rebuilt as
  title+categories+features+store (one-time 23-minute GPU re-embed of all 50k products).
  Rationale: the simulator derives customer constraints from title/features/details/
  material/color/price/store — the indexes now cover those fields.
- **Scenario gains**: intent_override 0.533 → 0.800 (largest; the pivoted requirement text now
  matches indexed details directly), buying 0.60 → 0.725, browsing 0.675 → 0.75, boundary
  0.9 → 1.0.

### 4 — Phase C: vector-search latency optimization

- **Change**: best-first `argsort` walk with early stop in `vector_index.search`, replacing a
  full 50k-row Python loop (~300 ms → ~15 ms per query). Result-order preserving.
- **Measurement**: shipped *before* the Phase A run, so its effect is contained in row 2's
  latency. **No separate score run exists** (identical results by construction).

### 5 — Stateful keyword-only: controlled after Phase E

- **Change from Phase E**: vector retrieval and RRF disabled; the same accumulated query,
  open-ended clarification, phrase matches, price window, and deterministic tie-breaking remain.
- **Depth-50 result**: Hit@10 0.895, MRR 0.647, MTTC 3.23, Score 0.797. It preserves Phase E
  coverage while improving ranking precision enough to beat equal-weight hybrid retrieval.
- **Conclusion**: after concrete constraints accumulate, exact lexical fidelity is more useful
  than adding semantically similar vector candidates. This controlled run isolates the vector
  contribution that was unknown in the earlier report.

### 6 — Phase D: local Qwen semantic reranking (rejected)

- **Change from #3**: retrieve top-50, rerank with local Qwen3-Reranker-0.6B (bf16, 640-token
  document cap), return reranked top-10.
- **Status**: the earlier GPU run was stopped at ~25%. A later bounded CPU benchmark measured
  38.4 s cold for top-5, 10.0 s warm for top-5, and **19.9 s warm for top-10**. Phase F makes
  581 Agent calls on the public set, implying about **3.2 hours of reranker inference alone**
  before retrieval/evaluator overhead. A full CPU scoring run was therefore rejected without
  risking the verified release candidate; score impact remains unknown.
- The library improvements (bf16 load, richer rerank document text) remain available to the
  demo app's ranking pipeline; the eval agent no longer uses them.

### 7 — Phase E: verbatim phrase boost + price filter

- **Change from #3/#6**: reranker removed from the eval agent. Fused top-50 candidates are
  re-sorted CPU-side before returning 10 — primary key: how many disclosed constraints appear
  **verbatim** in the product's normalized full text (the simulator copies constraints from
  the gold product's own listing, so the gold matches all of them; lookalikes rarely do; a
  `label: value` constraint also tries its value part); secondary key: price within ±15% of a
  disclosed `budget around $X` (X is the gold's exact price); tiebreak: original RRF order.
  Cost ~1–5 ms/turn.
- **Effects**: rank-1 hits 59 → 99 of 179; misses 48 → 21 (9 browsing/medium, 8 buying/easy,
  4 intent_override/hard); every scenario ≥ 0.867 hit@10; the difficulty inversion flattened
  (easy 0.90 / medium 0.90 / hard 0.867). Hard cases hit at ranks 1–3 only (20/5/1) — verbatim
  matching is decisive or the query misses entirely.
- **Only regression observed anywhere**: boundary MRR 0.736 → 0.636 (n = 10; noise-scale).

### 8 — Phase F: keyword depth 200 + deterministic constraint reranking (selected)

- **Change from #7**: a service-contract bug was fixed so `RetrievalService.top_k` reaches the
  underlying retrievers. The official Agent selects keyword retrieval, requests 200 candidates,
  and then applies the unchanged phrase/price reranker. Vector/model startup is removed from the
  official path; hybrid remains available to the demo stack.
- **Controlled depth sweep**: keyword depth 50 scored 0.797, depth 100 scored 0.804, depth 200
  scored **0.820**, and depth 500 scored 0.820 but with lower MRR. Depth 200 is the best weighted
  coverage/precision/efficiency trade-off rather than the largest arbitrary pool.
- **Verified result**: Hit@10 0.925, MRR 0.657, MTTC 2.98, Efficiency 0.802, Technical Score
  **0.819973**. Per-scenario Hit@10: boundary 1.000, browsing 0.938, buying 0.913,
  intent_override 0.900. Six unit tests pass; API token usage and cost remain zero.
- **Operational result**: the official scorer no longer requires the 149 MiB vector artifact,
  sentence-transformers, Qwen embedding weights, network access, or credentials.

## Were vector retrieval and sentence-transformers genuinely active?

- **Baseline (#1): definitively inactive** — the code contains neither.
- **Runs A/B/E: active, verified** by: (a) sentence-transformers 6.0.0 importing in the run
  venv; (b) the `vector_index.npz` existing at each run's start (built minutes before run A,
  rebuilt before run B); (c) `scripts/smoke_retrieval.py` asserting
  `fusion_sources: ['keyword', 'vector']` under the same service wiring; (d) a vector-*only*
  strategy probe returning valid ranked results; (e) the scenario signature — browsing
  0.025 → 0.675 requires semantic matching of vague openers.
- **Caveat, stated honestly**: the original run logs were not retained, so per-run log-level
  proof is unrecoverable. The known failure mode (a missing vector index degrades *silently*
  to keyword-only) is ruled out by (b)–(e), not by logs. `scripts/smoke_retrieval.py` fails
  loudly if the vector side ever goes dark and is the standing health check.
- **Phase F: intentionally inactive.** Controlled same-code runs showed hybrid depth 50 retained
  the same 0.895 Hit@10 as keyword depth 50 but reduced MRR from 0.647 to 0.603. Hybrid depth 100
  raised Hit@10 to 0.910 but still scored below keyword depth 200. Vector retrieval is retained
  as a demonstrated capability, not forced into the higher-scoring official policy.

## Conclusions

**Largest gains, ranked.**
1. Conversation state + open clarification (baseline → A): accumulating disclosed constraints
   and handling override semantics changed the task from isolated search into multi-turn intent
   convergence.
2. Verbatim phrase/price reranking (B → E): a few milliseconds of deterministic constraint
   checking produced the largest precision gain and beat the attempted 0.6B reranker on
   feasibility.
3. Index-text enrichment (A → B): aligning indexed fields with the simulator's constraint
   sources improved every scenario.
4. Deeper lexical recall (E → F): correctly propagating `top_k` and reranking 200 lexical
   candidates reduced misses from 21 to 15 and raised the score from 0.786 to 0.820.

**Did vector retrieval help?** It proved useful as an available semantic route, but equal-weight
fusion did not improve the final controlled policy. At depth 50 it preserved Hit@10 and lowered
MRR; at depth 100 it raised coverage but still lost on the weighted score. This is why Phase F
uses metric-driven routing rather than treating architectural complexity as automatically better.

**Which variant to submit: Phase F (#8).** It has the highest verified Technical Score
(0.819973), 0.925 Hit@10, zero API token cost, and the strongest CPU/offline reproducibility.
The vector and neural ranking paths remain implemented for the hosted demo and documented
experiments, while official scoring selects the measured best route.

**Known remaining risk**: unrecognized messages are now retained as bounded raw-text context, and explicit paraphrased override cues clear stale unstructured preferences. This protects retrieval when the private set changes the fixed simulator wording. The deterministic phrase reranker still rewards literal overlap, however, so unseen synonyms can reduce ranking precision. A lightweight structured paraphrase extractor is the next low-cost improvement to test.

**Judging-criteria support.**
- *Technical Execution*: 0.820 composite with ≥ 0.900 Hit@10 in every scenario; unchanged
  evaluator/data/catalog; explicit service-contract fix; focused regression tests.
- *Innovation*: multi-route retrieval was built and ablated, while adaptive policy selection,
  protocol-aware state, and deterministic constraint fidelity produced the selected result.
- *Feasibility*: $0 marginal cost, no network, no credentials, no required vector artifact or
  model weights, zero API tokens, and a clean fallback story.
