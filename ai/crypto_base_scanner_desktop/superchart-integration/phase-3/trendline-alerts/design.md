# Design: Trendline Alerts — SuperChart Integration

## Approach

Five files change:

1. **`chart-controller.js`** — add `createTrendlineAlert` and `createTriggeredTrendlineAlert` methods
2. **`overlays/trendline-alerts.js`** — new overlay component for pending trendline alerts
3. **`overlays/edit-trendline-alert.js`** — new overlay component for editing trendline alert
4. **`overlays/triggered-trendline-alerts.js`** — new overlay component for triggered trendline alerts
5. **`super-chart.js`** — wire all three components

Follows the time alerts pattern closely. Like time alerts, pending and editing trendline alerts are visually identical (same segment, same color, `lock: false`) — only the callbacks differ. A single `createTrendlineAlert` controller method handles both.

## Points Format Conversion (R6)

### TV format → SC format

Alert data stores points in TV format: `{time: epochSeconds, price: number}`.
SC segment expects: `{timestamp: epochMilliseconds, value: number}`.

```
alert.data.points[i]              →   {time: 1774051200, price: 67500}
  ↓ convert
SC overlay point                  →   {timestamp: 1774051200000, value: 67500}
```

Conversion (component-level, before passing to controller):
```js
const scPoints = alert.data.points.map(p => ({
  timestamp: p.time * 1000,
  value: p.price,
}))
```

### Legacy data path

Like time alerts, some trendline alerts have nested `alert.data.data.points` instead of `alert.data.points`. Also `lineType` and `properties` may be under `data.data`:

```js
function getAlertData(alert) {
  const {data} = alert
  const inner = data?.data || data || {}
  return {
    points: inner.points || data.points,
    lineType: inner.lineType || data.lineType,
  }
}
```

### Callback chain (R4/R5 — `onPressedMoveEnd`)

```
SC callback event                 →   event.overlay.points   [{timestamp, value}, {timestamp, value}]
  ↓ convert back to TV format
TV-format points                  →   [{time: ts/1000, price: value}, ...]
  ↓ util.priceAtTime(points, Date.now()/1000)
priceAtTime                       →   number (projected price at current time)
  ↓ compare with lastPrice
direction                         →   "up" | "down"
  ↓ dispatch(editAlert({...alert, direction, data: {..., points, priceAtTime, direction}}))
Redux alert form updated
```

Key: `util.priceAtTime` expects `{time, price}` in seconds. We convert SC points back to TV format before calling it. This keeps the utility unchanged and maintains compatibility with the alert form which also expects TV-format points.

## Chart Controller — `createTrendlineAlert`

### Pending + Editing (single method)

```js
createTrendlineAlert(group, key, points, callbacks) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "segment",
    points,
    lock: false,
    ...callbacks,
  })
  if (id) this._register(group, key, id)
  return id
}
```

Key decisions:
- `group` parameter — component passes `"trendlineAlerts"` for pending, `"editTrendlineAlert"` for editing
- `lock: false` — both pending and editing are interactive (matching time alert pattern)
- `...callbacks` — spread allows `onPressedMoveEnd` from component
- `points` is an array of two `{timestamp, value}` objects (already converted by component)
- No color/style props in `createOverlay` — `segment` doesn't respect them (T2). Controller still owns the color intent via `this.colors.alert`, but there's nothing to pass until SC fixes the gap.

Usage from components:
- **Pending**: `createTrendlineAlert("trendlineAlerts", key, scPoints, {onPressedMoveEnd: ...})`
- **Editing**: `createTrendlineAlert("editTrendlineAlert", "trendline", scPoints, {onPressedMoveEnd: ...})`

### Triggered alert

```js
createTriggeredTrendlineAlert(key, points) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "segment",
    points,
    lock: true,
  })
  if (id) this._register("triggeredTrendlineAlerts", key, id)
  return id
}
```

Key decisions:
- `lock: true` — not interactive
- No callbacks — display only
- No color props (same T2 gap)

## Component — `trendline-alerts.js`

Renders pending trendline alerts. Follows `time-alerts.js` pattern.

### Data flow

```
MarketTabDataContext.marketTradingInfo.alerts → filter(alertType === "trend_line") → getAlertData() → convert points → createTrendlineAlert()
```

### Structure

```js
function getAlertData(alert) {
  const {data} = alert
  const inner = data?.data || data || {}
  return {
    points: inner.points || data.points,
    lineType: inner.lineType || data.lineType,
  }
}

function toScPoints(tvPoints) {
  return tvPoints.map(p => ({timestamp: p.time * 1000, value: p.price}))
}

function toTvPoints(scPoints) {
  return scPoints.map(p => ({time: p.timestamp / 1000, price: p.value}))
}

const TrendlineAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const alertsShow = useSelector(state => state.chartSettings.alertsShow)
  const alertsFormId = useSelector(state => state.alertsForm.alert.id)
  const dispatch = useDispatch()

  const clearAlerts = util.useImmutableCallback(() => {
    chartController?.clearOverlays("trendlineAlerts")
  })
  useSymbolChangeCleanup(currentMarket, clearAlerts)

  useEffect(() => {
    clearAlerts()
    if (!readyToDraw) return
    if (!alertsShow) return

    const {alerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO

    alerts
      .filter(a => a.alertType === "trend_line" && a.id !== alertsFormId)
      .forEach(alert => {
        const {points} = getAlertData(alert)
        if (!points || points.length < 2) return
        const scPoints = toScPoints(points)
        chartController.createTrendlineAlert("trendlineAlerts", `trendline-${alert.id}`, scPoints, {
          onPressedMoveEnd: (event) => {
            const newScPoints = event?.overlay?.points
            if (!newScPoints || newScPoints.length < 2) return
            const newTvPoints = toTvPoints(newScPoints)
            const lastPrice = currentMarket.getMarket().lastPrice
            const priceAtTime = util.priceAtTime(newTvPoints, Date.now() / 1000)
            const direction = priceAtTime > lastPrice ? "up" : "down"
            const data = {...alert.data, points: newTvPoints, priceAtTime, direction}
            dispatch(editAlert({...alert, direction, data}))
          },
        })
      })
  }, [readyToDraw, marketTradingInfo, alertsShow, chartColors, alertsFormId])

  return null
}
```

### Key decisions

- **Filter by `alertType === "trend_line"`** — note: underscore, not camelCase (matches TV data format, see `alert-row.js`)
- **`toScPoints` / `toTvPoints`** — local conversion helpers. TV uses `{time: seconds, price}`, SC uses `{timestamp: ms, value}`. Kept as local functions (3 lines each, not worth a shared utility).
- **`onPressedMoveEnd` callback** — same pattern as TV's `onSelect`. Reads updated points from `event.overlay.points`, converts back to TV format, calculates `priceAtTime` and `direction`, dispatches `editAlert()`.
- **`currentMarket` needed** for `lastPrice` in direction calculation.

## Component — `edit-trendline-alert.js`

Renders the single trendline alert being edited. Follows `edit-time-alert.js` pattern.

### Structure

```js
const EditTrendlineAlert = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {currentMarket} = useContext(MarketTabContext)
  const alertsForm = useSelector(state => state.alertsForm)
  const alertsShow = useSelector(state => state.chartSettings.alertsShow)
  const dispatch = useDispatch()

  const clearEditAlert = util.useImmutableCallback(() => {
    chartController?.clearOverlays("editTrendlineAlert")
  })

  useEffect(() => {
    clearEditAlert()
    if (!readyToDraw) return
    if (!alertsForm.isEditing || alertsForm.alert.alertType !== "trend_line") return
    if (!alertsShow) return

    const {alert} = alertsForm
    const {points} = getAlertData(alert)
    if (!points || points.length < 2) return
    const scPoints = toScPoints(points)

    chartController.createTrendlineAlert("editTrendlineAlert", "trendline", scPoints, {
      onPressedMoveEnd: (event) => {
        const newScPoints = event?.overlay?.points
        if (!newScPoints || newScPoints.length < 2) return
        const newTvPoints = toTvPoints(newScPoints)
        const lastPrice = currentMarket.getMarket().lastPrice
        const priceAtTime = util.priceAtTime(newTvPoints, Date.now() / 1000)
        const direction = priceAtTime > lastPrice ? "up" : "down"
        const data = {
          ...alert.data, points: newTvPoints, priceAtTime, direction,
        }
        dispatch(editAlert({...alert, direction, price: newTvPoints[0].price, data}))
      },
    })
  }, [readyToDraw, alertsForm, chartColors, alertsShow])

  return null
}
```

### Key differences from `edit-time-alert.js`

- **Two points** instead of one — both extracted from `event.overlay.points`
- **Direction calculation** — needs `currentMarket.getMarket().lastPrice` (edit-time-alert doesn't calculate direction)
- **`price` field** — dispatch includes `price: newTvPoints[0].price` (TV's `edit-alerts.js` sets this for the alert form)
- **No saving state** — trendline alerts don't show a saving indicator (TV didn't either — the entity just disappears during save)

### Shared helpers

`getAlertData`, `toScPoints`, `toTvPoints` are used by both `trendline-alerts.js` and `edit-trendline-alert.js`. Options:
1. **Duplicate in each file** — simple, 3-line functions
2. **Extract to a shared file**

Decision: Duplicate locally in each file (matching time alerts pattern where `getAlertTime` is duplicated in all three files).

## Component — `triggered-trendline-alerts.js`

Renders triggered trendline alerts. Follows `triggered-time-alerts.js` pattern.

### Structure

```js
const TriggeredTrendlineAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const {alertsShow, alertsShowClosed} = useSelector(state => ({
    alertsShow: state.chartSettings.alertsShow,
    alertsShowClosed: state.chartSettings.alertsShowClosed,
  }))

  const clear = util.useImmutableCallback(() => {
    chartController?.clearOverlays("triggeredTrendlineAlerts")
  })
  useSymbolChangeCleanup(currentMarket, clear)

  useEffect(() => {
    clear()
    if (!readyToDraw || !alertsShow || !alertsShowClosed) return

    const {triggeredAlerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO

    triggeredAlerts
      .filter(a => a.alertType === "trend_line")
      .forEach(alert => {
        const {points} = getAlertData(alert)
        if (!points || points.length < 2) return
        const scPoints = toScPoints(points)
        chartController.createTriggeredTrendlineAlert(`triggered-trendline-${alert.id}`, scPoints)
      })
  }, [readyToDraw, marketTradingInfo, alertsShowClosed, alertsShow, chartColors])

  return null
}
```

## Wiring — `super-chart.js`

```js
import TrendlineAlerts from "./overlays/trendline-alerts"
import EditTrendlineAlert from "./overlays/edit-trendline-alert"
import TriggeredTrendlineAlerts from "./overlays/triggered-trendline-alerts"

// Inside render:
<TrendlineAlerts/>
<EditTrendlineAlert/>
<TriggeredTrendlineAlerts/>
```

## Open Questions

None — all unknowns resolved via storybook verification and `createOverlay` shared API.
