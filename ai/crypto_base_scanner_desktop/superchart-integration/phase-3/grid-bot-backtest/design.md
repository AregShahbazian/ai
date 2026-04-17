# Design: Grid Bot Backtest — SuperChart Integration

## Key Design Decisions

### 1. Dual-chart layout — side by side

Desktop: the chart area (`flex-1` in the existing `flex-row`) is split into TV (left) and SC (right), each `flex-1` in a nested `flex-row`:

```jsx
<div tw="flex-1 flex flex-row">
  <div tw="flex-1 min-w-0">
    <GridBotTradingWidget .../>
  </div>
  <div tw="flex-1 min-w-0">
    <GridBotSuperChartWidget .../>
  </div>
</div>
```

`min-w-0` prevents flex children from overflowing. The `w-1/3` sidebar stays unchanged.

Mobile: same side-by-side split in the toggle-to-show chart container.

### 2. Backtest time markers — reuse `_createTriggerTimeLine`

The controller already has `_createTriggerTimeLine(group, key, timestamp, {lock, ...callbacks})` which creates a `verticalStraightLine` with `triggerPrice` color. Entry conditions use it with `lock: false` + `onPressedMoveEnd`.

New controller method `createBacktestTimeLine(key, timestamp, onUpdate)`:
- Delegates to `_createTriggerTimeLine` with `lock: false`
- `onPressedMoveEnd` reads `event.overlay.points[0].timestamp` and calls `onUpdate(new Date(timestamp))`
- Controller owns the timestamp conversion (ms → Date) and the i18n label (future, when SC supports text on time lines)
- Registers in `OverlayGroups.backtestTimes`

### 3. BacktestTimes overlay component

Standard `useDrawOverlayEffect` pattern. Receives `backtest` prop (`{startTime, endTime, updateStartTime, updateEndTime}`). Converts `startTime`/`endTime` (Date objects) to ms timestamps for the controller.

Deps: `startTime?.getTime()`, `endTime?.getTime()` — primitive values to detect Date changes.

### 4. Conditional rendering in GridBotSuperChartWidget

`BacktestTimes` only renders when `backtest` prop is provided:

```jsx
{props.backtest && <BacktestTimes backtest={props.backtest}/>}
```

No overlay drawn when `backtest` is undefined (grid bot overview/settings).

## Data Flow

```
backtest-content.js
  ├── GridBotTradingWidget (TV) — existing, with backtest prop
  └── GridBotSuperChartWidget (SC) — with backtest prop
        ├── GridBotPrices (upper/lower draggable)
        ├── GridBotOrders (order level lines)
        ├── Trades (backtest result trades)
        └── BacktestTimes (start/end draggable time lines)
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `super-chart/overlays/grid-bot/backtest-times.js` | Backtest start/end time markers overlay component |

### Modified files

| File | Changes |
|---|---|
| `super-chart/chart-controller.js` | Add `createBacktestTimeLine(key, timestamp, onUpdate)` |
| `super-chart/overlay-helpers.js` | Add `backtestTimes` to `OverlayGroups` |
| `super-chart/grid-bot-super-chart.js` | Accept `backtest` prop, conditionally render `BacktestTimes` |
| `backtest-content.js` | Add SC next to TV, pass all props |
| `backtest-content-mobile-form.js` | Add SC next to TV, pass props (no backtest time markers on mobile) |
