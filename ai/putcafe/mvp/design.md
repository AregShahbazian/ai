# MVP — Design

PRD: [`prd.md`](prd.md) (`pc-mvp`). Replay UI spec mined from Superchart
(consumer-built panel per its Replay storybook) and Altrady cbs_desktop
(`feature/superchart-integration`): smart-pause on order/alert triggers,
auto-resume toggle ("Auto-resume playback after triggering order/alert.",
default on), quiz-style pick-on-chart date selection with labeled vertical
markers.

## Topology

Backends are **VPS-only** (never run locally). Frontend (localhost dev or the
deployed slots) talks to the same deployed API over HTTPS + CORS (`*`).

```
https://putcafe.<host>/
  /web/…                      static frontend (as today)
  /api/positions/* → 127.0.0.1:8101   positions-backend (Node 22 + Fastify + pg)
  /api/bot/*       → 127.0.0.1:8102   bot-backend (Python 3.12 + FastAPI)
VPS /root/putcafe/api/        docker compose: db (postgres:17, volume) +
                              positions + bot — one shared stack for all slots
```

`site.caddy` gains the two `reverse_proxy` matchers. Containers bind
127.0.0.1 only; db has no host port. One API stack serves prod/staging/preview
frontends (single-user MVP; revisit per-env stacks later).

## Positions-backend (owns Postgres)

Tables `sessions` (config + running state: quote_balance, base_qty, avg_entry,
fees_paid, status active|finished) and `trades` (time, side, price, base_qty,
quote_amount, fee). Endpoints under `/api/positions`:

- `POST /sessions` create (market, interval, startTime, endTime, mode, algo,
  algoConfig, startingBalance, feesEnabled)
- `GET /sessions` list · `GET /sessions/:id` (with trades) ·
  `DELETE /sessions/:id`
- `GET /sessions/:id/state` → balances/position/lastTradeTime
- `POST /sessions/:id/orders` `{time, side:"buy", quoteAmount, price}` —
  simulated market fill: when feesEnabled, fee = 0.1 % taker + 0.05 % slippage
  on price; rejects on insufficient balance; updates avg entry; persists trade
- `POST /sessions/:id/finish` · `GET /health`

## Bot-backend (decisions; ML later)

In-memory session store (support data = full seeded history + config); the DB
truth lives in positions. Endpoints under `/api/bot`:

- `POST /sessions/:id/seed` `{algo, config, candles[]}` (full history up to
  session start — "knowledge at that point in time")
- `POST /sessions/:id/step` `{candle}` → appends to history, fetches
  `…/state` from positions (`POSITIONS_URL` inside compose), runs the algo →
  `{decisions:[{side:"buy", type:"market", quoteAmount}]}`. Unknown session →
  409 `not_seeded`; the frontend re-seeds and retries (bot restarts are cheap).
- **DCA** (buy-only): config `{quoteAmount, frequencySec}` — buy on first step,
  then whenever `candle.time − lastTradeTime ≥ frequencySec`.
- `POST /sessions/:id/run` `{candles[]}` — **headless batch**: the whole range
  in one call. The bot loops in Python, tracks `lastTradeTime` locally (no
  per-candle positions GET), and hits positions only on fills, over the
  in-cluster network. Collapses the frontend's thousands of public round-trips
  into one. Replay still uses per-candle `step` (user-paced).

The replay step protocol sends **only the new candle** (PRD §6).

## Frontend

- `api/backend.ts` — typed clients; base URL from `VITE_API_BASE`
  (`frontend/.env`, the putcafe host).
- `binance/api.ts` — add `fetchKlinesRange(symbol, interval, startMs, endMs)`
  (forward pagination, 1000/page).
- `backtest/engine.ts` — one engine, two modes. State machine mirrors SC:
  `idle|loading|ready|playing|paused|finished`. Step = advance idx → bot step →
  post each decision as an order → fill ⇒ **significant event** (anything
  changing the position) ⇒ pause unless auto-resume. Play loop at speed
  *candles/sec*, options `1 2 5 10 20 100` (Altrady's set, capped at 100);
  ≥100 batches steps per tick. `stepBack` re-renders one candle fewer
  (orders are never undone — documented). Headless: same loop, no per-step
  render, progress callback, then viewport → backtest range + markers.
- `components/BacktestPanel.tsx` — header-toggled side panel: algo dropdown
  (DCA), amount + frequency, starting balance (1000), fees toggle, mode
  (replay/headless), **Start/End Candle picker fields** (quiz-style: field arms
  selection → click the chart picks the candle; Escape cancels; active-field
  styling), Start/Stop, results block (balance, qty, avg entry, unrealized
  PnL, fees, ROI), sessions list (load a finished session back onto the chart).
- `components/PlaybackControls.tsx` — Altrady-style bottom strip, replay only:
  status badge · ⏮⏮ restart · ⏮ step back · ▶/⏸ · ⏭ step · ⏹ stop ·
  speed select · auto-resume toggle (Altrady's label) · current candle time.
  Shortcuts: Shift+↓ play/pause, Shift+→/← step, Shift+R restart, Shift+Q stop.
- `components/ChartContextMenu.tsx` — right-click on chart: "Set backtest
  start here", "Set backtest end here", "Start replay here"
  (`coordinateToTime`).
- `chart/RangeHighlight.ts` — series primitive: shaded region + two labeled
  vertical lines ("Backtest start/end") for the selected range.
- `chart/ChartView.tsx` — session mode props (candles, upTo, trades): skips
  Binance fetching/lazy-load, incremental `series.update` per step,
  `setData(slice)` on jumps; trade markers via `createSeriesMarkers`
  (arrowUp belowBar, "B <amt>").

## Deploy & scripts

- `backend/` in the monorepo (compose.yml, positions/, bot/, Dockerfiles).
- `scripts/dev/remote/edge/setup-api.sh` — idempotent: install Docker
  (get.docker.com) + compose plugin if absent.
- `scripts/dev/local/edge/deploy-api.sh` — rsync `backend/` →
  `/root/putcafe/api/`, run setup-api, `docker compose up -d --build`, curl
  `/health` of both services via the public URL.
- `site.caddy` updated; `setup.sh` re-run applies it (validate + reload).
- `ci.yml`: new `api` job — push to `main` only: rsync + compose build
  (idempotent; Docker layer cache on the box keeps it fast).

## Out of scope (unchanged from PRD)

Sells, more algos, auth, per-env API stacks, Android.
