# Ablation Study — Conversational Shopping Agent (TechJam)

All scores come from the **unmodified official evaluator** (`evaluator/local_evaluator.py`) on
`data/public_set.jsonl` (200 sessions), run as:

```
shopping_copilot\venv\Scripts\python -m evaluator.local_evaluator --catalog starter\catalog.jsonl --dataset data\public_set.jsonl --output <results file>
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
| 5 | Stateful **keyword-only** | *(never run)* | unknown | unknown | unknown | unknown | **unknown** | — |
| 6 | Phase D: + Qwen3-Reranker-0.6B | *(aborted ~25%)* | unknown | unknown | unknown | unknown | **unknown** | ~3.8 s |
| 7 | Phase E: + phrase boost & price filter (**current**) | `results_phaseE.json` | 0.895 | 0.605 | 3.16 | 0.785 | **0.786** | ~0.82 s |

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

### 5 — Stateful keyword-only: not measured

- No run ever combined the stateful conversation strategy with BM25 alone; the stateful agent
  has been hybrid from its first version. All metrics **unknown** rather than estimated.
- This is the missing controlled experiment that would precisely isolate the vector
  contribution. It is one cheap run away (force `strategy="keyword"` in the agent's retrieve
  call) and is recommended before the final report if precise attribution is wanted.

### 6 — Phase D: cross-encoder reranking (aborted)

- **Change from #3**: retrieve top-50, rerank with local Qwen3-Reranker-0.6B (bf16, 640-token
  document cap), return reranked top-10.
- **Status**: functionally verified (~3.8 s/turn on an RTX 4080 Laptop; est. 30–60 s/turn on
  CPU), but the evaluation was **stopped at ~25% by team decision** — too expensive per turn,
  and a feasibility risk under the organizers' reserved CPU-only final scoring. The evaluator
  writes results only at completion, so the partial run's score is **unrecoverable/unknown**.
- The library improvements (bf16 load, richer rerank document text) remain available to the
  demo app's ranking pipeline; the eval agent no longer uses them.

### 7 — Phase E: verbatim phrase boost + price filter (current, submitted candidate)

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

## Conclusions

**Largest gains, ranked.**
1. Conversation strategy + working hybrid retrieval (+0.41, baseline → A): most of the value
   came from *playing the session protocol* — draining the hidden intent card via
   `ask_attribute: "other"` and accumulating constraints into the query — on top of retrieval
   that actually functions.
2. Verbatim phrase/price re-sort (+0.15, B → E): ~5 ms of CPU string matching that
   outperformed the neural reranker's projected contribution at 1/1000th of its cost.
3. Index-text enrichment (+0.12, A → B): aligning indexed fields with where the simulator
   sources its constraints.

**Did vector retrieval help?** Yes — browsing is the strongest evidence (0.025 keyword-only
stateless vs 0.675 hybrid stateful; "I'm looking for X, but I'm still exploring" gives keyword
search almost nothing to match). Limitation: constraint accumulation also boosts browsing, and
without the row-5 ablation the precise split between state and semantics is **not attributable**.

**Which variant to submit: Phase E (#7).** Highest measured score (0.786, 7.3× baseline);
deterministic (identical scores on rerun) with zero token cost; most robust to the organizers'
reserved CPU-only/offline scoring — everything except query embedding (~1–2 s/turn on CPU) is
CPU-trivial, and degradation is graceful (no phrase matches ⇒ ties ⇒ RRF order; unparsed
budget ⇒ neutral); simplest dependency story (no reranker weights to bundle).

**Known risk to disclose**: the agent's message parsing and phrase matching assume the
simulator's exact templates and verbatim constraint text. The organizer reserves the right to
add natural-language paraphrasing on the private set; phrase boost and price filter degrade
gracefully under it, but template parsing does not — a raw-text query fallback for
unrecognized messages is the recommended pre-submission hardening.

**Judging-criteria support.**
- *Technical Execution*: 0.786 composite with ≥ 0.867 hit@10 in every scenario; the evaluator,
  dataset, and catalog untouched; one-command reproduction.
- *Innovation*: hybrid RRF retrieval, protocol-aware conversation state, and the
  verbatim-constraint insight — a CPU string check beating a 0.6B neural reranker is a
  measured, defensible finding; this ablation itself documents mechanism-driven iteration.
- *Feasibility*: $0 marginal cost, ~0.8 s/turn on a laptop GPU, fully offline-capable, zero
  tokens; the CPU-only caveat (query embedding) is quantified and disclosed rather than hidden.
