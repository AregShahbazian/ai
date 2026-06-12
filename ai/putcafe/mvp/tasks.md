# MVP — Tasks

PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md)

1. **Positions-backend** — `backend/positions/` (Fastify + pg: schema bootstrap,
   sessions/orders/state routes, fill simulation, CORS, /health, Dockerfile).
   Verify: `tsc` clean (build in Docker on deploy).
2. **Bot-backend** — `backend/bot/` (FastAPI: seed/step, in-memory store, DCA,
   positions client, CORS, /health, Dockerfile) + `backend/compose.yml`.
   Verify: `python -m py_compile`; compose config parses.
3. **Edge + scripts** — `site.caddy` reverse_proxy matchers;
   `remote/edge/setup-api.sh` (Docker install, idempotent);
   `local/edge/deploy-api.sh` (rsync, compose up --build, health).
   Verify: `bash -n`; later live.
4. **CI** — `api` job in `ci.yml` (main only). Verify: YAML parses.
5. **Frontend data/api layer** — `api/backend.ts`, `fetchKlinesRange`,
   `frontend/.env`. Verify: build.
6. **Backtest engine** — `backtest/engine.ts` (+types): step/play/pause/
   stepBack/restart/stop, speeds, auto-resume pause, headless runner,
   re-seed on 409. Verify: build.
7. **Chart additions** — ChartView session mode + markers;
   `RangeHighlight` primitive; `ChartContextMenu`. Verify: build.
8. **Panel + controls** — `BacktestPanel` (config, pickers, results, sessions
   list), `PlaybackControls` (+shortcuts), App wiring, styles. Verify: build.
9. **Deploy + smoke** — re-run `setup.sh` (Caddy), `deploy-api.sh`; curl a full
   headless session against the live API (create → seed → steps → orders →
   state); deploy frontend to staging. Verify: 200s, trades persisted,
   PnL math sane.
10. **Review doc** — checklist incl. Trading-Terminal-style context cases
    (market/timeframe switch during replay).
