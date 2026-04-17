# Review: Grid Bot Backtest — SuperChart Integration

## Step 1: Dual-chart layout in backtest modal

### Round 1 bugs

#### Bug 1: Price handles duplicate after drag
**Root cause:** `updateOrCreate*` methods had an "update" path (`_updateGridBotHandle` → `setPrice`) that was dead code — `useDrawOverlayEffect` always clears the group before drawing, so the update path never triggered. The create path always ran, but `clearOverlays` → `line.remove()` may not have fully removed old handles.
**Fix:** Removed `updateOrCreate` pattern entirely. Renamed to plain `create*` methods. `useDrawOverlayEffect` clears, then creates fresh — no ambiguity.

### Verification
1. ✅ Desktop: TV (left) and SC (right) side by side in backtest modal, sidebar on the right
2. ✅ Mobile: toggle "Show Chart" — both charts visible side by side
3. ✅ SC shows candles, order lines, price handles, trades (when backtest result exists)
4. ✅ Change market in picker — both charts update
5. ✅ Drag upper/lower price handles in SC — no duplication, form updates correctly
6. ✅ Price handles in SC sync with TV when changed via form inputs

### Round 1 bugs

#### Bug 1: Ghost TP/SL handles on backtest chart + overlays disappear on resize
**Root cause:** Superchart uses a global singleton store (`chartStore.ts`). Two SC instances share `instanceApi`, `symbol`, `period`, etc. The second instance overwrites the first. `createOrderLine(chartA, ...)` internally uses `store.instanceApi()` which returns chartB — overlays from the settings chart render on the backtest chart. Reported to SC dev with reproduction story (`API/MultiChart`).
**Workaround:** Unmount settings SC chart when backtest modal is open. `isBacktestOpen` lifted to `GridBotSettings` via `BotFormContext`. Marked with `// WORKAROUND` comments for easy removal once SC supports multi-instance.

### Workaround verification
7. ✅ No ghost TP/SL handles appearing on backtest SC chart
8. ✅ Resize / mobile↔desktop toggle — backtest SC retains overlays
9. ✅ Close backtest modal — settings SC remounts with correct overlays

## Step 2: Backtest time markers overlay

### Verification
1. ✅ Desktop: two vertical time lines on SC matching TV positions (triggerPrice color)
2. ✅ Drag start time line in SC → date picker updates
3. ✅ Drag end time line in SC → date picker updates
4. ✅ Change date in picker → SC time lines reposition
5. ✅ Change date in picker → TV time lines also reposition (existing behavior)
6. ✅ Mobile: no time markers (no `backtest` prop passed)
7. ✅ Grid bot overview/settings: no time markers (no `backtest` prop)
