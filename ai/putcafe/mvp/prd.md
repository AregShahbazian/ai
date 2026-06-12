---
id: pc-mvp
---

# Putcafe — MVP (backtesting & replay)

Builds on the bare slice ([`../bare/prd.md`](../bare/prd.md)): putcafe becomes a
crypto trading bot **simulation and backtesting** app. Web-only. Binance spot
only, real historical data, fictional balances, no API keys. Deployment is in
[`../devops/prd.md`](../devops/prd.md).

## Requirements

### 1. Backtest sessions

- A session = market + timeframe + date range + algorithm config + starting
  balance (fictional, editable at start, default **1000 USDT**).
- **Date range selection on the chart**, UI modeled on Altrady's quiz
  start/end-date selection.
- Two session modes:
  - **Replay** — user-controlled playback, candle by candle. An
    **auto-resume** option; when off, any **significant event** (anything that
    changes the position — mirror Altrady's smart-backtest logic) pauses
    playback. Playback controls visible.
  - **Headless** — the full range plays out automatically without rendering
    each step or listening to playback input. Playback controls hidden. On
    completion the chart viewport moves to the backtest range (start visible;
    end included, or as much as fits zoomed out).
- Sessions and their outcomes **persist in a DB** and survive reload.

### 2. Replay playback UI

Mimic Altrady's replay controls as closely as possible — same elements, same
feeling: the playback buttons panel, the chart right-click context menu entries,
and the chart header buttons. Reference implementations: **Superchart**
(`~/git/altrady/Superchart`) and **cbs_desktop** branch
`feature/superchart-integration`; port the logic — never import the code.

### 3. Algorithms

- Dashboard dropdown of algorithms; MVP ships **DCA only** (buy-only).
- Selecting an algorithm shows its minimal config (e.g. frequency, amount).
- Example flow that must work: DCA buying 10 USDT weekly, headless over 20
  weeks, 1000 USDT start.

### 4. Trading simulation

- Orders fill against the current candle's data; **fees (and slippage)
  simulated, toggleable in the UI**.
- Buy-only for MVP: the session ends holding its position; PnL is unrealized.

### 5. Results

- Trades rendered as chart overlays (markers at fill price/time).
- Final position and PnL data visible in the UI (panel/summary).

### 6. Backends & protocol

- **Two backends.** A **bot-backend** (decisions; will host AI/ML later — Python)
  and a **positions-backend** (sessions, positions, trades, balances — owns the
  DB).
- Per-candle step protocol (simple JSON, order shape borrowed from Binance):
  1. Frontend → bot-backend: the **new candle only**.
  2. Bot-backend → positions-backend: fetch current position/balance.
  3. Bot-backend returns decisions to the frontend.
  4. Frontend → positions-backend: post orders; it simulates fills, persists,
     returns the updated position/balance.
- **Support data:** full candle history is seeded to the bot-backend at session
  start; it stores history + analyses per market/session. The backend only ever
  knows data up to the session's current point in time.

## Constraints (decided in discussion)

- Monorepo: frontend (React+TS+Vite, Lightweight Charts), positions-backend
  (Node/TS), bot-backend (Python/FastAPI).
- Protocol must stay transport-simple so backends can be swapped/evolved.

## Non-requirements

- No live trading, no API keys, no real funds, no accounts/auth.
- No sell logic, no algorithms beyond DCA, no exchanges beyond Binance.
- No Android yet (future; don't block a Capacitor wrap).
- No indicator/drawing tooling beyond what replay needs.
