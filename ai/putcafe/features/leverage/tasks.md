# Leverage — Tasks

Design: [`design.md`](design.md). Branch `feature/leverage` in worktree
`~/git/worktrees/putcafe/leverage`; commits tagged `[pc-leverage]` (left
uncommitted for user testing).

## 1. Bot: margin/leverage/liquidation in the sim

- `backend/bot/app/pivot_strategy.py` — margin/notional split, liq price on
  open, effective-stop resolution (SL vs liq vs reverse), `pnl ≥ −margin`
  clamp, bankruptcy guard + `bust`, trade fields `liqPrice`/`notional`/
  `margin`, result fields `leverage`/`bust`.
- `backend/bot/app/main.py` — `StrategyParams.leverage` (int, 1–125, default 1).
- Verify: standalone script over synthetic candles — ×1 reproduces old
  numbers; ×10 multiplies PnL ×10 (minus fee scaling); a forced deep adverse
  candle liquidates with `pnl == −margin`; SL > liq% ⇒ reason `liq`;
  equity < margin ⇒ no further entries, `bust`.

## 2. Frontend: types + plumbing

- `src/api/backend.ts` — `PivotParams.leverage`; `PivotTrade.liqPrice/
  notional/margin`, `"liq"` reason; `PivotSimResult.leverage/bust`.
- `src/backtest/engine.ts` — fallback params `leverage: 1`.
- `src/App.tsx` — default config, `setPivotParams` effect, `startSession`,
  preset-load merge over `DEFAULT_CONFIG`.
- Verify: `tsc -b` clean.

## 3. Frontend: picker + results + chart

- `src/components/BacktestPanel.tsx` — leverage slider (steps ×1–×125) in the
  pivot section, live-tunable; results row `Leverage` + bust note.
- `src/chart/ChartView.tsx` — `LIQ` exit marker (orange circle); `Liq` price
  line for the cursor-open trade at leverage > 1.
- Verify: picker re-runs the sim mid-replay; ×1 chart identical to before;
  high leverage shows liq line + LIQ exits; old preset loads as ×1; new
  preset round-trips leverage.

## 4. Build + review

- `tsc -b && vite build` clean; backend `python -m compileall` (or import
  check); write `review.md`; leave uncommitted; report deploy status
  (frontend hot-reload, bot needs VPS deploy via CI on push).
