# Overview widgets — Tasks

**ID:** `pc-overview-widgets` · refs `design.md`

- [ ] T1 Backend: orders ledger in `pivot_strategy.simulate` (armed stops,
      entry fills, bracket, reverse exits, end-of-range open) + invariants
      verified against the saved BTCUSDT range over real HTTP.
- [ ] T2 Types: `PivotOrder`, `PivotSimResult.orders` in `api/backend.ts`;
      `util/orders.ts` (orderStatusAt / ordersAt / dcaOrders).
- [ ] T3 Widget: `components/OverviewWidget.tsx` — tabs Positions / Orders
      (Open|Closed filter) / Sessions; css.
- [ ] T4 Sidebar: remove Sessions from `BacktestPanel.tsx` (state + props).
- [ ] T5 Chart: orders effect in `ChartView.tsx` — pending stops + bracket
      lines with qty/% labels, Altrady colors; drop old bracket effect.
- [ ] T6 App wiring; `tsc -b` + `vite build` clean.
- [ ] T7 Commit, push branch (preview deploy), report with test steps.
