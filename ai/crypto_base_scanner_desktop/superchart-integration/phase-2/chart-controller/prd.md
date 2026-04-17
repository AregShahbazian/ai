# PRD: Phase 2 — ChartController + SuperChartContext

## Goal

Introduce the foundational layer that all overlay components will depend on. By the end of
this phase, the superchart widget exposes a stable imperative handle (`ChartController`) and
a React context (`SuperChartContext`) so that future overlay components can access the chart
without prop-drilling or re-render issues.

No overlays are built in this phase — just the infrastructure they'll plug into.

## Done Looks Like

- `ChartController` is created on mount, holds references to `superchart` and `datafeed`
- `SuperChartContext` is provided to children of the widget
- `readyToDraw` is exposed via context, gated on `getChart() !== null`
- `super-chart.js` remains the main widget component — unchanged externally
- Context provider is a separate component in `context.js`, wrapping the widget
- Existing behavior (symbol/resolution/theme/resize sync) still works
- TV chart widget and all its existing functionality keeps working

## Files

- New: `super-chart/chart-controller.js`
- New: `super-chart/context.js` — context, provider component, `useSuperChart()` hook
- Modify: `super-chart/super-chart.js` — minimal changes to wire up ChartController

## Constraints

- `ChartController` is a plain JS object, not a React component or hook
- `SuperChartContext` provides `chartController` as a stable ref (no re-renders on chart ops)
- Reactive state (`readyToDraw`, etc.) is separate from the imperative controller ref
- Do NOT replicate TV's hook structure (`useTradingView`, `useTradingViewMarket`, etc.)
- Do NOT add convenience methods to `ChartController` upfront — add them as overlays need them
- TV chart widget must remain fully functional throughout

## Out of Scope

- Any overlay components
- Replay / quiz mode switching (`setMode`, `drawCandle`)
- `ChartRegistry` for multi-chart access (Phase 9)
- Persistence / StorageAdapter (Phase 6)
- `chartSettings` Redux integration (later)
