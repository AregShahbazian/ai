# Tasks: Trendline Alerts — SuperChart Integration

## Task 1: Add chart-controller methods

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**
- Add `createTrendlineAlert(group, key, points, callbacks)` method
  - Uses `chart.createOverlay({name: "segment", ...})`
  - `lock: false`, spreads `...callbacks`
  - `points` is array of two `{timestamp, value}` objects (component converts from TV format)
  - Registers under `group` param with `key`
- Add `createTriggeredTrendlineAlert(key, points)` method
  - Same `segment` overlay, `lock: true`, no callbacks
  - Registers under `"triggeredTrendlineAlerts"` group

Place after the Time Alerts section (after `createTriggeredTimeAlert`).

**Verify:** Methods exist, no syntax errors. Follows `createTimeAlert` / `createTriggeredTimeAlert` structure.

## Task 2: Create `trendline-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/trendline-alerts.js` (new)

**Changes:**
- Renders pending trendline alerts (not triggered, not editing)
- Filter `marketTradingInfo.alerts` by `alertType === "trend_line"`, exclude `alertsFormId`
- Extract points via `getAlertData()` (handles `data.data.points` legacy path)
- Convert TV points `{time, price}` → SC points `{timestamp, value}` via `toScPoints()`
- `onPressedMoveEnd` callback:
  - Extract `event.overlay.points`, convert back via `toTvPoints()`
  - Calculate `priceAtTime` via `util.priceAtTime(tvPoints, Date.now() / 1000)`
  - Calculate `direction` via comparison with `currentMarket.getMarket().lastPrice`
  - Dispatch `editAlert({...alert, direction, data: {..., points, priceAtTime, direction}})`
- Uses `useSuperChart()`, `useSymbolChangeCleanup`, `util.useImmutableCallback`
- Clears via `chartController.clearOverlays("trendlineAlerts")`

**Verify:**
1. Open chart with pending trendline alerts — segment lines appear between correct points
2. Click a line → enters edit mode (alert form opens with correct direction)
3. Switch symbols — lines clear and redraw
4. Toggle `alertsShow` off — lines disappear

## Task 3: Create `edit-trendline-alert.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/edit-trendline-alert.js` (new)

**Changes:**
- Renders the currently-editing trendline alert (one at a time)
- Gated on `alertsForm.isEditing && alert.alertType === "trend_line"` and `alertsShow`
- `onPressedMoveEnd` callback:
  - Same conversion + direction logic as task 2
  - Additionally sets `price: newTvPoints[0].price` on the dispatched alert
  - Dispatches `editAlert()` (updates form only, does NOT submit)
- Duplicates `getAlertData`, `toScPoints`, `toTvPoints` locally
- Clears via `chartController.clearOverlays("editTrendlineAlert")`

**Verify:**
1. Edit a trendline alert → segment line appears at alert's points
2. Drag an endpoint → points update in alert form (check form reflects new values)
3. Drag the line body → both points translate, form updates
4. When not editing → no line rendered

## Task 4: Create `triggered-trendline-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/triggered-trendline-alerts.js` (new)

**Changes:**
- Renders triggered trendline alerts
- Filter `marketTradingInfo.triggeredAlerts` by `alertType === "trend_line"`
- Extract points via `getAlertData()`, convert via `toScPoints()`
- `lock: true` — no interaction callbacks
- Gated on `alertsShow` AND `alertsShowClosed`
- Clears via `chartController.clearOverlays("triggeredTrendlineAlerts")`

**Verify:**
1. Toggle `alertsShowClosed` on → triggered trendline alert lines appear
2. Toggle off → lines disappear
3. Lines are not draggable or clickable
4. Switch symbols → lines clear and redraw

## Task 5: Wire into `super-chart.js`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

**Changes:**
- Import `TrendlineAlerts` from `./overlays/trendline-alerts`
- Import `EditTrendlineAlert` from `./overlays/edit-trendline-alert`
- Import `TriggeredTrendlineAlerts` from `./overlays/triggered-trendline-alerts`
- Render `<TrendlineAlerts/>`, `<EditTrendlineAlert/>`, `<TriggeredTrendlineAlerts/>` alongside existing overlays

**Verify:**
1. All three trendline alert overlay types render on SC chart
2. No duplicate alerts (editing alert is filtered from pending list)
3. All overlay lifecycle works: symbol change cleanup, readyToDraw gating
