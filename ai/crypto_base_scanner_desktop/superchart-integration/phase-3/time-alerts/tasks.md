# Tasks: Time Alerts — SuperChart Integration

## Task 1: Add chart-controller methods

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**
- Add `createTimeAlert(group, key, timestamp, {color, text, ...callbacks})` method
  - Uses `chart.createOverlay({name: "verticalStraightLine", ...})`
  - `lock: false`, line solid width 1
  - Spreads `...callbacks` (component decides `onClick` vs `onPressedMoveEnd`)
  - `text` accepted but not forwarded yet (T1)
  - Registers under `group` param with `key`
- Add `createTriggeredTimeAlert(key, timestamp, {color, text})` method
  - Same `verticalStraightLine` overlay
  - `lock: true` — no callbacks, display only
  - Registers under `"triggeredTimeAlerts"` group

**Verify:** Methods exist, no syntax errors. No import needed — uses `chart.createOverlay()` directly.

## Task 2: Create `time-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/time-alerts.js` (new)

**Changes:**
- Renders pending time alerts (not triggered, not editing)
- Filter `marketTradingInfo.alerts` by `alertType === "time"`, exclude `alertsFormId`
- Extract time via `getAlertTime()` (handles `data.data.time` legacy path)
- Convert to ms: `new Date(time).getTime()`
- Build label text via `buildTimeAlertLabel()` (passed to controller but unused until T1)
- `onClick` callback: extract `event.overlay.points[0].timestamp`, convert to UTC string, dispatch `editAlert()`
- Uses `useSuperChart()`, `useSymbolChangeCleanup`, `util.useImmutableCallback`
- Clears via `chartController.clearOverlays("timeAlerts")`

**Verify:**
1. Open chart with pending time alerts — vertical lines appear at correct timestamps
2. Click a line → enters edit mode (alert form opens with correct time)
3. Switch symbols — lines clear and redraw
4. Toggle `alertsShow` off — lines disappear

## Task 3: Create `edit-time-alert.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/edit-time-alert.js` (new)

**Changes:**
- Renders the currently-editing time alert (one at a time)
- Gated on `alertsForm.isEditing && alert.alertType === "time"` and `alertsShow`
- `onPressedMoveEnd` callback: extract `event.overlay.points[0].timestamp`, convert to UTC string, dispatch `editAlert()` (updates form only, does NOT submit)
- Build label text via `buildEditingTimeAlertLabel()` (unused until T1)
- Clears via `chartController.clearOverlays("editTimeAlert")`

**Verify:**
1. Edit a time alert → vertical line appears at alert's time
2. Drag line → time updates in alert form (check form reflects new time)
3. Line uses `chartColors.alert` color (not closedAlert)
4. When not editing → no line rendered

## Task 4: Create `triggered-time-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/triggered-time-alerts.js` (new)

**Changes:**
- Renders triggered time alerts
- Filter `marketTradingInfo.triggeredAlerts` by `alertType === "time"`
- Extract time via `getAlertTime()`, convert to ms
- `lock: true` — no interaction callbacks
- Color: `chartColors.closedAlert`
- Gated on `alertsShow` AND `alertsShowClosed`
- Clears via `chartController.clearOverlays("triggeredTimeAlerts")`

**Verify:**
1. Toggle `alertsShowClosed` on → triggered time alert lines appear with darker blue
2. Toggle off → lines disappear
3. Lines are not draggable or clickable
4. Switch symbols → lines clear and redraw

## Task 5: Wire into `super-chart.js`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

**Changes:**
- Import `TimeAlerts` from `./overlays/time-alerts`
- Import `EditTimeAlert` from `./overlays/edit-time-alert`
- Import `TriggeredTimeAlerts` from `./overlays/triggered-time-alerts`
- Render `<TimeAlerts/>`, `<EditTimeAlert/>`, `<TriggeredTimeAlerts/>` alongside existing overlays

**Verify:**
1. All three time alert overlay types render on SC chart
2. No duplicate alerts (editing alert is filtered from pending list)
3. All overlay lifecycle works: symbol change cleanup, readyToDraw gating
