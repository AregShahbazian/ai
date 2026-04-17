# Phase 5: Replay Overlays — Design

## Overview

Three types of changes:
1. **Conditional rendering** in `super-chart.js` — hide/show overlays based on `replayMode`
2. **Data source switching** in Trades, BreakEven, PnlHandle — read from replay state when active
3. **New component** ReplayTimelines — three vertical `timeLine` overlays

Bases already has replay filtering (reads `replayTime` from ReplayContext, filters by it). No changes needed.

---

## Conditional Rendering

`SuperChartWidgetWithProvider` reads `replayMode` from Redux and conditionally mounts overlays. Since `SuperChartWidgetWithProvider` is the top-level component (outside `SuperChartContext`), the `replayMode` selector needs `marketTabId` from `MarketTabContext` (already available).

Since `useSelector` can't be called in `SuperChartWidgetWithProvider` before the providers are set up, extract the overlay section into a child component:

```jsx
const SuperChartOverlays = () => {
  const {id: marketTabId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(marketTabId))

  return <>
    {/* Always mounted */}
    <Trades/>
    <Bases/>
    <BreakEven/>
    <PnlHandle/>
    <PriceTimeSelect/>
    <Screenshot/>

    {/* Hidden during replay */}
    {!replayMode && <>
      <BidAsk/>
      <PriceAlerts/> <EditPriceAlert/> <TriggeredPriceAlerts/>
      <TimeAlerts/> <EditTimeAlert/> <TriggeredTimeAlerts/>
      <TrendlineAlerts/> <EditTrendlineAlert/> <TriggeredTrendlineAlerts/>
      <Orders/> <EditOrders/>
      <OverlayContextMenu/>
    </>}

    {/* Replay-only */}
    {replayMode && <ReplayTimelines/>}
  </>
}
```

---

## Trades — Data Source Switching

Current SC Trades reads live trades from `marketTabDataContext.marketTradingInfo?.trades`.

Add replay awareness:
```js
const {id: chartId} = useContext(MarketTabContext)
const replayMode = useSelector(selectReplayMode(chartId))
const replayTrading = useSelector(selectReplayTrading(chartId))

const allTrades = useMemo(() => {
  if (replayMode) return replayTrading.trades
  // existing live trades logic
}, [replayMode, replayTrading.trades, ...existingDeps])
```

Time filtering: in replay mode, skip the visible range filter — show all replay trades
(they're already bounded by replay time). In live mode, keep the existing visible range filter.

---

## BreakEven — Data Source Switching

Current SC BreakEven reads from `CurrentPositionContext.currentPosition`.

Add replay awareness:
```js
const {id: chartId} = useContext(MarketTabContext)
const replayMode = useSelector(selectReplayMode(chartId))
const replayTrading = useSelector(selectReplayTrading(chartId))

const position = replayMode ? replayTrading.currentPosition : currentPosition
```

Pass `position` to the controller method instead of `currentPosition`. No controller changes needed — it draws whatever position it receives.

---

## PnlHandle — Data Source Switching + Disable Interactivity

Same data switching as BreakEven:
```js
const position = replayMode ? replayTrading.currentPosition : currentPosition
```

Disable interactivity during replay:
- Close button callback: skip or pass null when `replayMode`
- Position refresh: skip when `replayMode`
- The controller method likely accepts callbacks for close/refresh — pass undefined during replay

---

## ReplayTimelines — New Component

**File:** `super-chart/overlays/replay-timelines.js`

```js
const ReplayTimelines = () => {
  const {chartController} = useSuperChart()
  const {id: chartId} = useContext(MarketTabContext)
  const session = useSelector(selectReplaySession(chartId))
  const {startTime, endTime, time, status} = session || {}

  useDrawOverlayEffect(OverlayGroups.replayTimelines, () => {
    chartController.createReplayTimelines({startTime, endTime, currentTime: time, status})
  }, [startTime, endTime, time, status])

  return null
}
```

**Controller method** on ChartController:

```js
createReplayTimelines({startTime, endTime, currentTime, status}) {
  const chart = this._superchart.getChart()
  const colors = this.colors

  if (startTime) {
    this._createOverlay({...}, OverlayGroups.replayTimelines, "start")
    // timeLine overlay at startTime with colors.replayStartTime, label "Start At"
  }
  if (endTime) {
    this._createOverlay({...}, OverlayGroups.replayTimelines, "end")
    // timeLine overlay at endTime with colors.replayEndTime, label "End At"
  }
  if (currentTime && status !== "ready" && status !== "finished") {
    this._createOverlay({...}, OverlayGroups.replayTimelines, "current")
    // timeLine overlay at currentTime with colors.replayCurrentTime, label "Now At"
  }
}
```

**Colors:** Already defined in `src/themes/index.js`:
```js
replayCurrentTime: "rgba(250, 175, 49, 0.5)"    // orange
replayStartTime: "rgba(55, 203, 149, 0.2)"      // green
replayEndTime: "rgba(241, 89, 89, 0.2)"         // red
```

These need to be added to SC's `chartColors` mapping (in `use-chart-colors.js` or
equivalent) so they're accessible via `this.colors.replayStartTime`.

**OverlayGroups:** Add `replayTimelines: "replayTimelines"` to `overlay-helpers.js`.

---

## Bases — No Changes Needed

Already reads `replayTime` from `ReplayContext` and filters bases by it:
```js
const {time: replayTime} = useContext(ReplayContext)
// ...
(!replayMode || util.toSafeDate(formedAt).valueOf() < util.toSafeDate(replayTime).valueOf())
```

SC's `ReplayContext` now provides `time` from Redux session. This already works.
