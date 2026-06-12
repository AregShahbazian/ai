# Pivot detection — Tasks

Design: [`design.md`](design.md). Branch `feature/pivot-detection` in its own
worktree; commits tagged `[pc-pivots]` (left uncommitted for user testing).

## 1. Bot: detector

- `backend/bot/app/pivots.py` — `detect(candles, lookback, alternation)` per
  design (raw symmetric-window pass + alternation collapse, `confirmedAt`).
- Verify: run the detector standalone over
  `~/Downloads/temp/candles_BTCUSDT_1h_07-06-2026-2200_12-06-2026-0200.json`;
  with `lookback=3` all 8 candles from
  `saved-candles_12-06-2026-1932.json` must appear, alternating high/low.

## 2. Bot: API surface

- `backend/bot/app/main.py` — `PivotOptions` model; seed stores options;
  pivots in `seed`/`step`/`run` responses; `PUT /sessions/{id}/options`;
  `POST /analyze`.
- Verify: `uvicorn app.main:app --port 8102`, curl `/api/bot/analyze` with the
  exported candle file → expected pivots; seed + step + options flow by hand.

## 3. Frontend: API + options persistence

- `src/api/backend.ts` — types + `bot.setOptions` / `bot.analyze`, seed body
  `options`, response types.
- `src/util/pivotOptions.ts` — `usePivotOptions()` (localStorage).
- Verify: `tsc -b` clean.

## 4. Frontend: engine

- `src/backtest/engine.ts` — snapshot `pivots`, options at `start`/re-seed,
  fold pivots from seed/step/run, `setPivotOptions` (live PUT with 409
  re-seed; analyze on loaded views), `loadSession` analyze.
- Verify: `tsc -b` clean; replay session shows pivots growing as candles play.

## 5. Frontend: UI + chart

- `src/components/BacktestPanel.tsx` — Pivots block (enabled during replay).
- `src/App.tsx` — wire options/hook, `SessionView.pivots`.
- `src/chart/ChartView.tsx` — merged, sorted, `confirmedAt`-clipped markers.
- Verify: triangles above highs / below lows; step back hides late pivots;
  toggling alternation mid-replay updates markers; headless + loaded sessions
  show pivots.

## 6. Dev proxy

- `frontend/vite.config.ts` — `VITE_LOCAL_BOT=1` proxy per design.
- Verify: `VITE_LOCAL_BOT=1 yarn dev` + local uvicorn → bot calls hit
  localhost, positions calls hit the deployed API.
