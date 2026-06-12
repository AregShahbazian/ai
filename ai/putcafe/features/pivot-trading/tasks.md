# Pivot trading — Tasks

Design: [`design.md`](design.md). Branch `feature/pivot-trading` in worktree
`~/git/worktrees/putcafe/pivot-trading`; commits tagged `[pc-pivot-trading]`
(left uncommitted for user testing).

## 1. Bot: strategy simulator

- `backend/bot/app/pivot_strategy.py` — `simulate(candles, pivot_options,
  params)`: pivot detection (alternation on), candle-path state machine
  (breakout entry, capped opposite-pivot bracket, close+reverse, re-arm on
  fresh pivot), fees/slippage, returns trades + equity/wins/losses.
- Verify: standalone over an exported BTCUSDT 1h file — sane trades, brackets
  obey ratio, PnL adds up, single position invariant holds.

## 2. Bot: API

- `backend/bot/app/main.py` — `StrategyParams`, `SimulateBody`,
  `POST /api/bot/simulate`.
- Verify: `uvicorn app.main:app --port 8102`; curl `/api/bot/simulate` with the
  candle file → expected trades JSON.

## 3. Frontend: API + types

- `src/api/backend.ts` — `algo: "dca"|"pivot"`, `PivotParams`, `PivotTrade`,
  `PivotSimResult`, `bot.simulate`.
- Verify: `tsc -b` clean.

## 4. Frontend: engine

- `src/backtest/engine.ts` — `pivotSim` in snapshot; pivot branch in `start`
  (simulate once, no positions/seed); replay via `upTo` + significant-on-trade;
  `setPivotParams`/`setPivotOptions` re-run sim mid-replay.
- Verify: `tsc -b`; replay reveals entries/exits as candles play, headless jumps
  to final.

## 5. Frontend: UI + chart

- `src/App.tsx` — algo + pivot-params state, config builder, thread `pivotSim`.
- `src/components/BacktestPanel.tsx` — Pivot in algo select; ratio / SL cap /
  position-size inputs; pivot results block.
- `src/chart/ChartView.tsx` — entry/exit markers + bracket price lines for the
  cursor-open trade, clipped to the cursor.
- Verify: replay shows breakout entries, bracket lines track the open position,
  exits mark TP/SL/reverse; tweaking ratio/SL-cap mid-replay re-runs; headless
  result renders.

## 6. Build + review

- `tsc -b && vite build` clean; write `review.md`; leave uncommitted, hand the
  user test steps (local bot via `VITE_LOCAL_BOT=1`).
