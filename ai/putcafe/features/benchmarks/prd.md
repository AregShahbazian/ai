---
id: pc-candle-store
---

# Candle store & scraper — benchmark data layer

The first slice of the **benchmarks** initiative. Benchmarks (and
benchmark-maps) need a fixed, reproducible candle corpus to run against —
re-fetching live data would drift and break reruns. This PRD covers **only
data acquisition and storage**; the benchmark/benchmark-map *runner* is a
separate sibling PRD (see Non-requirements).

## Context — what the corpus is for

- **Benchmark** — a set of backtest sessions for one algo+config across many
  markets / resolutions / ranges (algo comparison).
- **Benchmark-map** — a set of benchmarks across different configs of one algo
  (internal tuning).
- Both replay against stored candles, so results are reproducible and the same
  inputs can train AI / neural-net models downstream.

Today candles are fetched client-side from Binance spot only
(`frontend/src/binance/api.ts`); the bot-backend is stateless and receives
candles in the request body. This feature adds the **first server-side candle
store** and a scraper that populates it.

## Requirements

### 1. Storage — on the VPS, persisted

- Lives in the persisted Docker volume on the VPS (alongside the existing
  backend DB), **not** on the laptop and not re-fetched per run.
- **Canonical format: SQLite, sharded one DB file per exchange**
  (`candles/<exchange>.db`). SQLite's single-writer lock is per-file, so 18
  files = 18 independent writers with **zero lock contention** — true parallel
  writes without a heavier DB. The shard key (exchange) is also the natural
  top-level partition.
- Within a file, rows keyed by `(market, resolution, ts)`, upsert-on-conflict so
  re-scrapes are idempotent and incremental (resume from the last stored candle,
  never re-download a covered range). WAL mode.
- One row = one OHLCV candle (`ts, open, high, low, close, volume`). Timestamps
  in epoch-ms, UTC.
- Reads/exports span all shards by `ATTACH`-ing the files (or via DuckDB/Polars
  reading them as one virtual table) — a single logical corpus when queried.
- **ML export**: a command to dump any slice to **Parquet** (columnar,
  pandas/NN-friendly) without touching the canonical store.

### 2. Exchanges — multi-exchange via CCXT

- Source the 18 exchanges in scope (all of the app's exchange list **except
  Binance US**): Binance, BingX, BitMart, Bitvavo, ByBit, Coinbase, Crypto.com,
  Gate.io, HitBTC, HTX, Hyperliquid, Kraken, KuCoin, MEXC, OKX, Poloniex,
  Toobit, WOO.
- Use **CCXT** (Python — the bot-backend is already Python) for unified public
  OHLCV. Public candle endpoints need no auth/keys.
- Per-exchange rate limits respected via CCXT's built-in throttling. Exchanges
  scraped **fully in parallel** — each exchange has its own fetcher(s) feeding
  its own SQLite shard (§1), so writes never contend. The scrape is
  network/rate-limit-bound, so wall-clock is set by the slowest exchange's rate
  limit, not by disk.

### 3. Scope filters — aggressive, to fit the disk

The VPS has ~42 GB free of 72 GB. To stay well within budget, the scrape is
filtered by **all** of:

1. **Top 20 markets per exchange** by 30-day quote volume.
2. **Majors only** — base in {BTC, ETH, SOL, BNB, XRP}, quote in the
   stablecoins (USDT/USDC/etc.). Intersection of #1 and #2.
3. **Last 2 years** only (rolling window from scrape date), not full history.
4. **Resolutions: 1m, 1h, 1d** only.

Estimated footprint: ~10–15 GB. The filter thresholds are config, not
hard-coded, so the corpus can be widened later if disk is upgraded.

### 4. Scraper — batch job, resumable, self-documenting

- Runs as a backend command / worker (not in the request path). Long-running;
  must be **resumable** — interrupting and restarting continues where it left
  off (per the incremental upsert in #1).
- Per run, emits a **manifest**: which exchanges/markets/resolutions/ranges were
  covered, candle counts, gaps/failures per market, start/end wall-clock,
  CCXT/exchange versions. Manifest written as both machine-readable JSON **and**
  a human `.md` summary — these are the reproducibility + training-provenance
  record.
- Gaps (missing candles, delisted markets, exchange errors) are recorded, not
  fatal — a failed market is logged and the run continues.

### 5. Serving — read API for backtests

- Bot-backend gains a read endpoint to fetch a stored candle range for a given
  `exchange / market / resolution / [start,end]`, so benchmark runs (and
  eventually the live app) source candles from the store instead of the public
  API.
- Returns the same `Candle` shape the bot-backend already uses; missing ranges
  return an explicit "not in store" rather than silently falling back to live.

### 6. Operational rule — scripted, idempotent

- Every VPS action goes through a committed, idempotent script under
  `scripts/dev/local/` (per repo workflow) — no ad-hoc docker/ssh one-liners.
  Safe to re-run anytime.
- A dedicated dir, `scripts/dev/local/scrape/`, holds thin SSH wrappers around
  the server-side scraper (which owns the resumable state):
  - **`start`** — kick off / launch the scrape job (detached on the VPS).
  - **`status`** — current progress: running?, per-exchange/market coverage,
    candle counts, last manifest, disk used.
  - **`stop`** — pause/halt the job, leaving stored candles intact.
  - **`resume`** — continue a stopped/interrupted job from where it left off
    (relies on the incremental upsert in #1; idempotent if already complete).
  - **`monitor`** — follow live progress/logs until interrupted.
  - **`export`** — dump a slice to Parquet (#1).

## Non-requirements

- **No benchmark/benchmark-map runner here** — that consumes this corpus and is
  a separate PRD.
- No live/streaming updates, no websocket ingestion — historical batch only.
- No spot vs futures distinction beyond what CCXT's default market type gives;
  revisit if the algos need futures-specific candles.
- No de-dup/normalization across exchanges (each exchange's candles stored
  as-is), no candle gap-filling/interpolation.
- No laptop-side storage, no full-history scrape, no Binance US.
- No automatic widening of filters — thresholds change only via config edit.

## Resolved

- **Storage layout** — per-exchange SQLite shards (§1), one writer per shard for
  true parallel writes. (Was: single file vs per-exchange.)

## Open questions

- Scraper as a one-shot container/cron vs a long-lived worker?
- Do we need 30-day volume from each exchange's ticker API to rank top-20, or a
  static curated major-pairs list (simpler, no ranking call)?
