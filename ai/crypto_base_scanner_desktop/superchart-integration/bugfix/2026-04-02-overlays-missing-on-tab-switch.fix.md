# Overlays missing after switching market tabs

**Date:** 2026-04-02
**Branch:** feature/superchart-integration
**Status:** fixed

## Symptoms
Switching between market tabs in TT caused most overlays to disappear. Only self-updating overlays (bidAsk, trades) survived. One-shot overlays (alerts, trendlines, bases, breakEven, pnl, orders) were missing. Reloading the page on the same market showed all overlays correctly.

Additionally, the old market's overlays briefly flashed on the new market's chart before disappearing.

## Diagnosis
Added diagnostic `console.log` calls to the overlay lifecycle:
- `useDrawOverlayEffect` — logged group name, `readyToDraw`, `hasController`, and current symbol on every effect run, clear, and draw
- `useSymbolChangeCleanup` — logged subscribe/unsubscribe/fire events with label and symbol
- `ChartController` — logged `syncSymbolToChart` entry, `setSymbol` call, `clearOverlays` (group + count), and `_register` (group/key)

Logs revealed that after switching tabs, every overlay effect fired with `hasController=false` for the new symbol. No `[overlay:...] draw` entries appeared — the `if (!chartController) return` guard blocked all draws. The `clear()` calls from `useSymbolChangeCleanup` were also no-ops since `chartController` was `undefined`. This pointed to the `ChartRegistry` lookup returning `null` for the new `marketTabId`.

## Cause
Two issues:

1. **ChartRegistry lookup miss.** `ChartController` was registered in `ChartRegistry` under the initial `marketTabId` (in a mount-only `useEffect([], [])`). When switching tabs, `marketTabId` changed, but the registry entry was never updated. The context's `chartController` getter (`ChartRegistry.get(chartId)`) returned `null` for the new ID, so every overlay effect hit the `if (!chartController) return` guard — nothing drew, nothing cleared.

2. **Old overlays flash.** `syncSymbolToChart` called `setSymbol` without clearing existing overlays first. The old market's overlays remained on the chart until React cleanup effects ran (next frame), causing a brief visual flash.

## Solutions Tried
Added diagnostic logs to `useDrawOverlayEffect`, `useSymbolChangeCleanup`, `clearOverlays`, `_register`, and `syncSymbolToChart`. Logs confirmed `hasController=false` for every overlay effect after tab switch.

## Final Solution
1. **Re-register controller on tab switch.** In the `marketTabId` sync effect in `super-chart.js`, unregister the old ID and register the new one in `ChartRegistry`. Also fixed the unmount cleanup to use the controller's current `_marketTabId` instead of the stale closure value.

2. **Clear overlays immediately on symbol change.** Added a loop in `syncSymbolToChart` that clears all overlay groups before calling `setSymbol`, preventing the old-market flash.

## Edited Files
- src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js
- src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js
