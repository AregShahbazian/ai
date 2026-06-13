# Benchmark UI — tasks

Design: [design.md](design.md). Branch `feature/benchmarks-runner`. All ✅ done.

## T1 — bot read-endpoints ✅
- `/api/bot/bench/{algos,markets,sessions}` over `results.db` (`immutable=1`,
  ro). 404 when no data.

## T2 — runner ro-read compatibility ✅
- results.db in DELETE journal mode (no WAL sidecars). Existing VPS db converted
  in place.

## T3 — frontend dashboard ✅
- `src/bench/{api,charts,BenchView}.tsx`; hash route + entry button in
  `main.tsx`; `.bench-*` styles in `app.css`.
- Views: algo leaderboard, return-distribution histogram + stats, per-market
  signed bars (click-to-filter).

## T4 — deploy + verify ✅
- Pushed; CI `web` + `api` deploys green. Endpoint returns donchian/2340
  sessions. UI verified live (Playwright screenshot) rendering the donchian run:
  leaderboard + histogram + per-market bars.

URL: `https://putcafe.46-250-232-224.sslip.io/web/benchmarks-runner/#/bench`

## Follow-ups (not done)
- Cross-algo compare view (needs ≥2 algos benchmarked; groups by shared windows).
- Sessions drill-down table per market; runs/provenance view.
- Combined cross-algo leaderboard endpoint.
