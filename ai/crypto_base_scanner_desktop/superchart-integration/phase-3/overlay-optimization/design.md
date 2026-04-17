# Overlay Optimization — Design

## New Files

### `src/.../super-chart/hooks/use-chart-colors.js`
- Hook returning memoized `chartColors` (theme.chart merged with chartSettings.chartColors[themeName])
- Selector targets `state.chartSettings.chartColors` not full `state.chartSettings` — toggle changes won't trigger re-renders
- Replaces identical pattern duplicated in all 5 overlays

### `src/.../super-chart/hooks/use-symbol-change-cleanup.js`
- `useSymbolChangeCleanup(currentMarket, cleanup)` — wraps cleanup in `util.useImmutableCallback` internally
- Replaces duplicated subscribe/unsubscribe pattern in break-even, trades, bases (3 files)
- bid-ask keeps its own (combines symbol change + state reset + market subscription)
- pnl-handle keeps its own (combines symbol change + needsRefresh registration)

## Modified Files

### All 5 overlays — common changes:
- Replace `chartColors` useMemo + ThemeContext + chartSettings selector → `useChartColors()`
- Replace `useSelector(state => state.chartSettings)` with field-specific selectors
- Switch clear callbacks from `useCallback` to `util.useImmutableCallback` (fixes stale closures, reduces effect re-runs)

### `bid-ask.js`
- Selector: `useSelector(state => state.chartSettings.miscShowOrderBookAskBid)`
- `clear` → `useImmutableCallback`

### `break-even.js`
- Selector: `useSelector(state => state.chartSettings.miscShowBreakEvenPoint)`
- `clearBreakEvenLine` → `useImmutableCallback` (fixes stale closure in `[]` subscription effect)
- Use `useSymbolChangeCleanup` hook
- Draw effect deps: `[readyToDraw, breakEvenPoint, miscShowBreakEvenPoint, chartColors]` (drop `chartSettings`)

### `trades.js`
- Selector: single selector with `shallowEqual` for 7 closedOrders* fields
- `clear` and `draw` → `useImmutableCallback` (eliminates `visibleTrades` from clear's deps, massive dep array from draw)
- Use `useSymbolChangeCleanup` hook

### `bases.js`
- Selector: single selector with `shallowEqual` for 5 bases* fields
- Use `useSymbolChangeCleanup` hook
- Filter effect deps: replace `chartSettings` with specific fields
- Draw effect deps: replace `chartSettings` with `basesShow, basesShowBox`
- O(n²) fix: build `Set(filteredBases.map(b => b.id))` before `.filter()`, use `.has()` instead of `.find()`

### `pnl-handle.js`
- Selector: `shallowEqual` selector for `positionsShowPnl`, `positionsEnableCanceling`
- `clearPnlLine` → `useImmutableCallback` (fixes stale closure in `[]` subscription effect)
- Draw effect deps: replace `chartSettings` with `chartColors`

## Verification
```
npx webpack --config webpack.dev-web.config.js --mode development
```
