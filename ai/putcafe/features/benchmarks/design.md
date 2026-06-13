# Candle store & scraper — design

PRD: [prd.md](prd.md) (`pc-candle-store`)

## Architecture

New backend service **`backend/scrape/`** (own image, Python 3.12 + ccxt +
polars) plus a shared named volume **`candledata`**:

```
compose: db, positions, bot, + scrape (profiles: [scrape], restart: "no")
volume:  candledata → /data   (scrape: rw, bot: ro)
```

- `scrape` is NOT part of the normal stack (compose profile) — it only runs
  when started by the ops scripts. Lifecycle = container lifecycle:
  `up -d` = start/resume, `stop` = graceful stop (SIGTERM → flush + manifest),
  `logs -f` = monitor.
- `bot` mounts the volume read-only and serves stored candles (§5) — no new
  deps (stdlib `sqlite3`).
- Named volume (not bind mount) so CI's `rsync --delete` of `backend/` can
  never touch the corpus.

## Scraper package (`backend/scrape/scraper/`)

| File | Role |
|---|---|
| `config.py` | EXCHANGES (18 ccxt ids), BASES {BTC,ETH,SOL,BNB,XRP}, QUOTES (USDT/USDC/USD/EUR/FDUSD/DAI/TUSD), TOP_N=20, YEARS=2, RESOLUTIONS 1m/1h/1d, paths |
| `store.py` | per-exchange shard `/data/<exchange>.db`, WAL; `candles(market, resolution, ts, o,h,l,c,v)` PK `(market,resolution,ts)`, `INSERT OR REPLACE` executemany; watermark = `MAX(ts)` query |
| `markets.py` | per exchange: `load_markets` → spot+active, base∈BASES, quote∈QUOTES → rank by 30d quote volume (sum of last 30 **1d candles** `close×volume` — no ticker API needed) → top 20 |
| `run.py` | asyncio orchestrator: one worker task per exchange (`ccxt.async_support`, built-in throttle), markets×resolutions sequential within it; pages `fetch_ohlcv(since, limit)` from `max(watermark, now−2y)` to now; empty page → skip ahead one page-span, record gap; writes via `asyncio.to_thread`; SIGTERM → stop event → flush, manifest, exit 0 |
| `status.py` | writes `/data/status.json` every ~5 s (run id, per-exchange state/market counts/candles/errors) |
| `manifest.py` | end of run (done or stopped): `/data/manifests/<run-id>.json` + `.md` — coverage per exchange/market/resolution (count, min/max ts, gaps, errors), wall-clock, ccxt version |
| `export.py` | CLI `python -m scraper.export <exchange> <market> <resolution> [start end]` → Parquet via polars to `/data/exports/` |

Resume needs no state beyond the shards: watermark = last stored ts per
(market, resolution); `resume` = `start`.

## Bot read endpoint

`GET /api/bot/candles?exchange&market&resolution&start&end` (epoch-s) → reads
`/data/<exchange>.db`, returns `{candles: [{time(s), open, high, low, close,
volume}]}` (bot's existing `Candle` shape; ms→s on the way out). Missing
shard/range → **404 "not in store"** — never falls back to live.

## Ops scripts

`scripts/dev/remote/scrape/scrape.sh` — on-box multiplexer
(`start|stop|resume|status|monitor|export <args>`), compose-profile commands +
`status.json`/`du` readout. `scripts/dev/local/scrape/<cmd>.sh` — thin wrappers:
source `../edge/_conn.sh`, scp the remote script (idempotent), run it;
`export.sh` additionally scp's the Parquet back to `./exports/`. All safe to
re-run.

## Resolved decisions

- **One-shot container via compose profile** (not long-lived worker) — stop =
  `compose stop`, resume = re-`up` (was an open PRD question).
- **Top-20 ranking from 30×1d candles** per candidate pair, not ticker APIs
  (was an open PRD question).

## Open questions

- Exact per-exchange `fetch_ohlcv` page limits — use 1000 default, trust ccxt
  clamping; tune per exchange only if a scrape proves slow.
