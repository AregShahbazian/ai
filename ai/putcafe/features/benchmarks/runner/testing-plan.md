# Broadest benchmark — testing plan (all algos)

Goal: benchmark **every algo** with fixed settings against the stored corpus,
on **identical data slices**, so the results are comparable and reproducible.
One run = one algo (`start.sh <algo>`); persist the session + per-window results.

Companion to [prd.md](prd.md) / [design.md](design.md). Drops benchmark-maps for
now (fixed algo-settings only).

## Algos under test (7)

`dca`, `pivot`, `ma_cross`, `rsi_revert`, `bollinger`, `donchian`, `macd`
(all present in the WT after merging `main`). Each runs with its **tuned/default
fixed config** — no per-algo grid.

## Datasets — from what we actually have

`overview.sh` (2026-06-13) shows 16 exchanges / 187 markets / 6 GB, but coverage
is very uneven. For a fair benchmark we use only the **deep-history** exchanges —
full 2-year span on 1m/1h/1d:

| Tier | Exchanges | Use |
|---|---|---|
| **Deep (use)** | binance, bybit, cryptocom, kucoin, woo, htx, bitvavo | full 2y, all resolutions — the benchmark set |
| Partial | okx (1d only from 2025-08), mexc (1m only recent) | optional, resolution-restricted |
| Shallow (skip) | bingx, kraken, hyperliquid, hitbtc, toobit, poloniex, gate | too recent/sparse — would inject gaps & bias |

- **Markets:** the corpus is already majors-only (bases BTC/ETH/SOL/BNB/XRP vs
  stablecoins, top-20/exchange). Across the 7 deep exchanges ≈ **83 markets**.
- **Resolution:** **1h** is the primary axis — best signal-vs-compute balance
  (2y ≈ 17,500 bars/market; 1m is ~50 MB/session JSON and its noise penalizes
  slower algos). Add **1d** as a slower-regime cross-check if wanted. **Skip 1m**
  for the broad sweep.

## Windowing — does length bias algos? Yes.

A single **full-2y** backtest per market gives **one** number, dominated by that
specific regime, and can't separate skill from luck. It also under/over-serves
algos unevenly:

- **Too short** → indicator algos (ma_cross, macd, bollinger, donchian,
  rsi_revert) spend most bars in warmup and fire too few trades; high-frequency
  algos look artificially better. dca (cadence ≈ 7d) barely enters.
- **Too long** → few independent samples, regime-dominated, heavy compute.

So we sample **many fixed-size random windows** instead of one long run, and read
a **distribution** (median/mean + variance) per algo.

### Rules for fairness

1. **Size in bars, not calendar time.** 1h windows of **500–2000 bars**
   (≈ 3 weeks to ~3 months). The 500 floor leaves ≥ ~300 active bars even after
   the slowest algo's warmup → every algo gets a meaningful trade count.
2. **Identical slices across all algos.** Windows are drawn **per
   `(exchange, market, resolution)`**, seeded — **independent of which algo or
   run** — so `dca` and `macd` are scored on the exact same slices. This is the
   single most important fairness lever.
3. **Same seed everywhere.** One global `seed` (e.g. 42) → the whole window set
   is replayable; the resolved absolute ranges are stored on each result row.
4. **~30 windows/market** → ≈ 2,490 sessions per algo (well under the 10k cap).

> **Runner change required:** the current `build_sessions` draws windows in
> `config × market` order, so different configs/algos would get *different*
> windows. For cross-algo comparison the draw must be keyed by
> `(seed, exchange, market, resolution)` only (e.g. a per-market
> `random.Random(hash(...))`), reused across every algo and run. This is a small
> change to `_windows`/`build_sessions`.

## Per-algo spec

One committed spec per algo, fixed settings, e.g. `specs/<algo>.json`:

```json
{ "algo": "donchian",
  "params": { "quoteAmount": 100, "leverage": 1, "feesEnabled": true,
              "startingBalance": 1000, "...": "tuned defaults" },
  "pivots": { "enabled": false },
  "selector": { "exchanges": ["binance","bybit","cryptocom","kucoin","woo","htx","bitvavo"],
                "bases": ["BTC","ETH","SOL","BNB","XRP"],
                "quotes": ["USDT","USDC","USD","EUR"],
                "resolutions": ["1h"] },
  "range": { "mode": "random", "n": 30, "minBars": 500, "maxBars": 2000, "seed": 42 } }
```

`start.sh` takes an **algo** (default e.g. `donchian`), loads `specs/<algo>.json`.
Fixed settings come from each algo's tuned defaults (`backend/bot/tuned_defaults.json`).

## Persistence (already built)

One row per session in `/data/bench/results.db`, keyed
`(config_hash, exchange, market, resolution, range_start, range_end)`, carrying
`config_hash` + `corpus_manifest_ref` (reproducibility) and the core metrics
(`return_pct, win_rate, max_drawdown, trades, bust, …`). A run manifest records
the spec + corpus provenance. Idempotent upsert ⇒ resume/re-run safe.

## Execution

```bash
# one run per algo (same windows across all, by construction):
for a in dca pivot ma_cross rsi_revert bollinger donchian macd; do
  ./scripts/dev/local/bench/start.sh "$a"; ./scripts/dev/local/bench/monitor.sh
done
```
(or kick them sequentially, checking `status.sh` between.)

## Viewing results

- **`./scripts/dev/local/bench/leaderboard.sh <algo> [metric]`** → ranked
  markdown (per-market + overall), copied to `scripts/dev/local/bench/out/`.
  Default metric `return_pct`; also `win_rate`, `max_drawdown`.
- **`./scripts/dev/local/bench/export.sh <algo>`** → Parquet of all that algo's
  result rows → `out/`, for cross-algo analysis / NN training (pandas/polars).
- To compare algos head-to-head: export each and group by
  `(exchange, market, resolution, range_start)` — identical slices line up, so
  median `return_pct` and its variance per algo are directly comparable. (A
  combined cross-algo leaderboard is a small follow-up if wanted.)
- No UI — markdown + parquet only (frontend view is a later slice).

## How to read it

- Rank algos by **median `return_pct` across windows**, not the single best
  market — robustness beats a lucky slice.
- Cross-check **`max_drawdown`** and **`bust` count** — a high mean return with
  frequent busts is fragile.
- Low **variance** across windows ⇒ the edge generalizes across regimes.

## Open / next

- Implement the per-market shared-window draw (fairness rule 2).
- Generate the 7 per-algo specs from tuned defaults.
- Optional: a `compare.sh` that merges per-algo exports into one ranked table.
