# Overview widgets — PRD

**ID:** `pc-overview-widgets` · **Branch:** `feature/overview-widgets` ·
**Worktree:** `~/git/worktrees/putcafe/overview-widgets`

## Problem

Backtest/replay state is scattered: the open position and results live as
stat lines in the Backtest sidebar, sessions are a sidebar list, and orders
don't exist as a first-class concept at all — the pivot sim only returns
*trades*, so the entry stop that was armed, the TP/SL bracket orders, and the
market close on a reverse are invisible as orders, both in any table and
(partially) on the chart.

## Goal

A separate **overview widget below the chart** (spanning the full width up to
the Backtest sidebar) with three tabs:

1. **Positions** — the (max 1) maintained position: side, size, entry, mark
   price, SL/TP, unrealized PnL + %. Pivot algo → the trade open at the replay
   cursor; DCA → the accumulated spot position of the active/loaded session.
2. **Orders** — *all* order types with an **Open / Closed** filter:
   - entry orders (pivot: stop-market breakout entries; DCA: market buys),
   - exit orders (market close on a reverse),
   - conditional orders (TP limit + SL stop placed at entry).
   Closed = filled + cancelled (status column distinguishes).
3. **Sessions** — the persisted sessions list, moved here from the sidebar.

All of these orders must also **render on the chart**: pending-at-cursor
orders as price lines (armed entry stops, the open position's TP/SL bracket +
entry), fills as the existing trade markers. UI/UX + label formatting roughly
follows Altrady (TV-era 5.3 implementation as reference) — e.g. a TP line
label includes the % — without going out of our way (lightweight-charts price
lines, not TV-style interactive order boxes).

Everything is **synced to the replay cursor** (no lookahead: an order appears
when created, shows "open" until its fill/cancel candle passes) and works for
replay, headless results, and loaded sessions.

## Requirements

- R1: Bot sim (`/api/bot/simulate`) returns an **orders ledger** alongside
  trades — single source of truth, frontend derives nothing strategy-side.
- R2: Orders ledger covers: armed entry stops (incl. ones cancelled when a
  newer pivot superseded them or the opposite side filled), TP/SL conditional
  orders, reverse market exits. Each order: role, type, side, price, qty, %
  (tp/sl), createdAt, status, filledAt/fillPrice, cancelledAt, trade link.
- R3: Overview widget below the chart, full width until the sidebar; tabs
  Positions / Orders / Sessions; Orders tab has Open|Closed filter.
- R4: Cursor clipping everywhere: tables and chart show order/position state
  as of the replay cursor; step-back re-clips (render-only, like trades).
- R5: Chart renders pending orders as labelled price lines (Altrady-ish
  formats: `TP 0.0013 BTC +1.79%`, `SL …`, `Buy stop …`); fills stay as
  markers. DCA buys remain markers (no resting orders in DCA).
- R6: Sessions section is removed from the Backtest sidebar (now in widget).
- R7: Altrady reference colors for order lines: buy/TP-side `#43B581`,
  sell/SL-side `#F15959` (chart candles/markers keep the putcafe palette).

## Non-goals

- No interactive order management (cancel/move from chart or table).
- No real resting orders / futures backend (`pc-futures-orders` effort).
- No TV-style order boxes with close buttons; price lines suffice.
- No persistence of pivot-sim orders (stateless sim remains stateless).

## References

- Altrady TV impl (backup checkout, branch `release-5.3.x`):
  `src/containers/trade/trading-terminal/widgets/center-view/tradingview/orders.js`,
  `widgets/my-orders.js`, `widgets/positions/position-row.js`.
- Discussion: `~/ai/putcafe/discussions/2026-06-12-pivot-trading-strategy.md`.
