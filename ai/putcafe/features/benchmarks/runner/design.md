# Benchmark runner — design

PRD: [prd.md](prd.md) (`pc-benchmark-runner`). Branch `feature/benchmarks-runner`,
worktree `~/git/worktrees/putcafe/benchmarks-runner` (off `feature/benchmarks`,
so the candle store + `/api/bot/candles` are present).

## Architecture

New backend service **`backend/bench/`** (own image, Python 3.12 + polars),
mirroring `scrape`:

```
compose: db, positions, bot, scrape, + bench (profiles: [bench], restart: "no")
volume:  candledata → /data (bench: ro — reads shards + writes results.db? see below)
```

- `bench` is NOT part of the normal stack (compose profile) — runs only via the
  ops scripts. Lifecycle = container lifecycle: `up -d` = start/resume,
  `stop` = graceful (SIGTERM → flush + manifest), `logs -f` = monitor.
- **Reuses the engine over HTTP** — for each session it POSTs to
  `http://bot:8102/api/bot/futures/run` (internal compose network). No backtest
  math is re-implemented. Candles are read **directly** from the corpus shard
  (`/data/<exchange>.db`, sqlite ro) — faster than a second HTTP hop — then sent
  in the run body.
- **Results live on the corpus volume** at `/data/bench/results.db` (+ status,
  manifests, exports under `/data/bench/`). The volume is shared rw with
  `scrape`; `bench` mounts it **rw** (it writes only under `/data/bench/`, never
  touching the `<exchange>.db` shards). `bot` keeps its `:ro` mount.

## Package (`backend/bench/bench/`)

| File | Role |
|---|---|
| `config.py` | `BOT_URL` (`http://bot:8102`), `DATA_DIR=/data`, `BENCH_DIR=/data/bench`, `RESULTS_DB`, `STATUS_FILE`, `MANIFEST_DIR`, `EXPORT_DIR`, `SPECS_DIR`, `SESSION_CAP=10000`, `CONCURRENCY` |
| `spec.py` | load a committed JSON spec (`specs/<name>.json`); dataclasses (algo, params, pivots, selector, range mode); `config_hash` = sha256(canonical-json of algo+params+pivots)[:12]; **grid expansion** → list of concrete configs (cartesian of per-knob lists; `SESSION_CAP` guard) |
| `candles.py` | sqlite ro reader over `/data/<exchange>.db`: `bounds(market,res)`, `slice(market,res,start,end)` → candle dicts (`time` epoch-s, OHLCV); `list_markets(exchange,res)` for "all in store" selectors |
| `randoms.py` | `roll_random_range(bounds, interval_s, min_bars, max_bars, rand)` — direct port of `frontend/src/util/randomRange.ts` (`pc-randoms`); seeded `random.Random` for replay |
| `metrics.py` | snapshot → core metrics: `realized_pnl, return_pct, equity_final, wins, losses, trades, win_rate, max_drawdown, bust` (drawdown from the ordered closed-trade pnl sequence vs `startingBalance`) |
| `store.py` | results SQLite (WAL): `results(config_hash, algo, exchange, market, resolution, range_start, range_end, config_json, corpus_manifest_ref, run_id, created_ts, <metrics…>)` PK `(config_hash, exchange, market, resolution, range_start, range_end)`, `INSERT OR REPLACE`; `done_keys()` for resume; `leaderboard()` queries |
| `runner.py` | asyncio orchestrator: expand spec → sessions (config × selector × range-mode windows); bounded `asyncio.Semaphore(CONCURRENCY)`; per session read candles, POST `/futures/run`, compute metrics, upsert; skip already-done (resume) & 404/empty slices (gap); SIGTERM → stop event → flush, manifest, exit 0 |
| `status.py` | writes `/data/bench/status.json` every ~5 s (run id, spec, sessions total/done/gaps/errors) — mirrors scrape |
| `manifest.py` | end of run: `/data/bench/manifests/<run-id>.json` + `.md` — spec, config_hash(es), corpus_manifest_ref, session coverage, wall-clock |
| `leaderboard.py` | CLI `python -m bench.leaderboard <spec> [--metric return_pct]` → ranked JSON + `.md` from `results.db` (per-config for a benchmark-map, per-market/overall for a benchmark) |
| `export.py` | CLI `python -m bench.export <spec> [--metric …]` → Parquet of the results slice via polars to `/data/bench/exports/`; carries `config_hash` + `corpus_manifest_ref` columns |
| `run.py` | entry: `python -m bench.run --spec <name>` (reads `specs/<name>.json`), `--dry-run` (count sessions, no calls) |

`corpus_manifest_ref` = most-recent `/data/manifests/*.json` run-id at run start
(the scrape provenance the sessions replayed against).

## Specs (`backend/bench/specs/`)

Committed JSON, so a run is reproducible from the repo. Two seeded examples:

- `algo-compare.json` — a **benchmark**: one algo, one fixed config, selector =
  all majors / 1h / random×N. (Algo comparison — swap `algo` to compare.)
- `pivot-map.json` — a **benchmark-map**: algo `pivot`, a small config grid
  (`tpSlRatio`, `slCapPct`, `pivots.lookback` value lists), same selector.

Spec shape:
```json
{ "algo": "pivot",
  "params": { "leverage": 1, "tpSlRatio": [1.5, 2, 3], "slCapPct": 4, ... },
  "pivots": { "enabled": true, "lookback": [3, 5] },
  "selector": { "exchanges": ["*"], "bases": ["BTC","ETH"], "quotes": ["USDT"],
                "resolutions": ["1h"] },
  "range": { "mode": "random", "n": 20, "minBars": 200, "maxBars": 1000, "seed": 42 } }
```
A list value on any `params`/`pivots` knob marks the grid axes (benchmark-map);
all-scalar = a single benchmark.

## Bot reuse

No change to `bot` required — `/api/bot/futures/run` already takes
`{candles, algo, pivots, params}` and returns the snapshot. `bench` is a pure
consumer over the internal network.

## Ops scripts

`scripts/dev/remote/bench/bench.sh` — on-box multiplexer
(`start <spec>|stop|resume <spec>|status|monitor|leaderboard <spec>|export <spec>`),
compose-profile commands + `status.json`/`du` readout — mirrors `scrape.sh`.
`scripts/dev/local/bench/<cmd>.sh` — thin wrappers: source `../edge/_conn.sh`,
scp the remote script (idempotent), run it; `leaderboard`/`export` scp the
`.md`/`.parquet` back to `./out/`. All safe to re-run.

## Resolved decisions (from PRD)

- Core metrics only (sharpe/profit-factor derivable later from stored rows).
- `SESSION_CAP = 10000`; a grid past it needs `--force`.
- New `backend/bench/` service, compose-profile worker, reads corpus ro-ish
  (rw only under `/data/bench/`), calls `bot` over the internal net.
- Reproducibility: every row carries `config_hash` + `corpus_manifest_ref`;
  random mode stores resolved absolute ranges.

## Open questions

- None blocking. Walk-forward window sub-mode can be added later; v1 ships
  full / explicit-window / random.
