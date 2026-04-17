# Tasks: PnL Handle — SuperChart Integration

## Task 1: Rewrite `createPnlHandle` in chart-controller.js

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**
- Replace chained-setter `createPnlHandle` with options-object version
- Add `onCancel` to the method signature (passed through to `createOrderLine` options)
- Set `align: "left"`, `editable: false`, `lineColor: "transparent"`
- Set body/quantity background and border to `this.colors.grid`
- Use `quantityTextColor` instead of old `setQuantityColor`

**Verify:** Method compiles, no other callers besides `pnl-handle.js`.

## Task 2: Rewrite `pnl-handle.js` component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/pnl-handle.js`

**Changes:**
- Import `useSymbolChangeCleanup` hook
- Replace `clearPnlLine` with `util.useImmutableCallback` pattern
- Replace manual `subscribeCoinraySymbolWillChange` / `unsubscribeCoinraySymbolWillChange` with `useSymbolChangeCleanup(currentMarket, clearPnlLine)`
- Build `onCancel` as `{params: {}, callback: fn}` before calling `createPnlHandle`
- Pass `onCancel` to `createPnlHandle` in the options object
- Remove post-creation `orderLine.onCancel(...)` wiring
- Keep `needsRefreshPositionOnMarketUpdates` wiring in a separate `useEffect` (PnL-specific)
- Keep position refresh logic unchanged

**Verify:**
1. Open a chart with an open position — PnL handle appears left-aligned at open price
2. Body shows PnL in currency, quantity shows PnL percentage
3. Toggle `positionsShowPnl` off — handle disappears
4. Toggle `positionsEnableCanceling` — cancel button appears/disappears
5. Switch symbols — handle clears and redraws for new position
6. With `hideAmounts` on — body shows `****`
