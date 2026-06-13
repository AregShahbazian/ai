# Benchmark UI — design

Plan: [plan.md](plan.md) (`pc-benchmark-runner`). Implemented on
`feature/benchmarks-runner`.

## Shape

- **No new service, no Caddy site.** A route in the existing Vite/React SPA +
  read-only `bot` endpoints over `/data/bench/results.db`. Ships via the existing
  CI `web` (frontend slot) + `api` (bot) deploys.

## Backend — bot endpoints (`backend/bot/app/main.py`)

Read-only over `results.db`. **Open with `?immutable=1`** — `/data` is a
read-only mount and plain `mode=ro` fails `SQLITE_CANTOPEN` on read-only media;
the bot only reads a completed snapshot, so immutable is correct.

- `GET /api/bot/bench/algos` — one summary row per algo/config_hash: sessions,
  avg/median/best/worst return_pct, avg win_rate, avg max_drawdown, busts
  (aggregated in Python; few config_hashes).
- `GET /api/bot/bench/markets?config_hash=` — per-(exchange,market,resolution)
  aggregates (SQL GROUP BY).
- `GET /api/bot/bench/sessions?config_hash=&market=…` — raw per-window rows.

404 "no benchmark data yet" when `results.db` is absent.

## Writer-side compatibility (runner)

`results.db` must be readable from the bot's ro mount:
- runner writes it in **DELETE journal mode** (not WAL) — a WAL reader needs to
  write the `-shm` sidecar, impossible on a ro mount. DELETE leaves no sidecars.
- combined with the bot's `immutable=1`, ro reads succeed.

## Frontend (`frontend/src/bench/`)

- `api.ts` — typed fetches (BASE convention from `api/backend.ts`).
- `charts.tsx` — dependency-free SVG: `Histogram` (return distribution),
  `HBars` (signed per-market bars). No charting lib added.
- `BenchView.tsx` — dashboard: algo leaderboard table → on select, return
  distribution histogram + stat strip + per-market bars; click a market bar to
  filter the distribution to that market.
- **Routing:** minimal hash switch in `main.tsx` (`#/bench`) + a floating entry
  button on the trading app. No router dependency.
- Styles appended to `app.css` (`.bench-*`).

## Deploy

`feature/**` push → CI `web` job → `/web/<slot>/` (slot = branch with `feature/`
stripped = `benchmarks-runner`). Bot endpoints via `api` deploy. URL:
`https://putcafe.<ip>.sslip.io/web/benchmarks-runner/#/bench`.

## Resolved

- Reuse frontend over a separate site (plan.md table).
- Dependency-free SVG charts over Recharts — smaller, no yarn.lock churn, fully
  controlled; revisit only if richer charts are needed.
- Hash switch over react-router — zero deps.
- `immutable=1` + DELETE journal — the two-part fix for ro-mount sqlite reads.
