# Candle store & scraper — tasks

Design: [design.md](design.md). Branch `feature/benchmarks`, worktree
`~/git/worktrees/putcafe/benchmarks`.

## T1 — scraper package

- `backend/scrape/Dockerfile` — python:3.12-slim, install requirements, copy
  `scraper/`, default CMD `python -m scraper.run`.
- `backend/scrape/requirements.txt` — ccxt, polars.
- `backend/scrape/scraper/{__init__,config,store,markets,status,manifest,run,export}.py`
  per design table.

Verify: `python -m scraper.run --dry-run` (lists selected markets per exchange,
no writes) against 2–3 exchanges locally; then a bounded real run (1 exchange,
1d only) produces rows + status.json + manifest.

## T2 — compose wiring

- `backend/compose.yml`: add `candledata` volume; `scrape` service
  (build ./scrape, `profiles: ["scrape"]`, `restart: "no"`,
  `candledata:/data`); mount `candledata:/data:ro` into `bot`.

Verify: `docker compose config` validates; `docker compose up -d` does NOT
start scrape; `--profile scrape up -d scrape` does.

## T3 — bot read endpoint

- `backend/bot/app/main.py`: `GET /api/bot/candles` per design (stdlib
  sqlite3, ro open `file:...?mode=ro`, 404 when shard/range missing).

Verify: with a seeded shard in the volume, curl returns candles in Candle
shape; bogus exchange/range → 404.

## T4 — ops scripts

- `scripts/dev/remote/scrape/scrape.sh` — multiplexer per design.
- `scripts/dev/local/scrape/{start,stop,resume,status,monitor,export}.sh`.

Verify: shellcheck-clean; `status` before any run reports "no data"; full
start→monitor→stop→status→resume cycle against the VPS.

## T5 — docs

- Append scrape ops to repo README (one section: scripts + endpoint).
- review.md checklist.

Commit message tag: `[pc-candle-store]`.
