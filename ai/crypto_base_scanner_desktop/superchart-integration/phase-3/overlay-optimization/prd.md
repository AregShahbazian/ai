# Overlay Optimization — PRD

## Goal

Assess and improve the SuperChart overlay components (bid-ask, break-even, trades, bases, pnl-handle) across two dimensions:

### 1. Rendering Efficiency

Evaluate redraw/rerender behavior. Identify unnecessary re-renders, overly broad Redux selectors, stale closures, and inefficient clear+redraw patterns. Where possible, prefer in-place updates over full redraws.

### 2. Code Patterns & Architecture

Assess whether logic lives in the right place. Identify duplicated patterns across overlays that should be extracted into shared hooks or moved to the chart controller. Ensure consistent use of existing utilities (e.g. `util.useImmutableCallback`).

## Scope

Files under `src/containers/trade/trading-terminal/widgets/super-chart/`:
- `overlays/bid-ask.js`
- `overlays/break-even.js`
- `overlays/trades.js`
- `overlays/bases.js`
- `overlays/pnl-handle.js`
- `chart-controller.js`
- `context.js`
