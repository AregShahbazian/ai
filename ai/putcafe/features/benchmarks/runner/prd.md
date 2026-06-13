---
id: pc-benchmark-runner
---

# Benchmark runner — algo evaluation over the candle corpus

The second slice of the **benchmarks** initiative. The candle store
(`pc-candle-store`, sibling PRD at [../prd.md](../prd.md)) gives us a fixed,
reproducible candle corpus on the VPS. This PRD covers the **runner** that
consumes that corpus: it replays an algo over many slices of stored candles,
collects per-session metrics, and aggregates them into ranked leaderboards —
reproducibly, so the same inputs can later train AI / neural-net models.

## Context — what we have, what this adds

- **Have:** a stateless backtest engine. `POST /api/bot/futures/run` takes
  `{candles, algo, pivots, params}` and returns a full snapshot — `equity`,
  `realizedPnl`, `wins`, `losses`, `bust`, `trades[]`, `events[]`. Algos live in
  a registry (`ALGOS = {"dca", "pivot", …}`). Candles come from the store via
  `GET /api/bot/candles?exchange&market&resolution&start&end` (404 when not
  stored — never falls back to live).
- **Add:** an orchestrator that builds the cartesian set of backtest *sessions*
  for a benchmark spec, runs each through the engine against stored candles,
  persists the metrics, and rolls them up into leaderboards.

## Definitions (from the candle-store PRD)

- **Session** — one backtest run: one algo + one config over one
  `(exchange, market, resolution, [start, end])` slice. The atomic unit.
- **Benchmark** — one algo + **one fixed config** across **many**
  markets / resolutions / ranges. Purpose: *algo comparison* — "how does this
  algo do across the corpus?"
- **Benchmark-map** — **many configs** of **one algo**, each config itself run
  as a benchmark. Purpose: *internal tuning / hyperparameter search* — "which
  config of this algo is best?"

A benchmark is a grid of sessions; a benchmark-map is a grid of benchmarks.

## Requirements

### 1. Benchmark spec — declarative, hashable

A run is driven by a **spec**: an algo, a config (or a config grid for a
benchmark-map), and a corpus selector (which exchanges / markets / resolutions /
ranges to sweep). The selector supports "all in store" plus filters
(exchange/base/quote/resolution allowlists, an explicit date window, or "the
full stored 2y").

- **Range mode** — how each session's `[start, end]` slice is chosen from a
  market's stored history. Three modes:
  1. **Full** — the entire stored window (default 2y) per market.
  2. **Fixed window** — an explicit `[start, end]` (or walk-forward windows: N
     equal slices) applied to every market.
  3. **Random** — N dice-rolled windows per market, each sized between `minBars`
     and `maxBars`, candle-aligned, drawn from that market's available history.
     This is the existing `rollRandomRange` logic (`pc-randoms`,
     `frontend/src/util/randomRange.ts`) ported to the runner. Crucially, the
     roll resolves to an **absolute** `[start, end]` that is *stored on the
     result row* — the dice stay out of the reproducible part, exactly as the
     randoms design intends. A **seed** in the spec makes the whole roll set
     replayable; the resolved absolute ranges are what guarantee
     reproducibility regardless. Random mode gives unbiased sampling across the
     corpus (no cherry-picked bull/bear windows) and many sessions per market
     for statistical weight.

- The config is the engine's existing knobs — `FuturesParams`
  (`quoteAmount, leverage, tpSlRatio, slCapPct, frequencySec, feesEnabled,
  startingBalance`) + `PivotOptions` (`lookback, alternation, …`). No new algo
  knobs invented here.
- For a **benchmark-map**, the spec carries a config *grid* (per-knob value
  lists); the runner expands it to the cartesian set of configs, each becoming
  one child benchmark. Guardrail: a cap on total expanded sessions, with a
  dry-run count printed before execution (no silent giant runs).
- The spec is serialized canonically so it has a stable **`config_hash`**
  (see §3). Editing any knob changes the hash.

### 2. Execution — fan out over sessions, reuse the engine

- The runner enumerates sessions from the spec × corpus selector, fetches each
  slice from the **store** (`/api/bot/candles`), and calls the existing
  `/api/bot/futures/run` — **no re-implementation of the backtest**.
- Sessions are independent → run in parallel (bounded pool). A session whose
  slice is **not in store** (404) or errors is recorded as a gap/failure and
  skipped — never fatal to the run (mirrors the scraper's gap policy).
- Resumable: a completed `(config_hash, exchange, market, resolution, range)`
  session is not re-run on restart (idempotent upsert on the results table).
- Runs as a backend command / worker, not in the request path. Long-running.

### 3. Results store — one row per session, reproducible

- Persisted alongside the corpus (same VPS volume), canonical format **SQLite**
  (consistent with the candle store). One **results** row per session:
  - keys: `config_hash, algo, exchange, market, resolution, range_start,
    range_end`
  - config: the full resolved config JSON (so a row is self-describing)
  - metrics: `realized_pnl, return_pct, equity_final, wins, losses, trades,
    win_rate, max_drawdown, bust` (+ room for sharpe/profit-factor later)
  - **provenance (the reproducibility hook):** `config_hash`, plus a
    **`corpus_manifest_ref`** — the scraper run-id / manifest that produced the
    candles this session replayed. Together `(config_hash, corpus_manifest_ref,
    keys)` make any result re-derivable byte-for-byte.
  - bookkeeping: `run_id, created_ts, engine/app version`.
- Upsert-on-conflict so re-runs are idempotent and incremental.

### 4. Leaderboards — ranked aggregation

- A benchmark's sessions aggregate into a **leaderboard**: rankable by a chosen
  metric (default `return_pct`, also `win_rate`, `max_drawdown`, `profit
  factor`), with breakdowns (per-market, per-resolution, overall).
- A **benchmark-map** aggregates one level up: rank **configs** against each
  other (each config's benchmark summarized to a single score), surfacing the
  best-performing config of the algo.
- Aggregation is a **query over the results table**, not a separate store —
  leaderboards are always live against whatever sessions have completed.
- Exposed as a read endpoint and/or a CLI/`.md` report (TBD in design); at
  minimum a machine-readable JSON + a human summary, like the scraper manifest.

### 5. ML export — Parquet for downstream training

- A command dumps any results slice (and, optionally, the underlying session
  candle slices) to **Parquet** — columnar, pandas/NN-friendly — without
  touching the canonical SQLite store. Reuses the candle store's `export`
  approach.
- Each export carries its `config_hash` + `corpus_manifest_ref` so a training
  set is fully traceable to the exact configs and candle corpus it came from.

### 6. Operational rule — scripted, idempotent

- Every VPS action goes through a committed, idempotent script under
  `scripts/dev/local/…` (per repo workflow) — no ad-hoc docker/ssh one-liners.
- A `bench/` script set mirrors the scraper's: **`start`** (run a spec),
  **`status`**, **`stop`**, **`resume`**, **`monitor`**, **`leaderboard`**
  (print/pull a ranked report), **`export`** (Parquet). All safe to re-run.

## Non-requirements

- **No new algos and no new engine math** — the runner only orchestrates the
  existing `/futures/run`. Adding/optimizing algos is separate.
- **No live trading, no live candles** — store-only; a missing slice is a gap,
  never a live fetch.
- **No AI/NN training here** — this produces the reproducible, Parquet-exportable
  dataset; the model training is a downstream PRD.
- No UI/visualization beyond the read endpoint + report (a frontend leaderboard
  view, if wanted, is a later slice).
- No auto-tuning loop (the runner *evaluates* a config grid; it doesn't *search*
  adaptively — that's a future optimizer PRD).
- No cross-exchange normalization/dedup (each session is one exchange's candles).

## Resolved

- **Definitions** — benchmark = one config × many slices; benchmark-map = many
  configs × (each a benchmark). Session is the atomic unit. (From candle-store
  PRD; restated here.)
- **Reuse the engine** — runner calls `/api/bot/futures/run`, never
  re-implements the backtest.
- **Reproducibility hook** — every result row carries `config_hash` +
  `corpus_manifest_ref`; exports inherit both. (Per this turn's discussion.)
- **Range modes** — full / fixed-window / random; random reuses `pc-randoms`'
  `rollRandomRange` and stores the *resolved absolute* range, so dice never
  break reproducibility. (Per this turn's discussion.)
- **Trigger & placement** — a new **`backend/bench/`** service, run as a
  **compose-profile worker** (symmetric with `scrape`): mounts the corpus volume
  read-only and calls `bot`'s `/api/bot/futures/run` over the internal network.
  Not part of the normal stack; `up`/`stop`/`logs` lifecycle. (Per this turn's
  discussion.)
- **Metric set v1** — **core only**: `realized_pnl, return_pct, win_rate,
  max_drawdown, bust` (+ `equity_final, wins, losses, trades`). The engine
  returns raw trades, so sharpe / profit-factor / expectancy are derivable later
  from stored rows without re-running. (Per this turn's discussion.)
- **Config-grid expansion cap** — default ceiling **10,000 sessions**: a grid
  expanding past it prints the dry-run count and requires explicit confirmation
  before executing. Configurable. (Per this turn's discussion.)

## Open questions

_None open — all resolved above. Remaining shape (results schema details,
leaderboard endpoint vs CLI report) is design-doc work, not product decisions._
