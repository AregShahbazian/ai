# Bare MVP — Review

PRD: [`prd.md`](prd.md) (`pc-bare`)

## Round 1: initial implementation (2026-06-12)

Implemented per [`design.md`](design.md)/[`tasks.md`](tasks.md). Stack as
designed; lockfile resolved lightweight-charts **5.2.0**. Switched to **yarn**
(repo preference, `~/ai/putcafe/workflow.md`). `yarn build` (strict tsc + vite)
passes — that covers items 1–2 below; the rest is manual.

### Verification

1. ✅ `yarn install` clean (agent-verified)
2. ✅ `yarn build` passes — strict TypeScript + production bundle (agent-verified)
3. ✅ App loads at `http://localhost:5173`: dark layout, header (title, market
   selector, timeframe buttons), chart fills the rest of the window
4. ✅ Default view: BTC/USDT 1h candles + volume histogram at the bottom
5. ✅ Legend shows OHLCV of the last candle; moving the crosshair updates it;
   leaving the chart falls back to the last candle
6. ✅ Pan/zoom is smooth; scrolling left keeps loading older history without a
   hard edge (watch the network tab: repeated `klines` calls with `endTime`)
7. ✅ Market selector: opens with search focused, filters as you type (e.g.
   "SOL"), Enter picks the top hit, outside click / Escape closes; selecting
   reloads the chart and the button label updates
8. ✅ Timeframe buttons: each of `1m 5m 15m 1h 4h 1d 1w` reloads the chart;
   market is preserved; selected button highlighted
9. ✅ Loading overlay appears briefly on every market/interval switch
10. ✅ Error state: with network offline (devtools), switching market shows the
    error + Retry; Retry recovers once back online
