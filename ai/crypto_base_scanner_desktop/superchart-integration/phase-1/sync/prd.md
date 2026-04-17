# PRD: Phase 1 — Bidirectional Symbol/Period Sync

## Goal

Wire the two SuperChart event callbacks (`onSymbolChange`, `onPeriodChange`) so that:

1. **Chart -> App**: When the user changes symbol or period in SuperChart's UI, the
   MarketTab state updates (same as TradingView does today).
2. **App -> Chart**: When the MarketTab state changes externally (tab switch, market
   click, URL navigation), SuperChart updates (already partially done, needs review).

The end result: SuperChart and TradingView behave identically from the MarketTab's
perspective for symbol and period. A user switching between the two widgets sees the
same sync behavior.

> **Note**: Visible range syncing is covered in a separate PRD:
> `ai/superchart-integration/phase-1/sync-visible-range/prd.md`

## Background

The SuperChart library now exposes these methods on the `Superchart` instance:

```javascript
// Subscribe — returns unsubscribe function
const unsub = chart.onSymbolChange((symbol: SymbolInfo) => { ... })
const unsub = chart.onPeriodChange((period: Period) => { ... })

// Constructor callbacks also work:
new Superchart({ onSymbolChange, onPeriodChange, ... })
```

See `ai/deps/SUPERCHART_API.md` and `ai/deps/SUPERCHART_USAGE.md` for full API docs.

## Current State

`super-chart.js` currently has App -> Chart sync via `useEffect` hooks:

- `[coinraySymbol]` effect calls `chartRef.current.setSymbol(toSymbolInfo(coinraySymbol))`
- `[resolution]` effect calls `chartRef.current.setPeriod(toPeriod(resolution))`

There is **no** Chart -> App sync. Changes made in SuperChart's UI (period bar clicks,
symbol search if it exists) are not propagated back to the MarketTab.

## How TradingView Does It (Reference)

### Symbol: Chart -> App

1. TV fires `chart.onSymbolChanged()` with `{ticker}`
2. `useTradingView.js:204` — `handleSymbolChanged` updates the datafeed GUID and calls
   `handleTVSymbolChanged(ticker)`
3. `tradingview.js:57` — callback calls
   `TradingTabsController.get()?.activeTab.setCoinraySymbol(coinraySymbol)`
4. `TradingTab.setCoinraySymbol` updates state, symbol history, calls `openMarket()`,
   saves to Redux

### Period: Chart -> App

1. TV fires `chart.onIntervalChanged()` with interval string (e.g. `"60"`)
2. `useTradingView.js:214` — `handleIntervalChanged` updates datafeed GUID, tracks
   `nextResolution`/`currentResolution` for `readyToDraw` gating, calls
   `handleTVIntervalChanged(interval)`
3. `tradingview.js:61` — callback calls
   `TradingTabsController.get().getTabById(marketTabId).setResolution(interval)`
4. `MarketTab.setResolution` updates state and saves to Redux

## Implementation Plan

### 1. Symbol sync: Chart -> App

Subscribe to `onSymbolChange` after chart init. When fired:

- Extract `coinraySymbol` from `SymbolInfo.ticker`
- Guard: skip if `ticker === currentMarketRef.coinraySymbol` (avoid echo from App -> Chart
  -> App loops)
- Call `TradingTabsController.get()?.activeTab.setCoinraySymbol(coinraySymbol)`

**Echo prevention**: The App -> Chart `[coinraySymbol]` effect calls `setSymbol()`, which
may fire `onSymbolChange`. The guard check prevents the callback from writing back the
same symbol. TradingView has the same guard (`useTradingView.js:209`).

### 2. Period sync: Chart -> App

Subscribe to `onPeriodChange` after chart init. When fired:

- Convert `Period` to TV resolution string via `periodToResolution(period)`
- Guard: skip if resolution matches current `marketTabResolution`
- Call `TradingTabsController.get().getTabById(marketTabId).setResolution(resolution)`

**Echo prevention**: Same pattern — the `[resolution]` effect calls `setPeriod()`, which
may fire `onPeriodChange`. The guard prevents write-back of the same value.

### 3. Review App -> Chart sync (existing effects)

The existing `[coinraySymbol]` and `[resolution]` effects need minor hardening:

- **Skip initial render**: Both effects fire on mount with the constructor's values. The
  chart is already initialized with those values — calling `setSymbol`/`setPeriod` again
  is redundant. Use a `mountedRef` pattern (like TV does at `useTradingView.js:434`) to
  skip the first render.
- **Null safety**: Already handled (`if (!chartRef.current) return`), keep as-is.

## Files

- Modify: `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`
  - Subscribe to `onSymbolChange`, `onPeriodChange`
  - Add echo-prevention guards
  - Add `mountedRef` to skip initial effect fires

No new files needed.

## Constraints

- **No changes to SuperChart library.** The three callbacks are already shipped.
- **No changes to TradingView integration.** TV chart must remain fully functional.
- **No changes to MarketTab / TradingTabsController.** Use existing APIs exactly as TV does.
- **No `readyToDraw` changes.** The existing `readyToDraw` gating in `context.js` is
  sufficient. The sync callbacks don't depend on overlay readiness.

## Out of Scope

- Symbol search UI within SuperChart (SuperChart may or may not have this — either way,
  `onSymbolChange` handles it generically)
- Visible range syncing (`onVisibleRangeChange`, `setVisibleRange`) — separate PRD
- `onTimezoneChange` (Phase 4)
- Locked tab behavior (`marketTabIsLocked`) — TV has special handling for locked tabs in
  `useTradingView.js:52`. SuperChart doesn't have a symbol search UI that could conflict
  with locked tabs. If needed later, add the guard then.
- `coinraySymbolOverride` prop (used by grid bot chart) — Phase 9
- Replay mode interaction with period/symbol changes — Phase 5
- `currentResolution`/`nextResolution` tracking for `readyToDraw` — TV uses this to gate
  overlays during period transitions. SuperChart's `readyToDraw` is simpler (just
  `getChart() !== null`). If overlays flicker during period changes, revisit then.

## Testing Steps

1. Open Trading Terminal with SuperChart widget visible
2. **Period sync (Chart -> App)**: Click a different period in SuperChart's period bar.
   Verify the MarketTab's resolution updates (check Redux state or observe that reopening
   the same tab preserves the new period).
3. **Period sync (App -> Chart)**: Switch to a different trading tab and back. Verify
   SuperChart shows the correct period for each tab.
4. **Symbol sync (Chart -> App)**: If SuperChart has a symbol search, use it. Otherwise,
   this direction is tested implicitly — the callback is wired but won't fire until
   SuperChart adds symbol search UI.
5. **Symbol sync (App -> Chart)**: Click a different market in the market list. Verify
   SuperChart loads the new symbol's candles.
6. **No echo loops**: Change period in SuperChart's UI. Verify no console errors, no
   infinite re-renders, no double state updates. Period should change exactly once.
7. **TV still works**: Verify the TradingView chart (CenterView) continues to function
   identically — symbol/period sync all work as before.

## Apply Steps

1. No SuperChart rebuild needed (library unchanged)
2. Webpack dev server HMR should pick up the changes to `super-chart.js`
3. If HMR doesn't work, restart `yarn start-web`
