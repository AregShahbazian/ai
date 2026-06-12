# Futures order protocol — Tasks

**ID:** `pc-futures-orders` · refs [`design.md`](design.md)

Order matters: the Python correctness gate (T1–T3) is the crux and must pass
before the frontend/DB are touched.

- [ ] **T1 Engine** — `bot/app/futures.py`: hedge-mode isolated-margin matching
      engine, order-action driven (place/cancel/amend), resting orders, OHLC
      no-lookahead matching, deterministic conflict rule, per-side liquidation,
      events. Mechanics moved verbatim from `pivot_strategy` so numbers hold.
- [ ] **T2 Algos** — `bot/app/algos/{pivot,dca}.py` + `Algo`/`StepContext`/
      `Action` types. Pivot ports 1:1 (armed stops, bracket, reverse); DCA emits
      periodic market longs.
- [ ] **T3 Parity gate** — script diffs new engine vs current `simulate` on both
      saved BTCUSDT 1h files; trades/reasons/pnl/liq/orders match within float
      tol. DCA accumulation verified. (Blocks the rest.)
- [ ] **T4 Bot API** — `POST /api/bot/futures/run` returns the snapshot; remove
      `/simulate`, `/sessions/*/seed|step|run`. Keep `/analyze`.
- [ ] **T5 Persistence** — positions-backend: `futures_sessions` schema +
      create-from-run / list / get / finish / delete; drop spot tables &
      endpoints.
- [ ] **T6 Frontend types+engine** — `api/backend.ts` futures types; collapse
      `engine.ts` to one run-once + reveal-by-cursor path for all algos; delete
      DCA per-candle + seed/step/run/reseed.
- [ ] **T7 Frontend UI** — OverviewWidget per-side positions + liq; ChartView
      order-line labels (side/type/liq) + per-side entry lines; BacktestPanel
      DCA vs pivot params unchanged.
- [ ] **T8 Build + verify** — `tsc -b` + `vite build` clean; bot run locally;
      end-to-end smoke (pivot + DCA, replay + headless + reload).
- [ ] **T9 Review** — `review.md`, parity evidence, deferred notes; commit,
      push branch (preview), report with test steps.
