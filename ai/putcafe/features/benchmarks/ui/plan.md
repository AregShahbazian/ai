# Benchmark UI — viewing sessions & results, visualized

A small web view to browse benchmark **sessions** and their **results**
(per-algo, per-market, per-window) and compare algos visually. Consumes the
`results.db` produced by the runner ([../runner/prd.md](../runner/prd.md)).

## Decision: reuse the frontend, NOT a separate Caddy site

The repo already ships a Vite/React/TS SPA deployed by CI to Caddy slots
(`main` → `/web/staging/`, `feature/**` → `/web/<slot>/`). The benchmark UI is
**a route in that same app**, fed by a new `bot` read-endpoint over `results.db`.

Why this over a standalone viz site:

| | Reuse frontend (chosen) | Separate Caddy site |
|---|---|---|
| Deploy | free — existing CI `web` job, slots | new site.caddy + setup script + CI job |
| Data access | bot already mounts `/data:ro`, reads sqlite | new service or duplicate mount |
| Auth/host | inherits the app's host + CORS | new host, new config |
| Effort | one view + one endpoint | a whole second app + edge wiring |

A separate static tool (Streamlit/Observable/metabase) was considered — rejected:
it needs its own Caddy site, auth, and deploy, for a view the SPA can host
natively. The "follow other Caddy patterns" answer is: **don't add a site — the
frontend pipeline already is the pattern.**

## Stack

- **Frontend:** existing React 18 + Vite 6 + TypeScript. No new heavy deps.
- **Charts:** add **Recharts** (declarative, React-native) for bars / scatter /
  distributions — `lightweight-charts` (already in) is candle-oriented and a poor
  fit for leaderboards. (Alt: uPlot if bundle size bites; Recharts is fine here.)
- **Routing:** the app is currently single-view (no router). Add a minimal
  **hash-based view switch** (`#/bench`) or `react-router-dom` (small) — a top
  nav toggling Trading ⇄ Benchmarks. Lean: hash switch, zero new dep.
- **Data:** new `bot` read-endpoints over `/data/bench/results.db` (stdlib
  `sqlite3`, `mode=ro` — same pattern as `/api/bot/candles`).

## Backend — bot read-endpoints (over results.db, ro)

No new service; add to `backend/bot/app/main.py`:

- `GET /api/bot/bench/algos` — one row per algo/config_hash present: session
  count, avg/median `return_pct`, avg `win_rate`, avg `max_drawdown`, bust count.
  Powers the top-level algo leaderboard.
- `GET /api/bot/bench/markets?config_hash=` — per-(exchange,market,resolution)
  aggregates for one algo (drill-down). Mirrors `store.leaderboard_by_market`.
- `GET /api/bot/bench/sessions?config_hash=&exchange=&market=` — the raw session
  rows (each window: range, return_pct, win_rate, max_drawdown, trades, bust) for
  the distribution view + table.
- `GET /api/bot/bench/runs` — manifests list (run_id, spec, state, totals,
  corpus_manifest_ref) for provenance.

(The SQL already exists in `bench/store.py`; the bot re-expresses the few queries
it needs with stdlib sqlite3 — no import coupling across images. Missing
`results.db` → 404 "no benchmark data".)

## Frontend — structure & views

`frontend/src/bench/`:
- `api.ts` — typed fetches against the endpoints above (reuse the `req<T>` helper
  in `src/api/backend.ts`).
- `BenchView.tsx` — the dashboard shell + view switch.
- components per view below.

**Views / visualizations:**

1. **Algo leaderboard** (landing) — horizontal **bar chart** of median
   `return_pct` per algo, with a sortable table (sessions, win%, maxDD, busts).
   Sort by any metric. This is the headline "which algo wins" view.
2. **Algo detail** (click an algo) —
   - **Distribution** of `return_pct` across its windows (histogram / box) — shows
     robustness vs a lucky slice.
   - **Scatter** return_pct vs max_drawdown per session (risk/reward cloud).
   - **Per-market table** (ranked), drill to sessions.
3. **Cross-algo compare** — because all algos share identical windows (fairness
   fix), group sessions by `(exchange, market, resolution, range_start)` and plot
   **grouped bars / box-per-algo** on the same slices — the apples-to-apples view.
4. **Sessions table** — filterable raw rows (algo, exchange, market), each with
   its absolute range + metrics; links provenance (`corpus_manifest_ref`).
5. **Runs/provenance** — manifests list (run state, spec, corpus ref).

Keep it read-only and stateless — every view is a query; no writes from the UI.

## Deploy

Nothing new: push `feature/benchmarks-runner` (or a `feature/bench-ui` slot) →
CI `web` job builds and rsyncs to `/web/<slot>/`; the bot endpoints ship with the
already-wired `api` deploy. The preview slot URL is the test surface. No Caddy
edits.

## Phasing

1. **Backend** — the 4 read-endpoints in `bot` (small, testable with curl against
   the live `results.db`).
2. **UI v1** — view switch + algo leaderboard (view 1) + sessions table (view 4).
3. **UI v2** — algo detail distributions/scatter (view 2) + cross-algo compare
   (view 3) + runs (view 5).

## Open questions

- Hash-switch vs `react-router-dom` — lean hash (no dep); revisit if more routes
  appear.
- Recharts vs uPlot — start Recharts; swap only if bundle/perf demands.
- Does the UI need live polling while a run is in progress, or is on-demand
  refresh enough? Lean: a manual refresh + `/runs` state badge; no websockets.
