# Design: Time Alerts — SuperChart Integration

## Approach

Five files change:

1. **`chart-controller.js`** — add `createTimeAlert` (pending + editing) and `createTriggeredTimeAlert` methods
2. **`overlays/time-alerts.js`** — new overlay component for pending time alerts
3. **`overlays/edit-time-alert.js`** — new overlay component for editing time alert
4. **`overlays/triggered-time-alerts.js`** — new overlay component for triggered time alerts
5. **`super-chart.js`** — wire all three components

The TV implementation bundles pending + triggered into one `TimeAlert` component in `alerts.js`. For SC, each gets its own overlay file (matching the price alerts pattern: `price-alerts.js`, `edit-price-alert.js`, `triggered-price-alerts.js`).

## Time Format Conversion (R6)

### Conversion chain

```
alert.data.time (or alert.data.data.time)   →   UTC string   e.g. "Thu, 20 Mar 2026 14:00:00 GMT"
  ↓ new Date(time).getTime()
milliseconds (epoch ms)                      →   number       e.g. 1774051200000
  ↓ passed directly to createTimeAlertLine
SC overlay point                             →   {timestamp: ms, value: 0}
```

### Callback chain (editing — `onPressedMoveEnd`)

```
SC callback event                            →   event.overlay.points[0].timestamp   (epoch ms)
  ↓ new Date(ms).toUTCString()
UTC string                                   →   "Thu, 20 Mar 2026 14:00:00 GMT"
  ↓ dispatch(editAlert({...alert, data: {..., time: utcString}}))
Redux alert form                             →   alert.data.time updated
```

### Callback chain (pending — `onClick`)

Same as editing callback chain. The `onClick` event gives access to the overlay's current point timestamp.

### Key difference from TV

TV uses **seconds** (`new Date(time).getTime() / 1000`) and converts back (`points[0].time * 1000`). SC uses **milliseconds** natively. No division/multiplication needed — just `new Date(time).getTime()` in and `new Date(ms).toUTCString()` out.

## Time Extraction Helper

TV's `alerts.js` and `edit-alerts.js` both extract time the same way:

```js
const {data} = alert
const {time} = data.data || data || {}
```

This handles both `alert.data.time` and the legacy `alert.data.data.time` path. We replicate this as a shared helper in the chart-controller or as a local function.

```js
function getAlertTime(alert) {
  const {data} = alert
  const {time} = data?.data || data || {}
  return time
}
```

## Chart Controller — `createTimeAlert`

### Pending + Editing (single method)

Unlike price alerts (where submitted and editing have very different visuals — body/quantity/cancel button), pending and editing time alerts are visually identical: same vertical line, same color, same style, `lock: false`. Only the callbacks differ. A single `createTimeAlert` method handles both — the component decides which callbacks to pass.

```js
createTimeAlert(group, key, timestamp, {color, text, ...callbacks}) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "verticalStraightLine",
    points: [{timestamp, value: 0}],
    styles: {
      line: {color, size: 1, style: "solid"},
    },
    lock: false,
    ...callbacks,
  })
  if (id) this._register(group, key, id)
  return id
}
```

Key decisions:
- `group` parameter — component passes `"timeAlerts"` for pending, `"editTimeAlert"` for editing
- `lock: false` — both pending and editing are interactive
- `...callbacks` — spread allows any combination of `onClick`, `onPressedMoveEnd`, etc.
- `text` accepted but not passed through yet (T1 — label not rendering)
- Color passed from component

Usage from components:
- **Pending**: `createTimeAlert("timeAlerts", key, ts, {color, text, onClick: ...})`
- **Editing**: `createTimeAlert("editTimeAlert", "time", ts, {color, text, onPressedMoveEnd: ...})`

### Triggered alert

```js
createTriggeredTimeAlert(key, timestamp, {color, text}) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "verticalStraightLine",
    points: [{timestamp, value: 0}],
    styles: {
      line: {color, size: 1, style: "solid"},
    },
    lock: true,
  })
  if (id) this._register("triggeredTimeAlerts", key, id)
  return id
}
```

Key decisions:
- `lock: true` — not interactive
- No callbacks — display only
- Registered under `"triggeredTimeAlerts"` group (separate lifecycle)
- Color: `chartColors.closedAlert`

## Component — `time-alerts.js`

Renders pending time alerts. Follows `price-alerts.js` pattern.

### Data flow

```
MarketTabDataContext.marketTradingInfo.alerts → filter(alertType === "time") → getAlertTime() → createTimeAlert()
```

### Structure

```js
function getAlertTime(alert) {
  const {data} = alert
  const {time} = data?.data || data || {}
  return time
}

const TimeAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const alertsShow = useSelector(state => state.chartSettings.alertsShow)
  const alertsFormId = useSelector(state => state.alertsForm.alert.id)
  const dispatch = useDispatch()

  const clearAlerts = util.useImmutableCallback(() => {
    chartController?.clearOverlays("timeAlerts")
  })
  useSymbolChangeCleanup(currentMarket, clearAlerts)

  useEffect(() => {
    clearAlerts()
    if (!readyToDraw) return
    if (!alertsShow) return

    const {alerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO

    alerts
      .filter(a => a.alertType === "time" && a.id !== alertsFormId)
      .forEach(alert => {
        const time = getAlertTime(alert)
        if (!time) return
        const timestamp = new Date(time).getTime()
        const text = buildTimeAlertLabel(alert)  // built but unused until T1
        chartController.createTimeAlert("timeAlerts", `time-${alert.id}`, timestamp, {
          color: chartColors.alert,
          text,
          onClick: {params: {}, callback: (_params, event) => {
            const newTimestamp = event?.overlay?.points?.[0]?.timestamp
            if (newTimestamp === undefined) return
            const data = {...alert.data, time: new Date(newTimestamp).toUTCString()}
            dispatch(editAlert({...alert, data}))
          }},
        })
      })
  }, [readyToDraw, marketTradingInfo, alertsShow, chartColors, alertsFormId])

  return null
}
```

### `buildTimeAlertLabel` helper (local to file)

Builds the label string for future use when SC supports text rendering. Passed to controller but not forwarded to `createTimeAlertLine` yet.

```js
function buildTimeAlertLabel(alert) {
  // Format: "Trigger At {date}" with optional " - {note}"
  // Date formatting uses the alert's time — controller will handle timezone when T1 lands
  const time = getAlertTime(alert)
  if (!time) return ""
  const {note} = alert
  const formatted = moment(time).format("DD MMM 'YY HH:mm")
  const suffix = note ? ` - ${note}` : ""
  return `Trigger At ${formatted}${suffix}`
}
```

Note: This uses `moment` without timezone — the controller should own timezone-aware formatting when T1 is implemented. For now it's a placeholder that won't be displayed.

## Component — `edit-time-alert.js`

Renders the single time alert being edited. Follows `edit-price-alert.js` pattern.

### Structure

```js
const EditTimeAlert = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const alertsForm = useSelector(state => state.alertsForm)
  const alertsShow = useSelector(state => state.chartSettings.alertsShow)
  const dispatch = useDispatch()

  const clearEditAlert = util.useImmutableCallback(() => {
    chartController?.clearOverlays("editTimeAlert")
  })

  useEffect(() => {
    clearEditAlert()
    if (!readyToDraw) return
    if (!alertsForm.isEditing || alertsForm.alert.alertType !== "time") return
    if (!alertsShow) return

    const {alert} = alertsForm
    const time = getAlertTime(alert)
    if (!time) return
    const timestamp = new Date(time).getTime()
    const text = buildEditingTimeAlertLabel(time)  // built but unused until T1

    chartController.createTimeAlert("editTimeAlert", "time", timestamp, {
      color: chartColors.alert,
      text,
      onPressedMoveEnd: {params: {}, callback: (_params, event) => {
        const newTimestamp = event?.overlay?.points?.[0]?.timestamp
        if (newTimestamp === undefined) return
        const data = {...alert.data, time: new Date(newTimestamp).toUTCString()}
        dispatch(editAlert({...alert, data}))
      }},
    })
  }, [readyToDraw, alertsForm, chartColors, alertsShow])

  return null
}
```

### `buildEditingTimeAlertLabel` helper (local to file)

```js
function buildEditingTimeAlertLabel(time) {
  // Editing label: time only, no "Trigger At" prefix, no note
  return moment(time).format("DD MMM 'YY HH:mm")
}
```

### Key differences from `edit-price-alert.js`

- Uses the same `createTimeAlert` controller method as pending (just different group + callbacks)
- No saving state — time alerts don't show a "Saving" handle (TV doesn't either; the vertical line just disappears during save)
- No `onModify` — time alerts don't have a submit-from-chart interaction (submit happens from the form)
- No `onCancel` — no cancel button on vertical lines
- Uses `onPressedMoveEnd` instead of price alert's `onMoveEnd` (different SC callback for overlay vs order-line)

## Component — `triggered-time-alerts.js`

Renders triggered time alerts. Follows `triggered-price-alerts.js` pattern.

### Structure

```js
const TriggeredTimeAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const {alertsShow, alertsShowClosed} = useSelector(state => ({
    alertsShow: state.chartSettings.alertsShow,
    alertsShowClosed: state.chartSettings.alertsShowClosed,
  }))

  const clear = util.useImmutableCallback(() => {
    chartController?.clearOverlays("triggeredTimeAlerts")
  })
  useSymbolChangeCleanup(currentMarket, clear)

  useEffect(() => {
    clear()
    if (!readyToDraw || !alertsShow || !alertsShowClosed) return

    const {triggeredAlerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO

    triggeredAlerts
      .filter(a => a.alertType === "time")
      .forEach(alert => {
        const time = getAlertTime(alert)
        if (!time) return
        const timestamp = new Date(time).getTime()
        const text = buildTimeAlertLabel(alert)  // built but unused until T1
        chartController.createTriggeredTimeAlert(`triggered-time-${alert.id}`, timestamp, {
          color: chartColors.closedAlert,
          text,
        })
      })
  }, [readyToDraw, marketTradingInfo, alertsShowClosed, alertsShow, chartColors])

  return null
}
```

## Wiring — `super-chart.js`

```js
import TimeAlerts from "./overlays/time-alerts"
import EditTimeAlert from "./overlays/edit-time-alert"
import TriggeredTimeAlerts from "./overlays/triggered-time-alerts"

// Inside render:
<TimeAlerts/>
<EditTimeAlert/>
<TriggeredTimeAlerts/>
```

## Shared helpers

`getAlertTime` is used by all three components. Options:
1. **Local to each file** — simple, follows price alerts pattern (which has `buildQuantityText` local)
2. **Shared utility** — avoids duplication

Decision: Define `getAlertTime` in each file locally (3 lines, trivial). The label builders are unique per component so they stay local too.

## `onClick` callback shape

SC callbacks follow the pattern `{params: {}, callback: (params, event) => ...}` — same as `onModify`/`onCancel`/`onMoveEnd` on order lines. The overlay event object contains `event.overlay.points[0].timestamp` for the current position.

## Visibility range check (R7)

TV uses `timeIsInVisibleRange(time)` to skip alerts outside the visible range. For SC, we skip this check initially — SC overlays outside the visible range are simply not rendered by the chart engine. If performance issues arise, we can add range filtering later.

## Open Questions

1. ~~**`onClick` event shape**~~ — Assumed same as other SC callbacks: `(params, event)` with `event.overlay.points[0].timestamp`. To verify during implementation.
