# Overview widgets — Review

## Round 0: implementation verification (2026-06-12)

Branch `feature/overview-widgets` (worktree
`~/git/worktrees/putcafe/overview-widgets`), commit `b4f8528`, tag
`[pc-overview-widgets]`. Web preview + api stack deployed:
https://putcafe.46-250-232-224.sslip.io/web/overview-widgets/

Files: `backend/bot/app/pivot_strategy.py`,
`frontend/src/{api/backend.ts, util/orders.ts (new),
components/OverviewWidget.tsx (new), components/BacktestPanel.tsx,
chart/ChartView.tsx, App.tsx, app.css}`.

### Verification

1. ✅ Ledger invariants on both saved BTCUSDT 1h ranges (116 + 101 candles,
   direct module call): each closed trade has exactly one filled entry and
   one filled tp/sl/exit order with fill price/time equal to the trade's;
   bracket legs cancelled exactly at exit; pct reconstructs the order price
   to 1e-9; no order resolved before created; only entry stops left
   unlinked (claude-verified).
2. ✅ `/api/bot/simulate` over HTTP (local :8109 + deployed) returns
   `orders`; armed sell stop showed `createdAt` 2 candles before its
   `filledAt`, fill below stop (slippage), TP `pct: -8.0` (claude-verified).
3. ✅ `tsc -b && vite build` clean (claude-verified).
4. Widget: Positions tab shows the open position at the cursor (side, size,
   entry, mark, SL, TP, PnL, PnL %); flat → "No open position".
5. Orders tab: Open filter shows armed stops while flat / the bracket while
   in position; Closed shows filled + cancelled with status colors; TP/SL
   rows carry the % in the type label; DCA runs list their market buys.
6. Sessions tab: list + Clear sessions moved from the sidebar; clicking a
   row loads the session; sidebar no longer has a Sessions section.
7. Chart: while flat, dashed Buy/Sell stop lines at the armed pivot levels
   (green `#43B581` / red `#F15959`); in position, entry line
   `Long <qty> BTC @ <px>` + `TP <qty> BTC +x.xx%` / `SL <qty> BTC −x.xx%`.
8. Sync: step-back re-clips tables and lines (orders re-open, fills
   disappear); live-tuning TP/SL ratio mid-replay updates ledger + lines +
   tables together.
9. Playback strip still sits on the chart's bottom edge (not on the widget).

### Notes / deferred

- DCA position row has no SL/TP (spot, no brackets) — shown as "—".
- Pivot sims remain unpersisted: the Sessions tab only lists
  positions-backend (DCA) sessions, as before.
- `sim.orders ?? []` guards a deployed bot that predates the ledger.
- Reverse entries materialize their stop order on the reversal candle
  (created+filled same time) — there's no pre-armed reverse stop, by design
  (matches the strategy's close-then-reverse semantics).
