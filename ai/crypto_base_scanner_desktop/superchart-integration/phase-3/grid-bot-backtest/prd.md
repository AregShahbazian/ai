---
id: sc-grid-bot-backtest
---

# PRD: Grid Bot Backtest — SuperChart Integration

## Overview

Reimplement the grid bot backtest chart for SuperChart and add a dual-chart comparison layout. The backtest chart is rendered inside a modal (`BacktestModal`) on a separate screen from the grid bot details page. It shares the same `GridBotTradingWidget` as the regular grid bot chart but adds backtest-specific overlays: draggable start/end time markers and a right-click context menu for setting backtest boundaries.

This PRD covers:
1. **Dual-chart layout** — render SC next to TV in the backtest modal for comparison
2. **Backtest time markers** — draggable vertical lines for start/end times

## Current Behavior (TradingView)

### Backtest modal layout

The backtest opens as a modal with responsive layout:

**Desktop** (`backtest-content.js`):
- Left: chart (`flex-1`) — `GridBotTradingWidget` with full overlays + backtest time markers
- Right: sidebar (`w-1/3`) — form inputs (market, dates, prices, orders, investment) + results

**Mobile** (`backtest-content-mobile.js` → `backtest-content-mobile-form.js`):
- Tab switcher: Form | Results
- Chart hidden by default, toggled via "Show Chart" button
- Chart rendered **without** `backtest` prop (no time markers on mobile)

### Chart overlays in backtest mode

The `GridBotTradingWidget` renders these overlays in backtest:

| Overlay | Present | Notes |
|---|---|---|
| Grid bot orders | Yes | Calculated order levels from form |
| Grid bot prices | Yes | Upper/lower draggable, no SL/TP (not passed) |
| Trades | Yes | `backtestResult.trades` when result available, empty array otherwise |
| Backtest times | Yes (desktop only) | Two draggable vertical time lines |
| Alerts | Yes (TV-internal) | Read-only (`noEdit`), unintended — will be removed with TV |
| PriceTimeSelect | Yes | Crosshair tracking for click-to-select-price — SC version exists but not yet wired to grid bot charts |

### BacktestTimes component (`backtest-times.js`)

Renders two `TimeAlert` child components, each creating a draggable vertical time line:

| Marker | Label | Color | Draggable | Callback |
|---|---|---|---|---|
| Start time | "Backtest Start" | `chartColors.entryCondition` (triggerPrice) | Yes | `updateStartTime(new Date(points[0].time * 1000))` |
| End time | "Backtest End" | `chartColors.entryCondition` (triggerPrice) | Yes | `updateEndTime(new Date(points[0].time * 1000))` |

Each marker uses `chartFunctions.drawTimeLine("entryCondition", unixTimestamp, options)` with:
- `timeFormat: "DD MMM 'YY HH:mm"` — date/time label on the line
- `label` — "Backtest Start" or "Backtest End"
- `withText: true` — shows the label text
- `allowMove: true` — draggable

On drag completion (`onSelect`), the new time is read from the shape's points and passed to `updateStartTime` / `updateEndTime`.

Delete is prevented (`onDelete` → `stopPropagation` + `preventDefault`).

### Context menu (desktop only)

`backtest-content.js` passes `onContextMenu` to `GridBotTradingWidget`:
```
onContextMenu={({time}) => [
  {position: "top", text: "Set Backtest Start", click: () => updateStartTime(new Date(time * 1000))},
  {position: "top", text: "Set Backtest End", click: () => updateEndTime(new Date(time * 1000))},
]}
```

This adds two items to the TV chart's right-click context menu.

### Symbol change handling (desktop only)

`backtest-content.js` passes `handleTVSymbolChanged` — when the user changes the symbol via the TV chart's built-in symbol search, it updates the backtest form's market. Mobile form also supports this.

### Props comparison: backtest vs regular grid bot chart

| Prop | Grid bot overview | Grid bot settings | Backtest |
|---|---|---|---|
| `orders` | Yes (from bot session) | Yes (from form) | Yes (from form) |
| `trades` | Yes (from bot session) | No | Yes (from backtest result) |
| `upperPrice` | Yes | Yes | Yes |
| `lowerPrice` | Yes | Yes | Yes |
| `updateUpperPrice` | No | Yes | Yes |
| `updateLowerPrice` | No | Yes | Yes |
| `stopLoss` | Yes | Yes | No |
| `takeProfit` | Yes | Yes | No |
| `updateStopLoss` | No | Yes | No |
| `updateTakeProfit` | No | Yes | No |
| `edited` | Yes (always true) | Yes (from form) | Yes (always true) |
| `backtest` | No | No | Yes (`{startTime, endTime, updateStartTime, updateEndTime}`) |
| `onContextMenu` | No | No | Yes (set start/end) |
| `handleTVSymbolChanged` | No | No | Yes |
| `visible` | Default | Mobile: conditional | Always true |

## Requirements

### R1 — Dual-chart layout in backtest modal

Add SuperChart **next to** TradingView in the backtest chart area. The chart space currently used by TV alone is split equally between TV (left) and SC (right). This is a **temporary comparison layout** — once overlays are verified, TV will be removed.

- **Desktop**: TV and SC side by side in the left chart area (each `flex-1` in a `flex-row`), sidebar stays on the right
- **Mobile**: TV and SC side by side in the toggle-to-show chart area
- Both charts receive the same `coinraySymbol`
- SC uses the same `GridBotSuperChartWidget` from `sc-grid-bot`

### R2 — Backtest time markers overlay (SuperChart)

Render two draggable vertical time lines on SuperChart. Reuse `_createTriggerTimeLine` from the chart controller (same method used by entry conditions/expirations in `sc-orders`), with `lock: false` and `onPressedMoveEnd`.

| Marker | Label | Color | Draggable | Callback |
|---|---|---|---|---|
| Start time | "Backtest Start" | `chartColors.triggerPrice` | Yes (`lock: false`) | `onPressedMoveEnd` → `updateStartTime` |
| End time | "Backtest End" | `chartColors.triggerPrice` | Yes (`lock: false`) | `onPressedMoveEnd` → `updateEndTime` |

- Only rendered when `backtest` prop is provided (desktop mode)
- Delete is not supported — lines cannot be removed by the user
- Uses `useDrawOverlayEffect` with `OverlayGroups.backtestTimes` group
- Controller method: `createBacktestTimeLine(timestamp, label, onUpdate)` — delegates to `_createTriggerTimeLine` with `lock: false` and `onPressedMoveEnd` that converts the new timestamp and calls `onUpdate`. Label and timestamp conversion are the controller's responsibility.
- The new price from drag comes from `event.overlay.points[0].timestamp` (same pattern as editing entry conditions)

### R3 — Grid bot overlays in backtest

The backtest chart reuses the same grid bot overlays from `sc-grid-bot`:

- **Grid bot prices**: upper/lower draggable (callbacks provided), no SL/TP (not passed)
- **Grid bot orders**: horizontal lines for calculated order levels
- **Trades**: simulated trade markers from backtest result

No additional overlay work needed — these are the same components already wired in `GridBotSuperChartWidget`.

### R4 — Backtest-specific props on GridBotSuperChartWidget

Extend `GridBotSuperChartWidget` (from `sc-grid-bot`) to accept:

| Prop | Type | Description |
|---|---|---|
| `backtest` | `{startTime, endTime, updateStartTime, updateEndTime}` | Enables backtest time markers |

When `backtest` is provided, the widget renders the `BacktestTimes` overlay component inside the `SuperChartContextProvider`.

### R5 — Symbol change handling

The backtest form's market picker updates `coinraySymbol`, which is passed as a prop to `GridBotSuperChartWidget`. The widget already syncs prop changes to the chart via `superchart.setSymbol()` — no additional work needed.

TV also supports `handleTVSymbolChanged` (symbol change from the TV chart's built-in search updates the form). SC doesn't have a built-in symbol search yet — when it does, the same wiring pattern applies.

## Data Sources

### Backtest time markers
| Prop | Type | Source |
|---|---|---|
| `startTime` | Date | `backtestForm.current.startTime` |
| `endTime` | Date | `backtestForm.current.endTime` |
| `updateStartTime` | `fn(Date)` | `backtestForm.current.updateStartTime` |
| `updateEndTime` | `fn(Date)` | `backtestForm.current.updateEndTime` |

### Backtest trades
| Prop | Type | Source |
|---|---|---|
| `trades` | array | `backtestResult.trades` (from Redux `state.backtest.loadedBacktest`) |

### Colors
| Key | Used for |
|---|---|
| `chartColors.triggerPrice` | Backtest time markers |

## File Structure

```
super-chart/
  overlays/
    grid-bot/
      backtest-times.js               # Backtest start/end time markers overlay component
```

## Incremental Implementation Plan

### Step 1: Dual-chart layout in backtest modal

Add `GridBotSuperChartWidget` next to TV in `backtest-content.js` and `backtest-content-mobile-form.js`. Split chart area 50/50 side by side. Pass all existing grid bot props (orders, trades, prices, callbacks). Verify both charts load and display candles.

**Files:** `backtest-content.js`, `backtest-content-mobile-form.js`

### Step 2: Backtest time markers overlay

Implement the two draggable time lines on SuperChart. Add `createBacktestTimeLine` to controller (delegates to `_createTriggerTimeLine`). Add `BacktestTimes` overlay component. Wire into `GridBotSuperChartWidget` when `backtest` prop is provided. Verify drag updates the form's start/end time. Verify lines reposition when dates are changed via the date pickers.

**Files:** `overlays/grid-bot/backtest-times.js`, `chart-controller.js`, `overlay-helpers.js`, `grid-bot-super-chart.js`

### Step 3: Remove TV from backtest (future — not part of this PRD)

Once overlays are verified, remove TV and give SC the full chart area. This is a separate task after review.

## Non-Requirements

- No changes to Redux state, backtest form, or backtest API
- No context menu — SC doesn't support it yet. Backtest items ("Set Backtest Start/End") tracked in Phase 4 (`INTEGRATION.md` §4a)
- No symbol change from SC chart UI — SC doesn't have built-in symbol search yet. Form market picker works via prop sync.
- No mobile backtest time markers (TV doesn't have them on mobile either)
- No storybook stories — time lines are already proved via entry conditions
- No backtest result table/list changes — only chart overlays
- No alerts on the backtest chart (or any grid bot chart) — TV currently renders `<Alerts noEdit>` but this is unintended; it will be removed when TV is removed
- No PriceTimeSelect on grid bot SC charts — SC component exists but wiring to grid bot is pending
- No removal of TV — that happens after review
